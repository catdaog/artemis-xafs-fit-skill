"""COD discovery and explicit, provenance-preserving P1 candidate model construction."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen, Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.deps'))

def gemmi_module():
    try:
        import gemmi
        return gemmi
    except ImportError:
        raise RuntimeError('Install requirements.txt (gemmi) into your Python environment or skill/.deps')

def search(formula):
    tokens = re.findall(r'([A-Z][a-z]?)(\d*)', formula.replace(' ', ''))
    if not tokens or ''.join(a+b for a,b in tokens) != formula.replace(' ', ''):
        raise ValueError('Use a simple stoichiometric formula, e.g. MoO3')
    counts = {}
    for el, n in tokens:
        counts[el] = counts.get(el, 0) + int(n or 1)
    order = sorted(counts, key=lambda e: (0 if e=='C' else 1 if e=='H' and 'C' in counts else 2, e))
    cod_formula = ' '.join(e + (str(counts[e]) if counts[e]!=1 else '') for e in order)
    url = 'https://www.crystallography.net/cod/result?' + urlencode({'formula':cod_formula,'format':'json'})
    with urlopen(Request(url, headers={'User-Agent':'XAFS-structure-helper/1.0'}), timeout=45) as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise ValueError('Unexpected COD response; no candidates selected')
    return {'query':formula,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),
            'selection':'required: verify polymorph, temperature, occupancy and citation', 'candidates':records}

def inspect(path):
    g = gemmi_module()
    s = g.read_small_structure(str(path))
    if not s.sites:
        raise ValueError('CIF contains no atom sites')
    sites = [{'id':str(i),'label':a.label,'element':a.element.name,
              'frac':[a.fract.x % 1,a.fract.y % 1,a.fract.z % 1], 'occupancy':a.occ}
             for i,a in enumerate(s.get_all_unit_cell_sites())]
    return {'cell':list(s.cell.parameters),'spacegroup_source':s.spacegroup_hm,
            'sites':sites,'source':str(Path(path).resolve()),
            'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}

def validate(model):
    g = gemmi_module()
    vals = model['cell']
    if len(vals)!=6 or not all(math.isfinite(x) for x in vals):
        raise ValueError('Six finite cell parameters required')
    if any(x<=0 for x in vals[:3]) or any(not 0<x<180 for x in vals[3:]):
        raise ValueError('Invalid cell lengths/angles')
    cell = g.UnitCell(*vals)
    if not math.isfinite(cell.volume) or cell.volume < 1e-6:
        raise ValueError('Degenerate cell')
    sites = model['sites']
    if not sites or len(sites)>20000:
        raise ValueError('Require 1..20000 sites')
    seen=set()
    for a in sites:
        if a['id'] in seen:
            raise ValueError('Duplicate site id')
        seen.add(a['id'])
        if g.Element(a['element']).atomic_number<=0:
            raise ValueError('Unknown element')
        if len(a['frac'])!=3 or not all(math.isfinite(x) for x in a['frac']):
            raise ValueError('Invalid fractional position')
        if not 0 < a.get('occupancy',1) <= 1:
            raise ValueError('Occupancy must be in (0,1]')
    # Exact overlap guard; near-neighbor plausibility still needs phase-specific review.
    coords=set()
    for a in sites:
        key=tuple(round(x%1,8) for x in a['frac'])
        if key in coords:
            raise ValueError('Overlapping/disordered sites: resolve explicit configurations first')
        coords.add(key)
    return cell

def construct(spec, source=None):
    base = inspect(source) if source else {'cell':spec['cell'],'sites':spec['sites']}
    base=json.loads(json.dumps(base))
    for i,a in enumerate(base['sites']):
        a.setdefault('id',str(i)); a.setdefault('occupancy',1)
    if 'cell' in spec:
        base['cell']=spec['cell']
    factors=spec.get('supercell',[1,1,1])
    if len(factors)!=3 or any(type(n)!=int or n<1 for n in factors):
        raise ValueError('supercell requires three positive integers')
    if math.prod(factors)*len(base['sites'])>20000:
        raise ValueError('Supercell exceeds 20000-site limit')
    if factors != [1,1,1]:
        base['sites']=[dict(a,id=a['id']+'@'+','.join(map(str,t)),
            frac=[(a['frac'][j]+t[j])/factors[j] for j in range(3)])
            for t in itertools.product(*(range(n) for n in factors)) for a in base['sites']]
        base['cell']=[base['cell'][j]*factors[j] for j in range(3)]+base['cell'][3:]
    ids={a['id'] for a in base['sites']}
    remove=set(spec.get('remove',[])); changes=spec.get('substitute',{}); occ=spec.get('occupancies',{})
    if (remove|set(changes)|set(occ))-ids:
        raise ValueError('Unknown site id; inspect expanded structure first')
    base['sites']=[dict(a,element=changes.get(a['id'],a['element']),occupancy=occ.get(a['id'],a['occupancy']))
                   for a in base['sites'] if a['id'] not in remove]
    validate(base)
    base.update(model_status='constructed_unrelaxed_candidate',operations=spec)
    return base

def write_cif(model, output):
    g=gemmi_module(); cell=validate(model)
    s=g.SmallStructure(); s.name='candidate'; s.cell=cell; s.spacegroup_hm='P 1'
    for i,a in enumerate(model['sites']):
        site=g.SmallStructure.Site(); site.label=a['element']+str(i+1)
        site.element=g.Element(a['element']); site.fract=g.Fractional(*a['frac']); site.occ=a['occupancy']
        s.add_site(site)
    output=Path(output)
    if output.exists(): raise ValueError('Refusing to overwrite existing CIF')
    output.parent.mkdir(parents=True,exist_ok=True)
    s.make_cif_block().write_file(str(output))
    reread=inspect(output)
    if len(reread['sites'])!=len(model['sites']): raise ValueError('CIF round-trip site count changed')
    model['output_sha256']=reread['source_sha256']
    output.with_suffix('.provenance.json').write_text(json.dumps(model,indent=2),encoding='utf-8')

def feff_input(source, absorber_id, radius, output):
    g=gemmi_module(); model=inspect(source); cell=validate(model)
    if not 3<=radius<=12: raise ValueError('Cluster radius must be 3..12 Angstrom')
    if any(abs(a['occupancy']-1)>1e-8 for a in model['sites']):
        raise ValueError('FEFF requires an explicit fully occupied configuration')
    center=next((a for a in model['sites'] if a['id']==absorber_id),None)
    if center is None: raise ValueError('Unknown absorber site id; run inspect')
    reciprocal=cell.reciprocal()
    bounds=[math.ceil(radius*x)+1 for x in (reciprocal.a,reciprocal.b,reciprocal.c)]
    if math.prod(2*n+1 for n in bounds)*len(model['sites'])>2_000_000:
        raise ValueError('Cluster enumeration too large')
    atoms=[]
    for shift in itertools.product(*(range(-n,n+1) for n in bounds)):
        for a in model['sites']:
            delta=[a['frac'][j]+shift[j]-center['frac'][j] for j in range(3)]
            pos=cell.orthogonalize(g.Fractional(*delta)); d=pos.length()
            if 1e-6<d<=radius: atoms.append((d,pos,a['element']))
    atoms.sort(key=lambda a:a[0])
    if not atoms or len(atoms)>5000: raise ValueError('Empty/oversized FEFF cluster')
    elements=sorted({a[2] for a in atoms}); ipots={el:i+1 for i,el in enumerate(elements)}
    if len(elements)>7: raise ValueError('FEFF6 potential limit exceeded')
    lines=['TITLE CIF candidate; verify absorber, phase and cluster convergence',
           'HOLE 1 1.0','CONTROL 1 1 1 1','PRINT 1 0 0 0',f'RMAX {min(radius,6):.3f}',
           'POTENTIALS',f"0 {g.Element(center['element']).atomic_number} {center['element']}"]
    lines += [f'{ipots[el]} {g.Element(el).atomic_number} {el}' for el in elements]
    lines += ['ATOMS',f"0 0 0 0 {center['element']}"]
    lines += [f'{p.x:.8f} {p.y:.8f} {p.z:.8f} {ipots[el]} {el}' for _,p,el in atoms]
    lines += ['END']
    output=Path(output)
    if output.exists(): raise ValueError('Refusing to overwrite FEFF input')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(lines)+'\n',encoding='ascii')
    output.with_suffix('.provenance.json').write_text(json.dumps(dict(source=model['source'],
        source_sha256=model['source_sha256'],absorber_site=center,radius_A=radius,edge='K',
        status='candidate_requires_path_review',ipot=ipots),indent=2),encoding='utf-8')

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('search'); a.add_argument('--formula',required=True); a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('inspect'); a.add_argument('cif',type=Path); a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('build'); a.add_argument('--source',type=Path); a.add_argument('--spec',type=Path,required=True); a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('feff'); a.add_argument('cif',type=Path); a.add_argument('--absorber-id',required=True); a.add_argument('--radius',type=float,default=6); a.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.command=='build': write_cif(construct(json.loads(args.spec.read_text(encoding='utf-8-sig')),args.source),args.output)
    elif args.command=='feff': feff_input(args.cif,args.absorber_id,args.radius,args.output)
    else:
        result=search(args.formula) if args.command=='search' else inspect(args.cif)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__': main()
