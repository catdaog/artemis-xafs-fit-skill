#!/usr/bin/env python3
"""FDMNES XANES simulation, real geometry refinement, and model comparison.

See references/xanes-fdmnes.md and examples/xanes/fe-n4.json for the schema.
All energies are eV, all Cartesian coordinates/displacements are Angstrom.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from pathlib import Path
import re
import sys

from fdmnes_runtime import (SKILL_ROOT, read_spectrum, resolve_executable,
                            run_deck, save_json, sha256)
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares

ELEMENTS = ('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu '
            'Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba '
            'La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb '
            'Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs '
            'Mt Ds Rg Cn Nh Fl Mc Lv Ts Og').split()


def atomic_number(value):
    if isinstance(value, str) and value in ELEMENTS:
        return ELEMENTS.index(value) + 1
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 118:
        raise ValueError(f'Unknown element/atomic number: {value}')
    return value


def number(value, label):
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f'Nonfinite {label}.')
    return x


def vector(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f'{label} must be a three-component list.')
    return np.array([number(x, label) for x in value])


def parameter(spec, kind):
    name = spec['name']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
        raise ValueError('Invalid parameter name.')
    low, high = [number(v, name) for v in spec['bounds']]
    initial = number(spec['initial'], name)
    if not low < high or not low <= initial <= high:
        raise ValueError(f'Invalid bounds/initial for {name}.')
    step = number(spec.get('step', 0.01 if kind == 'geometry' else 0.02), name)
    if step <= 0:
        raise ValueError('Finite-difference steps must be positive.')
    return {**spec, 'bounds': [low, high], 'initial': initial, 'step': step, 'kind': kind}


def coordinates(model, values):
    base = np.array([a['xyz'] for a in model['atoms']], dtype=float)
    xyz = base.copy()
    center = base[model.get('absorber_index', 0)]
    for p in model.get('parameters', []):
        delta = values[p['name']] - p['reference']
        for i in p.get('radial_atoms', []):
            direction = base[i] - center
            length = np.linalg.norm(direction)
            if length < 1e-8:
                raise ValueError('Radial displacement cannot select the absorber.')
            xyz[i] += delta * direction / length
        for effect in p.get('displacements', []):
            xyz[effect['atom']] += delta * np.array(effect['vector'])
    for i in range(len(xyz)):
        if i and np.min(np.linalg.norm(xyz[:i] - xyz[i], axis=1)) < model.get('min_separation_A', 0.5):
            raise ValueError('Geometry has overlapping/unphysically close atoms.')
    return xyz


def validate_config(config):
    if config.get('schema_version') != 1:
        raise ValueError('schema_version must be 1.')
    edge = config.get('edge', 'K')
    if edge not in ('K', 'L1', 'L2', 'L3'):
        raise ValueError('Supported edges: K, L1, L2, L3; assess theory suitability separately.')
    settings = config['calculation']
    if settings.get('method') not in ('fdm', 'green'):
        raise ValueError('Select method explicitly: fdm or green.')
    if number(settings['radius_A'], 'radius') <= 0:
        raise ValueError('Cluster radius must be positive.')
    r = settings['range_eV']
    if len(r) < 3 or len(r) % 2 != 1:
        raise ValueError('range_eV is [Emin, step, Emax] or piecewise odd-length list.')
    for i in range(1, len(r), 2):
        if number(r[i], 'step') <= 0 or number(r[i+1], 'end') <= number(r[i-1], 'start'):
            raise ValueError('Invalid energy range/step.')
    if 'scf' not in settings or not isinstance(settings['scf'], bool):
        raise ValueError('Set calculation.scf explicitly to true/false.')
    conv = settings.get('convolution', {})
    if set(conv) - {'gamma_hole', 'gamma_max', 'ecent', 'elarg', 'e_cut'}:
        raise ValueError('Unknown convolution keyword.')
    for name, value in conv.items():
        number(value, name)
        if name != 'e_cut' and float(value) <= 0:
            raise ValueError(f'{name} must be positive.')
    ids = set()
    for model in config['models']:
        mid = model['id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', mid) or mid in ids:
            raise ValueError('Model ids must be unique safe file names.')
        ids.add(mid)
        if not model.get('provenance'):
            raise ValueError('Each model needs provenance (including candidate/illustrative status).')
        atoms = model['atoms']
        if not atoms:
            raise ValueError('Empty structure.')
        for atom in atoms:
            atomic_number(atom['element'])
            vector(atom['xyz'], 'atom xyz')
        ai = model.get('absorber_index', 0)
        if not isinstance(ai, int) or not 0 <= ai < len(atoms):
            raise ValueError('Invalid zero-based absorber_index.')
        if atomic_number(atoms[ai]['element']) != atomic_number(config['absorber']):
            raise ValueError('Selected absorber does not match config.absorber.')
        names = set()
        for p in model.get('parameters', []):
            parameter(p, 'geometry')
            if p['name'] in names or p['name'] in ('shift_eV', 'gaussian_sigma_eV', 'amplitude', 'offset'):
                raise ValueError('Duplicate/reserved geometry parameter name.')
            names.add(p['name'])
            number(p['reference'], 'reference')
            if not p.get('radial_atoms') and not p.get('displacements'):
                raise ValueError('Geometry parameter must move explicit atoms.')
            indices = list(p.get('radial_atoms', []))
            if len(indices) != len(set(indices)):
                raise ValueError('Duplicate radial atom index.')
            for effect in p.get('displacements', []):
                indices.append(effect['atom'])
                vector(effect['vector'], 'displacement vector')
            if any(not isinstance(i, int) or not 0 <= i < len(atoms) for i in indices):
                raise ValueError('Invalid zero-based parameter atom index.')
        initial = {p['name']: p['initial'] for p in model.get('parameters', [])}
        coordinates(model, initial)
        # Check each parameter's bounds before launching costly calculations.
        for p in model.get('parameters', []):
            for endpoint in p['bounds']:
                coordinates(model, {**initial, p['name']: endpoint})
    if not ids:
        raise ValueError('At least one model required.')


def make_deck(config, model, values, radius=None):
    calc = config['calculation']
    xyz = coordinates(model, values)
    lines = ['! Generated XANES calculation; see config.used.json for provenance',
             'Filout', 'spectrum', 'Range', ' '.join(f'{v:.10g}' for v in calc['range_eV']),
             'Radius', f'{radius or calc["radius_A"]:.8g}', 'Edge', config.get('edge', 'K'),
             'Absorber', str(model.get('absorber_index', 0) + 1)]
    if calc['method'] == 'green':
        lines += ['Green']
    if calc['scf']:
        lines += ['SCF']
    if calc.get('quadrupole', False):
        lines += ['Quadrupole']
    lines += ['Molecule', '1 1 1 90 90 90']
    for atom, position in zip(model['atoms'], xyz):
        lines += [str(atomic_number(atom['element'])) + ' ' + ' '.join(f'{v:.9f}' for v in position)]
    lines += ['Convolution']
    for name, value in calc.get('convolution', {}).items():
        lines += [name, f'{value:.10g}']
    lines += ['End', '']
    return '\n'.join(lines)


def load_numeric(path, columns):
    rows = []
    begun = False
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '!', ';')):
            continue
        parts = re.split(r'[\s,]+', stripped)
        try:
            row = [float(parts[i].replace('D', 'E')) for i in columns]
        except (ValueError, IndexError):
            if begun:
                raise ValueError(f'Malformed data row after numerical data began: {stripped[:100]}')
            continue
        rows.append(row)
        begun = True
    a = np.asarray(rows, dtype=float)
    if a.ndim != 2 or len(a) < 8 or not np.isfinite(a).all():
        raise ValueError('Experimental data need at least eight finite rows.')
    if not np.all(np.diff(a[:, 0]) > 0):
        raise ValueError('Experimental energy must increase strictly; resolve duplicates/order explicitly.')
    return a


def prepare_experiment(spec, base):
    data_kind = spec.get('data_kind', 'experimental')
    if data_kind not in ('experimental', 'synthetic'):
        raise ValueError('experiment.data_kind must be experimental or synthetic.')
    path = (base / spec['path']).resolve()
    columns = [spec.get('energy_column', 0), spec.get('mu_column', 1)]
    if 'sigma_column' in spec:
        columns.append(spec['sigma_column'])
    raw = load_numeric(path, columns)
    if not spec.get('calibration_basis'):
        raise ValueError('Record experiment.calibration_basis; unknown is allowed but must be stated.')
    energy = raw[:, 0] + number(spec.get('calibration_shift_eV', 0), 'calibration shift')
    mu = raw[:, 1].copy()
    sigma = raw[:, 2].copy() if len(columns) == 3 else None
    record = {'source_path': str(path), 'source_sha256': sha256(path),
              'data_kind': data_kind,
              'calibration_basis': spec['calibration_basis'],
              'calibration_shift_eV': spec.get('calibration_shift_eV', 0),
              'edge_energy_eV': number(spec['edge_energy_eV'], 'experimental edge reference'),
              'normalization': spec['normalization']}
    if spec['normalization'] == 'linear_windows':
        e0 = record['edge_energy_eV']
        fits = []
        for name in ('pre_edge_window_eV', 'post_edge_window_eV'):
            low, high = spec[name]
            mask = (energy >= low) & (energy <= high)
            if mask.sum() < 3 or high <= low:
                raise ValueError(f'Insufficient points in {name}. Windows use calibrated absolute energy.')
            fits.append(np.polyfit(energy[mask] - e0, mu[mask], 1))
        pre, post = fits
        jump = post[1] - pre[1]
        if jump <= 0:
            raise ValueError('Nonpositive edge jump.')
        mu = (mu - np.polyval(pre, energy - e0)) / jump
        if sigma is not None:
            sigma /= jump
        record.update(pre_coefficients=pre.tolist(), post_coefficients=post.tolist(), edge_jump=float(jump),
                      flatten_post_edge=False)
    elif spec['normalization'] != 'already_normalized':
        raise ValueError('normalization must be already_normalized or linear_windows.')
    if sigma is not None and np.any(sigma <= 0):
        raise ValueError('Experimental uncertainties must be positive.')
    return {'energy': energy, 'mu': mu, 'sigma': sigma, 'raw': raw, 'record': record}


def aligned_spectrum(theory, target, shift, sigma):
    """Positive shift moves theoretical features toward higher experimental energy."""
    if sigma < 0:
        raise ValueError('Gaussian sigma cannot be negative.')
    lo, hi = theory[0, 0], theory[-1, 0]
    queries = np.asarray(target) - shift
    margin = 4 * sigma
    if queries.min() < lo + margin or queries.max() > hi - margin:
        raise ValueError('Theory range too narrow for fit window, shift bounds and 4-sigma broadening tails.')
    if sigma <= 1e-9:
        return np.interp(queries, theory[:, 0], theory[:, 1])
    spacing = min(float(np.min(np.diff(theory[:, 0]))), max(sigma / 5, 0.02))
    grid = np.linspace(lo, hi, int(math.ceil((hi - lo) / spacing)) + 1)
    smooth = gaussian_filter1d(np.interp(grid, theory[:, 0], theory[:, 1]),
                             sigma / (grid[1] - grid[0]), mode='nearest', truncate=4)
    return np.interp(queries, grid, smooth)


def nuisance_specs(fit):
    params, fixed = [], {}
    defaults = {'shift_eV': 0., 'gaussian_sigma_eV': 0., 'amplitude': 1., 'offset': 0.}
    for name, default in defaults.items():
        spec = fit.get(name, {'fixed': default})
        if 'fixed' in spec:
            fixed[name] = number(spec['fixed'], name)
        else:
            params.append(parameter({**spec, 'name': name}, 'nuisance'))
    for name in ('gaussian_sigma_eV', 'amplitude'):
        p = next((p for p in params if p['name'] == name), None)
        minimum = p['bounds'][0] if p else fixed[name]
        if minimum < 0 or (name == 'amplitude' and minimum == 0):
            raise ValueError('Gaussian sigma must be nonnegative and amplitude strictly positive.')
    return params, fixed


class Calculator:
    def __init__(self, config, executable, work):
        self.config, self.exe, self.work = config, executable, work
        self.launches = 0
        self.requests = 0
        self.memory = {}
        self.max_runs = config.get('limits', {}).get('max_engine_runs', 150)

    def calculate(self, model, values, radius=None):
        deck = make_deck(self.config, model, values, radius)
        if deck in self.memory:
            return self.memory[deck]
        if self.launches >= self.max_runs:
            raise RuntimeError('FDMNES calculation budget exhausted; no completed fit may be claimed.')
        job, record, cached = run_deck(self.exe, deck, self.work / 'calculations',
                    self.config.get('limits', {}).get('timeout_seconds', 600))
        self.launches += int(not cached)
        self.requests += 1
        theory = read_spectrum(job / 'spectrum_conv.txt')
        self.memory[deck] = (theory, job)
        return theory, job


def uncertainty_report(result, params, weighted):
    p = len(params)
    if p == 0:
        return {'status': 'no_free_parameters', 'standard_errors': {}, 'correlation': []}
    jac = np.asarray(result.jac)
    singular = np.linalg.svd(jac, compute_uv=False)
    rank = int(np.linalg.matrix_rank(jac))
    condition = float(singular[0] / singular[-1]) if rank == p else None
    report = {'status': 'rank_deficient' if rank < p else 'local_linear_approximation',
              'rank': rank, 'condition_number': condition, 'standard_errors': {}, 'correlation': [],
              'caveat': 'Conditional local errors exclude theory/model/calibration systematics and energy-point correlation.'}
    if rank < p or len(result.fun) <= p:
        return report
    # Absolute supplied sigma is used without rescaling. Otherwise estimate local residual variance.
    factor = 1. if weighted else float(np.dot(result.fun, result.fun) / (len(result.fun) - p))
    _, s, vt = np.linalg.svd(jac, full_matrices=False)
    covariance = (vt.T / s**2) @ vt * factor
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    den = np.outer(se, se)
    corr = np.divide(covariance, den, out=np.eye(p), where=den > 0)
    report.update(standard_errors={p['name']: float(e) for p, e in zip(params, se)},
                  correlation=corr.tolist())
    return report


def write_table(path, header, rows, delimiter=','):
    with open(path, 'w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)


def refine_model(config, model, experiment, calculator, destination):
    fit = config['fit']
    destination.mkdir(parents=True, exist_ok=False)
    geometry = [parameter(p, 'geometry') for p in model.get('parameters', [])]
    nuisance, fixed = nuisance_specs(fit)
    params = geometry + nuisance
    low = np.array([p['bounds'][0] for p in params])
    high = np.array([p['bounds'][1] for p in params])
    e = experiment['energy']
    mask = (e >= fit['window_eV'][0]) & (e <= fit['window_eV'][1])
    energy, observed = e[mask], experiment['mu'][mask]
    if len(energy) < max(8, 3 * len(params)):
        raise ValueError('Too few points for this parameterization; reduce variables/widen data window.')
    relative_energy = energy - experiment['record']['edge_energy_eV']
    uncertainty = experiment['sigma'][mask] if experiment['sigma'] is not None else np.ones(len(energy))
    evaluations = []

    def values_for(x):
        return {**fixed, **{p['name']: float(v) for p, v in zip(params, x)}}

    def predicted(x):
        values = values_for(x)
        theory, job = calculator.calculate(model, values)
        signal = aligned_spectrum(theory, relative_energy, values['shift_eV'], values['gaussian_sigma_eV'])
        return values['amplitude'] * signal + values['offset'], job

    def objective(x):
        signal, job = predicted(x)
        residual = (signal - observed) / uncertainty
        evaluations.append({'parameters': values_for(x), 'sse': float(residual @ residual),
                            'calculation': str(job)})
        return residual

    def jacobian(x):
        # Absolute finite steps avoid numerically meaningless sub-picometre geometry perturbations.
        columns = []
        for i, p in enumerate(params):
            left, right = x.copy(), x.copy()
            left[i] = max(low[i], x[i] - p['step'])
            right[i] = min(high[i], x[i] + p['step'])
            columns.append((objective(right) - objective(left)) / (right[i] - left[i]))
        return np.column_stack(columns)

    initial = np.array([p['initial'] for p in params])
    # Validate full shift/broadening envelope before optimization, not after many engine jobs.
    initial_theory, _ = calculator.calculate(model, values_for(initial))
    bounds_by_name = {p['name']: p['bounds'] for p in params}
    shift_bounds = bounds_by_name.get('shift_eV', [fixed.get('shift_eV', 0.)] * 2)
    max_sigma = bounds_by_name.get('gaussian_sigma_eV', [0, fixed.get('gaussian_sigma_eV', 0.)])[1]
    for shift in shift_bounds:
        aligned_spectrum(initial_theory, relative_energy, shift, max_sigma)
    max_nfev = config.get('limits', {}).get('max_nfev', 40)
    stage = None
    if nuisance and geometry:
        indices = list(range(len(geometry), len(params)))

        def staged_objective(n):
            x = initial.copy()
            x[indices] = n
            return objective(x)

        def staged_jacobian(n):
            x = initial.copy()
            x[indices] = n
            # Geometry is held fixed: do not launch geometry jobs in this alignment stage.
            cols = []
            for j, i in enumerate(indices):
                a, b = n.copy(), n.copy()
                a[j] = max(low[i], n[j] - params[i]['step'])
                b[j] = min(high[i], n[j] + params[i]['step'])
                cols.append((staged_objective(b) - staged_objective(a)) / (b[j] - a[j]))
            return np.column_stack(cols)
        stage = least_squares(staged_objective, initial[indices], bounds=(low[indices], high[indices]),
                              jac=staged_jacobian, max_nfev=max_nfev, x_scale='jac')
        initial[indices] = stage.x
    starts = [initial]
    for start in model.get('additional_starts', fit.get('additional_starts', [])):
        if set(start) - {p['name'] for p in params}:
            raise ValueError('additional_starts contains an unknown/fixed parameter.')
        candidate = np.array([start.get(p['name'], v) for p, v in zip(params, initial)])
        if np.any(candidate < low) or np.any(candidate > high):
            raise ValueError('Additional start outside bounds.')
        starts.append(candidate)
    results = []
    if params:
        for x in starts:
            results.append(least_squares(objective, x, jac=jacobian, bounds=(low, high),
                          max_nfev=max_nfev, x_scale='jac',
                          ftol=fit.get('ftol', 1e-6), xtol=fit.get('xtol', 1e-5),
                          gtol=fit.get('gtol', 1e-6)))
        successful = [r for r in results if r.success]
        result = min(successful or results, key=lambda r: float(r.fun @ r.fun))
        best = result.x
        converged = bool(result.success)
        errors = uncertainty_report(result, params, experiment['sigma'] is not None)
    else:
        best, converged = initial, True
        errors = {'status': 'no_free_parameters', 'standard_errors': {}, 'correlation': []}
    signal, best_job = predicted(best)
    values = values_for(best)
    residual = observed - signal
    warnings = []
    if not converged:
        warnings.append('optimizer_not_converged')
    if geometry and len(starts) == 1:
        warnings.append('single_structural_start_not_a_global_search')
    if params and converged and result.optimality > 10 * fit.get('gtol', 1e-6):
        warnings.append('optimizer_stopped_before_gradient_tolerance')
    boundary = [p['name'] for p, v in zip(params, best) if
                min(v - p['bounds'][0], p['bounds'][1] - v) < 1e-3 * (p['bounds'][1] - p['bounds'][0])]
    if boundary:
        warnings.append('parameters_at_bounds: ' + ', '.join(boundary))
    if errors['status'] == 'rank_deficient':
        warnings.append('rank_deficient_parameterization')
    corr = np.asarray(errors['correlation'])
    if corr.size and np.any(np.abs(corr - np.diag(np.diag(corr))) > .95):
        warnings.append('parameter_correlation_above_0.95')
    if len(results) > 1:
        spread = [float(r.fun @ r.fun) for r in results]
        if max(spread) - min(spread) > max(1e-10, .01 * min(spread)):
            warnings.append('start_dependent_minima')
    report = {'model': model['id'], 'status': 'review_required' if converged else 'incomplete',
              'target_data_kind': experiment['record']['data_kind'],
              'mode': 'structural_fit' if geometry else ('spectral_alignment' if params else 'model_comparison'),
              'provenance': model['provenance'], 'parameters': values,
              'fitted_parameters': [p['name'] for p in params],
              'n_geometry_parameters': len(geometry), 'n_parameters': len(params),
              'n_energy_points': len(energy), 'rmse': float(np.sqrt(np.mean(residual**2))),
              'r_factor': float(np.sum(residual**2) / max(np.sum(observed**2), 1e-30)),
              'weighted_sse': float(np.sum((residual / uncertainty)**2)),
              'sigma_supplied': experiment['sigma'] is not None,
              'optimizer_converged': converged, 'warnings': warnings, 'uncertainty': errors,
              'best_calculation': str(best_job),
              'starts': [{'success': bool(r.success), 'message': str(r.message),
                          'optimality': float(r.optimality),
                          'parameters': values_for(r.x), 'sse': float(r.fun @ r.fun)} for r in results],
              'alignment_stage_converged': bool(stage.success) if stage is not None else None,
              'acceptance': 'Numerical optimization is not scientific acceptance.'}
    if experiment['sigma'] is not None:
        report['reduced_chi_square_assuming_independent_points'] = report['weighted_sse'] / (len(energy) - len(params))
    target_name = 'synthetic_target' if experiment['record']['data_kind'] == 'synthetic' else 'experimental'
    write_table(destination / 'data_fit.csv', ['energy_eV', target_name, 'calculated', 'residual_target_minus_calc'],
                zip(energy, observed, signal, residual))
    theory = read_spectrum(best_job / 'spectrum_conv.txt')
    write_table(destination / 'theory_native.csv', ['energy_relative_Fermi_eV', 'fdmnes_convolved_cross_section'], theory)
    save_json(destination / 'fit_result.json', report)
    save_json(destination / 'evaluations.json', evaluations)
    save_json(destination / 'best_structure.json', {**model, 'parameters': [], 'original_parameterization': model.get('parameters', []), 'atoms': [
        {**atom, 'xyz': position.tolist()} for atom, position in zip(model['atoms'], coordinates(model, values))],
        'parameters_at_export': values,
        'note': 'Coordinates already transformed; do not apply reference displacements twice.'})
    import shutil
    shutil.copy2(best_job / 'input.txt', destination / 'best_fdmnes_input.txt')
    write_table(destination / 'parameters.tsv', ['parameter', 'value', 'status', 'local_standard_error', 'lower', 'upper'],
        [[name, value, 'fitted' if name in {p['name'] for p in params} else 'fixed',
          errors['standard_errors'].get(name, ''),
          next((p['bounds'][0] for p in params if p['name'] == name), ''),
          next((p['bounds'][1] for p in params if p['name'] == name), '')] for name, value in values.items()], '\t')
    make_plot(destination / 'comparison', energy, observed, signal, model['id'],
              experiment['record']['data_kind'])
    return report


def make_plot(prefix, energy, observed, calculated, label, data_kind='experimental'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(6, 5), gridspec_kw={'height_ratios': [3, 1]})
    axes[0].plot(energy, observed, label='Synthetic target' if data_kind == 'synthetic' else 'Experimental')
    axes[0].plot(energy, calculated, label='FDMNES')
    title = label + (' (synthetic regression)' if data_kind == 'synthetic' else '')
    axes[0].set(ylabel='Normalized absorption', title=title)
    axes[0].legend(frameon=False)
    axes[1].plot(energy, observed - calculated, color='0.3')
    axes[1].axhline(0, color='0.7', lw=.7)
    axes[1].set(xlabel='Photon energy (eV)', ylabel='Residual')
    fig.tight_layout()
    fig.savefig(str(prefix) + '.png', dpi=180)
    fig.savefig(str(prefix) + '.svg')
    plt.close(fig)


def simulate(config, calculator, destination):
    reports = []
    for model in config['models']:
        values = {p['name']: p['initial'] for p in model.get('parameters', [])}
        folder = destination / model['id']
        folder.mkdir()
        theory, job = calculator.calculate(model, values)
        write_table(folder / 'theory_native.csv', ['energy_relative_Fermi_eV', 'fdmnes_convolved_cross_section'], theory)
        import shutil
        shutil.copy2(job / 'input.txt', folder / 'fdmnes_input.txt')
        report = {'model': model['id'], 'status': 'simulated_not_fitted', 'parameters': values,
                  'calculation': str(job), 'provenance': model['provenance']}
        save_json(folder / 'simulation.json', report)
        reports.append(report)
    return reports


def convergence(config, calculator, destination):
    """Finite clusters: radius tests do NOT synthesize missing support atoms."""
    radii = config['calculation'].get('convergence_radii_A', [])
    if len(radii) < 2 or any(b <= a for a, b in zip(radii, radii[1:])):
        raise ValueError('convergence_radii_A needs >=2 strictly increasing radii.')
    rows = []
    tolerance = config['calculation'].get('convergence_relative_rms_tolerance', 0.01)
    for model in config['models']:
        values = {p['name']: p['initial'] for p in model.get('parameters', [])}
        previous = None
        for radius in radii:
            spectrum, job = calculator.calculate(model, values, radius)
            rms = None
            if previous is not None:
                if not np.allclose(previous[:, 0], spectrum[:, 0], rtol=0, atol=1e-6):
                    raise ValueError('Convergence spectra use inconsistent energy grids.')
                rms = float(np.linalg.norm(spectrum[:, 1] - previous[:, 1]) /
                            max(np.linalg.norm(spectrum[:, 1]), 1e-30))
            rows.append({'model': model['id'], 'radius_A': radius, 'relative_rms_change': rms,
                         'within_tolerance': rms <= tolerance if rms is not None else None,
                         'calculation': str(job)})
            previous = spectrum
    save_json(destination / 'radius_convergence.json', {'status': 'review_required', 'comparisons': rows,
        'tolerance': tolerance, 'caveat': 'Also inspect peaks and test energy step/method. Unchanged small clusters do not prove support completeness.'})
    return rows


def execute(config_path, destination, executable=None, mode='fit'):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    validate_config(config)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    marker = destination / 'xanes_run.json'
    if marker.exists() or any(destination.iterdir()):
        raise FileExistsError('Output must be a new/empty directory; source files are never overwritten.')
    manifest = {'status': 'running', 'mode': mode, 'config_path': str(config_path),
                'config_sha256': sha256(config_path)}
    save_json(marker, manifest)
    save_json(destination / 'config.used.json', config)
    try:
        exe = resolve_executable(executable)
        manifest.update(executable=str(exe), executable_sha256=sha256(exe))
        calculator = Calculator(config, exe, destination)
        if mode == 'simulate':
            reports = simulate(config, calculator, destination)
            status = 'simulated_not_fitted'
        elif mode == 'converge':
            reports = convergence(config, calculator, destination)
            status = 'review_required'
        else:
            experiment = prepare_experiment(config['experiment'], config_path.parent)
            save_json(destination / 'preprocessing.json', experiment['record'])
            columns = [experiment['raw'][:, 0], experiment['energy'], experiment['raw'][:, 1], experiment['mu']]
            headers = ['raw_energy_eV', 'calibrated_energy_eV', 'raw_mu', 'normalized_mu']
            if experiment['sigma'] is not None:
                columns.append(experiment['sigma'])
                headers.append('normalized_sigma')
            write_table(destination / 'experimental_processed.csv', headers, zip(*columns))
            reports = [refine_model(config, model, experiment, calculator, destination / model['id'])
                       for model in config['models']]
            reports.sort(key=lambda r: r['rmse'])
            status = 'review_required' if all(r['optimizer_converged'] for r in reports) else 'incomplete'
            write_table(destination / 'model_comparison.tsv',
                ['model', 'mode', 'status', 'n_parameters', 'rmse', 'r_factor', 'warnings'],
                [[r[k] if k != 'warnings' else '; '.join(r[k]) for k in
                  ('model', 'mode', 'status', 'n_parameters', 'rmse', 'r_factor', 'warnings')] for r in reports], '\t')
        manifest.update(status=status, target_data_kind=config.get('experiment', {}).get('data_kind', 'experimental') if mode == 'fit' else None,
                        engine_launches=calculator.launches, unique_calculation_requests=calculator.requests,
                        results=reports)
        (destination / 'XANES_WORKFLOW.txt').write_text(
            f'Mode: {mode}\nStatus: {status}\nConfig SHA256: {manifest["config_sha256"]}\n'
            f'Target data kind: {manifest["target_data_kind"]}\n'
            f'FDMNES SHA256: {manifest["executable_sha256"]}\nActual new engine launches: {calculator.launches}\n'
            'Configuration, preprocessing and model records specify all fixed/fitted parameters.\n'
            'Calculation directories retain real inputs, fdmfile.txt, stdout/stderr, native spectra and bav logs.\n'
            'Energy equation: E_theory_relative = E_experiment_calibrated - E0_experiment - shift_eV.\n'
            'FDMNES lifetime convolution precedes optional additional Gaussian instrumental sigma.\n'
            'RMSE/R-factor rankings are descriptive; they do not prove a unique site or single-atom dispersion.\n'
            'Local errors exclude theoretical systematics and point correlation. No source data were changed.\n', encoding='utf-8')
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        save_json(marker, manifest)
        raise
    save_json(marker, manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['simulate', 'converge', 'fit'])
    parser.add_argument('config')
    parser.add_argument('--out', required=True)
    parser.add_argument('--exe')
    args = parser.parse_args()
    try:
        result = execute(args.config, args.out, args.exe, args.mode)
        print(json.dumps({'status': result['status'], 'engine_launches': result['engine_launches'],
                          'output': str(Path(args.out).resolve())}, indent=2))
        return 0 if result['status'] != 'incomplete' else 3
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
