"""Run the installed Demeter bundle without a shell; preserve logs on failure."""
from pathlib import Path
import os
import subprocess


def run(script, args, runtime, demeter_root=None, timeout=600):
    candidates = [demeter_root, os.environ.get('DEMETER_BASE'), str(Path.home() / 'DemeterPerl')]
    root = next((Path(p) for p in candidates if p and (Path(p) / 'perl/bin/perl.exe').is_file()), None)
    if root is None:
        raise RuntimeError('Demeter unavailable: pass --demeter-root or set DEMETER_BASE')
    runtime = Path(runtime).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(APPDATA=str(runtime), DEMETER_BASE=str(root),
               IFEFFIT_DIR=str(root / 'c/share/ifeffit') + os.sep,
               PGPLOT_FONT=str(root / 'c/lib/pgplot/grfont.dat'),
               FONTCONFIG_FILE=str(root / 'c/bin/gnuplot/etc/fonts/fonts.conf'),
               LC_ALL='', LC_CTYPE='', LANG='')
    env['PATH'] = os.pathsep.join([str(root / x) for x in
                                  ('c/bin', 'perl/site/bin', 'perl/bin', 'c/bin/gnuplot/bin')]
                                 + [env.get('PATH', '')])
    command = [str(root / 'perl/bin/perl.exe'), str(Path(script).resolve()), *map(str, args)]
    p = subprocess.run(command, cwd=runtime, env=env, capture_output=True,
                       text=True, errors='replace', timeout=timeout)
    (runtime / (Path(script).stem + '.stdout.log')).write_text(p.stdout, encoding='utf-8')
    (runtime / (Path(script).stem + '.stderr.log')).write_text(p.stderr, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(f'Demeter failed ({p.returncode}); see {runtime}: {p.stderr[-1200:]}')
    return p
