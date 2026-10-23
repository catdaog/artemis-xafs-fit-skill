"""Standard-derived S02 -> samples. Outputs remain unreviewed until scientific review."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from demeter_runtime import run
from check_project import check

HERE=Path(__file__).resolve().parent

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(config, base):
    standard=config['standard']; samples=config['samples']
    if not samples: raise ValueError('At least one sample required')
    if not standard.get('known_cn',0)>0: raise ValueError('Known crystallographic standard CN required')
    ids=set()
    for item in [standard,*samples]:
        if item['id'] in ids or not item['id'].replace('_','').replace('-','').isalnum():
            raise ValueError('Unique safe sample ids required')
        ids.add(item['id'])
        if (item['absorber'],item['edge']) != (standard['absorber'],standard['edge']):
            raise ValueError('S02 cannot transfer across absorber/edge')
        if not item.get('calibration_record') or not item.get('model_review'):
            raise ValueError('Calibration and structure/path review records required')
        if any('REPLACE' in str(item[k]) for k in ('calibration_record','model_review','data','feff')):
            raise ValueError('Replace template placeholders with verified inputs and records')
        for key in ('data','feff'):
            item[key]=str((base/item[key]).resolve())
            if not Path(item[key]).is_file(): raise ValueError('Missing input '+item[key])
        for key in ('paths','sigma_groups'):
            if not item.get(key): raise ValueError('Reviewed '+key+' required')
        if len(item['paths'])!=len(item['sigma_groups']): raise ValueError('Path/group count mismatch')
        if any(type(i)!=int or i<0 for i in item['paths']) or len(set(item['paths']))!=len(item['paths']):
            raise ValueError('Path indices must be unique nonnegative integers')
        if item.get('datatype','chi') not in ('chi','xmu'): raise ValueError('Unsupported datatype')
        item['input_sha256']={k:digest(item[k]) for k in ('data','feff')}
    return config

def fit_one(item, folder, mode, s02=None, root=None):
    folder.mkdir(parents=True)
    args=['--data',item['data'],'--feff',item['feff'],'--out',folder,'--mode',mode,
          '--sample-name',item['id'],'--datatype',item.get('datatype','chi'),
          '--paths',','.join(map(str,item['paths'])),'--sigma-groups',','.join(map(str,item['sigma_groups']))]
    for key in ('kmin','kmax','rmin','rmax','rbkg','bkg_e0'):
        if key in item: args += ['--'+key.replace('_','-'),item[key]]
    if mode=='standard': args += ['--expected-cn',item['known_cn']]
    else:
        args += ['--s02',s02]
        if 'amplitude_groups' in item: args += ['--amplitude-groups',','.join(item['amplitude_groups'])]
    run(HERE/'demeter_first_shell_fit.pl',args,folder,root)
    audit=subprocess.run([sys.executable,str(HERE/'audit_fit_log.py'),str(folder/'fit.log'),
                          '--output',str(folder/'audit.json')],capture_output=True,text=True)
    if audit.returncode: raise RuntimeError('Fit audit failed; inspect '+str(folder/'audit.json'))
    exports={f'k{k}':folder/f'fit_k{k}.dat' for k in (1,2,3)}
    exports.update({f'r{k}_{c}':folder/f'fit_r{k}_{c}.dat' for k in (1,2,3) for c in ('mag','re','im')})
    proof=check(folder/'fit.dpj',exports,folder/'fit_parameters.tsv',root,folder)
    (folder/'reload_proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return json.loads((folder/'fit_result.json').read_text())

def execute(config, output, root=None):
    if output.exists(): raise ValueError('Choose a new output directory; previous runs are preserved')
    output.mkdir(parents=True)
    (output/'resolved_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    state={'status':'running','samples':[]}
    try:
        std=fit_one(config['standard'],output/'standard','standard',root=root)
        s02,error=std['s02'],std['s02_error']
        limits=config.get('s02_bounds',[0.6,1.1])
        if not (math.isfinite(s02) and error is not None and math.isfinite(error) and error>=0
                and limits[0]<=s02<=limits[1] and error/s02<=config.get('max_s02_relative_error',0.3)):
            raise ValueError('Standard S02 failed bounds/uncertainty gate; no samples fitted')
        state['standard']=std
        for item in config['samples']:
            fitted=fit_one(item,output/item['id'],'sample',s02,root)
            fitted['standard_s02_error']=error
            fitted['cn_uncertainty_note']='Fit CN errors conditional on fixed S02; standard uncertainty reported separately.'
            state['samples'].append(fitted)
        state['status']='review_required'
        state['next']='Inspect residuals, correlations, window sensitivity and chemical plausibility before marking accepted and building nine-file delivery.'
    except Exception as exc:
        state.update(status='failed',error=str(exc))
        raise
    finally:
        (output/'pipeline_result.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    return state

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('config',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--demeter-root'); a=p.parse_args()
    cfg=validate(json.loads(a.config.read_text(encoding='utf-8-sig')),a.config.resolve().parent)
    print(json.dumps(execute(cfg,a.output.resolve(),a.demeter_root),indent=2))
