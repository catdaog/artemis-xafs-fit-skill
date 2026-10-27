#!/usr/bin/env python3
"""Isolated, auditable execution of the real FDMNES program (no shell)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

SKILL_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PYTHON = SKILL_ROOT / '.deps' / 'python'
if LOCAL_PYTHON.is_dir():
    sys.path.insert(0, str(LOCAL_PYTHON))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False) + '\n', encoding='utf-8')


def resolve_executable(explicit=None):
    choices = [explicit, os.environ.get('FDMNES_EXE')]
    local = SKILL_ROOT / '.deps' / 'fdmnes'
    config = local / 'runtime.json'
    if config.exists():
        choices.append(str(local / json.loads(config.read_text(encoding='utf-8'))['executable']))
    choices.extend([shutil.which('fdmnes'), shutil.which('fdmnes_windows')])
    for choice in choices:
        if choice and Path(choice).is_file():
            return Path(choice).resolve()
    raise FileNotFoundError('FDMNES not found. Set FDMNES_EXE, pass --exe, or use install.')


def install_runtime(destination, archive=None, url=None, expected_sha256=None):
    """Install an explicitly selected official ZIP. Never overwrite an existing runtime."""
    dest = Path(destination).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if (dest / 'runtime.json').exists():
        raise FileExistsError(f'Runtime already installed at {dest}; choose another destination.')
    if bool(archive) == bool(url):
        raise ValueError('Provide exactly one of --archive and --url.')
    package = Path(archive).resolve() if archive else dest / 'download.zip'
    if url:
        from urllib.parse import urlparse
        if urlparse(url).scheme != 'https':
            raise ValueError('Runtime downloads require HTTPS.')
        with urllib.request.urlopen(url, timeout=120) as response, open(package, 'wb') as out:
            shutil.copyfileobj(response, out)
    digest = sha256(package)
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise ValueError('Downloaded archive SHA256 does not match the supplied hash.')
    with zipfile.ZipFile(package) as zipped:
        for item in zipped.infolist():
            target = (dest / item.filename).resolve()
            if not target.is_relative_to(dest):
                raise ValueError('Unsafe archive member path.')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlinks are not supported.')
        zipped.extractall(dest)
    executables = [p for p in dest.rglob('*.exe') if p.name.lower().startswith('fdmnes')]
    if len(executables) != 1:
        raise ValueError(f'Expected one Windows FDMNES executable, found {len(executables)}.')
    exe = executables[0]
    record = {'executable': exe.relative_to(dest).as_posix(), 'executable_sha256': sha256(exe),
              'archive_sha256': digest, 'source_url': url,
              'source_archive': str(package) if archive else None,
              'retrieved_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'trust_note': 'Hash records downloaded bytes; it is not a publisher signature.'}
    save_json(dest / 'runtime.json', record)
    return record


def read_spectrum(path, column=1):
    """Only read numeric rows AFTER the Energy header, never the metadata line."""
    import numpy as np
    rows, started = [], False
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        tokens = line.replace('D', 'E').replace('d', 'e').split()
        if tokens and tokens[0].lower() in ('energy', 'energ', 'e_(ev)'):
            started = True
            continue
        if not started or not tokens:
            continue
        try:
            row = [float(x) for x in tokens]
        except ValueError:
            continue
        if len(row) <= column:
            raise ValueError(f'Spectrum column {column} absent in {path}.')
        rows.append([row[0], row[column]])
    a = np.asarray(rows, dtype=float)
    if a.ndim != 2 or a.shape[0] < 4 or not np.isfinite(a).all():
        raise ValueError(f'Missing/invalid numerical spectrum: {path}')
    if not np.all(np.diff(a[:, 0]) > 0):
        raise ValueError(f'Non-increasing FDMNES energy grid: {path}')
    return a


def run_deck(executable, deck, run_root, timeout=600, column=1):
    """Content-addressed cache includes executable and companion DLL hashes."""
    exe = Path(executable).resolve()
    runtime_files = [exe] + sorted(exe.parent.glob('*.dll'))
    runtime_hashes = {p.name: sha256(p) for p in runtime_files}
    key = hashlib.sha256((deck + json.dumps(runtime_hashes, sort_keys=True)).encode()).hexdigest()
    job = Path(run_root).resolve() / key[:24]
    job.mkdir(parents=True, exist_ok=True)
    result_file = job / 'execution.json'
    if result_file.exists():
        old = json.loads(result_file.read_text(encoding='utf-8'))
        if old.get('status') == 'calculated' and all(
                (job / name).exists() and sha256(job / name) == digest
                for name, digest in old.get('outputs', {}).items()) and old.get('outputs'):
            read_spectrum(job / 'spectrum_conv.txt', column)
            return job, old, True
        raise RuntimeError(f'Incomplete or altered cached calculation: {job}. Use a fresh work directory.')
    (job / 'input.txt').write_text(deck, encoding='ascii')
    (job / 'fdmfile.txt').write_text('1\ninput.txt\n', encoding='ascii')
    local_exe = job / exe.name
    for source in runtime_files:
        target = job / source.name
        if not target.exists():
            try:
                os.link(source, target)
            except OSError:
                shutil.copy2(source, target)
    record = {'status': 'running', 'input_sha256': sha256(job / 'input.txt'),
              'runtime_files_sha256': runtime_hashes, 'command': [str(local_exe)],
              'cwd': str(job), 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    save_json(result_file, record)
    started = time.monotonic()
    try:
        with open(job / 'stdout.log', 'wb') as stdout, open(job / 'stderr.log', 'wb') as stderr:
            process = subprocess.run([str(local_exe)], cwd=job, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, timeout=timeout, check=False,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        record['returncode'] = process.returncode
        if process.returncode:
            raise RuntimeError(f'FDMNES exited with code {process.returncode}.')
        error = job / 'fdmnes_error.txt'
        if error.exists() and error.read_text(errors='replace').strip():
            raise RuntimeError('FDMNES error: ' + error.read_text(errors='replace')[:1500])
        for name in ('spectrum.txt', 'spectrum_conv.txt', 'spectrum_bav.txt'):
            if not (job / name).is_file() or (job / name).stat().st_size == 0:
                raise RuntimeError(f'FDMNES did not produce {name}.')
        read_spectrum(job / 'spectrum.txt', column)
        read_spectrum(job / 'spectrum_conv.txt', column)
        record.update(status='calculated', outputs={name: sha256(job / name) for name in
                      ('spectrum.txt', 'spectrum_conv.txt', 'spectrum_bav.txt')})
    except Exception as error:
        record.update(status='failed', error=str(error))
        raise
    finally:
        record['elapsed_seconds'] = time.monotonic() - started
        save_json(result_file, record)
    return job, record, False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    probe = sub.add_parser('probe')
    probe.add_argument('--exe')
    install = sub.add_parser('install')
    install.add_argument('--destination', default=str(SKILL_ROOT / '.deps' / 'fdmnes'))
    source = install.add_mutually_exclusive_group(required=True)
    source.add_argument('--url')
    source.add_argument('--archive')
    install.add_argument('--sha256')
    run = sub.add_parser('run')
    run.add_argument('input')
    run.add_argument('--exe')
    run.add_argument('--work', required=True)
    run.add_argument('--timeout', type=float, default=600)
    args = parser.parse_args()
    try:
        if args.command == 'install':
            result = install_runtime(args.destination, args.archive, args.url, args.sha256)
        elif args.command == 'probe':
            exe = resolve_executable(args.exe)
            result = {'status': 'located_not_executed', 'executable': str(exe), 'sha256': sha256(exe)}
        else:
            job, record, cached = run_deck(resolve_executable(args.exe),
                Path(args.input).read_text(encoding='ascii'), args.work, args.timeout)
            result = {'job': str(job), 'cached': cached, **record}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
