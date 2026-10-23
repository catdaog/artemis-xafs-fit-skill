"""Real Demeter DPJ reload and export/parameter consistency check. No attestation bypass."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import os
import re
import tempfile
import zipfile
from demeter_runtime import run


def structural_check(project):
    project = Path(project)
    if project.suffix.lower() != '.dpj':
        raise ValueError('runtime validation requires a .dpj fit serialization')
    if not zipfile.is_zipfile(project):
        raise ValueError('DPJ is not a ZIP fit serialization')
    with zipfile.ZipFile(project) as z:
        required = {'FIT.SERIALIZATION', 'structure.yaml', 'fit.yaml', 'paths.yaml', 'gds.yaml'}
        if not required.issubset(z.namelist()):
            raise ValueError('DPJ missing required serialization members')
        if sum(i.file_size for i in z.infolist()) > 200_000_000:
            raise ValueError('DPJ exceeds 200MB uncompressed limit')
        if z.testzip():
            raise ValueError('DPJ CRC failure')
        if any(n.startswith(('/', '\\')) or '..' in Path(n).parts or ':' in n for n in z.namelist()):
            raise ValueError('unsafe DPJ member path')


def numeric(path):
    result = []
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        try:
            vals = [float(x) for x in re.split(r'[\s,]+', line.strip())]
        except ValueError:
            continue
        if len(vals) >= 3:
            result.append(vals)
    if len(result) < 3 or any(not math.isfinite(v) for row in result for v in row):
        raise ValueError('invalid numerical export: ' + str(path))
    return result


def compare(a, b, label, cols=(0, 1, 2)):
    if len(a) != len(b):
        raise ValueError(f'{label}: row count differs from reloaded project')
    for ra, rb in zip(a, b):
        for j in cols:
            if not math.isclose(ra[j], rb[j], rel_tol=2e-5, abs_tol=2e-7):
                raise ValueError(f'{label}: export differs from reloaded project at column {j}')


def check(project, exports=None, parameters=None, demeter_root=None, runtime_root=None):
    project = Path(project).resolve()
    structural_check(project)
    base = Path(runtime_root or os.environ.get('XAFS_RUNTIME_ROOT', tempfile.gettempdir()))
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='xr_', dir=base) as temp:
        folder = Path(temp)
        run(Path(__file__).with_name('reload_project.pl'), [project, folder], folder, demeter_root)
        report = json.loads((folder / 'reload.json').read_text())
        if report.get('status') != 'pass' or report.get('path_count', 0) < 1:
            raise ValueError('invalid runtime reload report')
        for name, path in (exports or {}).items():
            loaded = numeric(folder / (name + '.dat'))
            given = numeric(path)
            # Combined R files are stored once with magnitude/real/imaginary columns.
            if name.startswith('r') and len(given[0]) >= 10:
                start = {'mag': 1, 're': 4, 'im': 7}[name.split('_')[1]]
                given = [[r[0], r[start], r[start+1]] for r in given]
            compare(given, loaded, name)
        if parameters:
            with Path(parameters).open(encoding='utf-8-sig', newline='') as f:
                rows = list(csv.DictReader(f, delimiter='\t'))
            if len(rows) != report['path_count']:
                raise ValueError('parameter table path count differs from project')
            for row, p in zip(rows, report['paths']):
                for field, key in [('degeneracy_theory', 'n'), ('reff_A', 'reff'),
                                   ('delr_A', 'delr'), ('sigma2_A2', 'sigma2'), ('e0_eV', 'e0')]:
                    if not math.isclose(float(row[field]), p[key], rel_tol=2e-5, abs_tol=6e-7):
                        raise ValueError(f'parameter {field} differs from project')
                amp = float(row['s02']) * float(row['amplitude_factor'])
                if not math.isclose(amp, p['amplitude'], rel_tol=2e-5, abs_tol=6e-7):
                    raise ValueError('path amplitude differs from project')
        report.update(project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
                      validation='Demeter thaw + numerical re-export', exports_compared=list(exports or {}))
        return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('project', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--demeter-root')
    p.add_argument('--runtime-root')
    a = p.parse_args()
    r = check(a.project, demeter_root=a.demeter_root, runtime_root=a.runtime_root)
    a.output.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps(r))
