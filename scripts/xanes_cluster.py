#!/usr/bin/env python3
"""Extract an explicit Cartesian XANES candidate cluster from a verified CIF."""
import argparse
import itertools
import json
import math
from pathlib import Path

from fdmnes_runtime import save_json
import cif_tools


def extract(source, absorber_id, radius, model_id, provenance):
    g = cif_tools.gemmi_module()
    model = cif_tools.inspect(source)
    cell = cif_tools.validate(model)
    if not 1 <= radius <= 20:
        raise ValueError('Extraction radius must be 1..20 Angstrom.')
    if any(abs(a['occupancy'] - 1) > 1e-8 for a in model['sites']):
        raise ValueError('Resolve partial occupancies/disorder into explicit configurations first.')
    center = next((a for a in model['sites'] if a['id'] == absorber_id), None)
    if center is None:
        raise ValueError('Unknown site id; inspect the symmetry-expanded CIF first.')
    rec = cell.reciprocal()
    bounds = [math.ceil(radius * x) + 1 for x in (rec.a, rec.b, rec.c)]
    if math.prod(2*n+1 for n in bounds) * len(model['sites']) > 2_000_000:
        raise ValueError('Cluster enumeration too large.')
    neighbors = []
    for shift in itertools.product(*(range(-n, n+1) for n in bounds)):
        for atom in model['sites']:
            delta = [atom['frac'][i] + shift[i] - center['frac'][i] for i in range(3)]
            xyz = cell.orthogonalize(g.Fractional(*delta))
            distance = xyz.length()
            if 1e-7 < distance <= radius:
                neighbors.append((distance, atom, [xyz.x, xyz.y, xyz.z], list(shift)))
    neighbors.sort(key=lambda row: (row[0], row[1]['id'], row[3]))
    if len(neighbors) > 5000:
        raise ValueError('Cluster exceeds 5000 atoms.')
    return {'id': model_id, 'provenance': provenance,
            'source_cif': model['source'], 'source_cif_sha256': model['source_sha256'],
            'source_absorber_site': center, 'extraction_radius_A': radius, 'absorber_index': 0,
            'model_status': 'candidate_requires_review', 'parameters': [],
            'atoms': [{'element': center['element'], 'xyz': [0, 0, 0], 'source_site_id': center['id'],
                       'source_translation': [0, 0, 0]}] + [
                     {'element': atom['element'], 'xyz': xyz, 'source_site_id': atom['id'],
                      'source_translation': shift} for _, atom, xyz, shift in neighbors]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cif')
    p.add_argument('--absorber-id', required=True)
    p.add_argument('--radius', required=True, type=float)
    p.add_argument('--model-id', required=True)
    p.add_argument('--provenance', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    out = Path(a.out)
    if out.exists():
        raise FileExistsError('Refusing to overwrite a model.')
    result = extract(a.cif, a.absorber_id, a.radius, a.model_id, a.provenance)
    out.parent.mkdir(parents=True, exist_ok=True)
    save_json(out, result)
    print(json.dumps({'output': str(out.resolve()), 'n_atoms': len(result['atoms'])}))


if __name__ == '__main__':
    main()
