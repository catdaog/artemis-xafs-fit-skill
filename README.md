# Artemis XAFS Fit Skill

A reusable Codex skill for an evidence-traceable XAFS workflow:

1. calibrate a simultaneously measured foil or accepted standard in Athena;
2. determine `S0²` from a known-coordination standard at the same absorber edge;
3. download and validate experimental CIFs with provenance;
4. generate/inspect FEFF paths and fit staged shell models through Demeter/Artemis;
5. reject physically invalid or statistically unidentifiable fits;
6. export a rerunnable project, logs, numerical curves, and model comparison.

The skill covers multiple absorber elements and edges. It includes the historical Teo–Lee `k^n` heuristic based on the dominant **backscatterer** atomic number, plus modern multi-k validation:

- `Zscatterer < 36`: `k³`
- `36 < Zscatterer < 57`: `k²`
- `Zscatterer > 57`: `k¹`

For mixed shells, the workflow recommends testing k weights 1, 2, and 3 simultaneously rather than relying on a single absorber-based weight.

## Install

Copy this folder to:

```text
~/.codex/skills/artemis-xafs-fit-skill
```

Then invoke it with `$artemis-xafs-fit-skill` or let Codex select it for Artemis/EXAFS fitting tasks.

## Included helpers

- `fetch_reference.py` — COD/direct CIF or XAS download, validation, SHA256, provenance sidecar.
- `foil_calibrate.py` — derivative candidate listing and reviewed energy-shift application.
- `suggest_xafs_settings.py` — absorber/edge, standard structure/CN, and scatterer-aware k-weight suggestions.
- `run_demeter.ps1` — isolated Windows Demeter/FEFF runtime wrapper.
- `demeter_first_shell_fit.pl` — fixed-`S0²`, explicit-path first-shell fit driver.
- `audit_fit_log.py` — checks negative `σ²`, extreme shifts, excessive correlations, S0² mismatch, and parameter count.

Read `SKILL.md` for the routing instructions and `references/` for the scientific workflow and source policy.

## Scientific note

The Teo–Lee rule is a historical starting heuristic, not a substitute for data inspection. Source: B.-K. Teo and P. A. Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, [DOI: 10.1021/ja00505a003](https://doi.org/10.1021/ja00505a003).
