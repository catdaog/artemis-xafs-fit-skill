# XAFS Fit Skill · EXAFS + XANES

[![test](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)

**Un seul skill, deux méthodes : analyse quantitative EXAFS et simulation XANES avec affinement de la géométrie locale.**

`artemis-xafs-fit-skill` exécute de véritables programmes de calcul locaux et conserve les données sources, la provenance des structures, les entrées, les sorties et les journaux. Chaque méthode peut être utilisée seule, ou les deux peuvent servir à évaluer la même structure candidate.

## Choisir une méthode

| Aspect | Ajustement EXAFS | Ajustement XANES près du seuil |
|---|---|---|
| Question principale | Nombres de coordination, distances interatomiques, facteurs de Debye–Waller et chemins de diffusion | Accord des géométries de coordination candidates et de la forme des spectres près du seuil avec les données |
| Programmes | Athena / Artemis / Demeter + FEFF | FDMNES : diffusion multiple avec fonctions de Green ou différences finies |
| Entrées principales | Spectres numériques ou χ(k) non pondéré, paramètres de traitement, étalon au même seuil et modèle structural/FEFF | Données énergie–absorption, informations de calibration et de normalisation, structures atomiques candidates |
| Procédure | Déterminer S₀² sur un étalon → vérifier les chemins → ajuster par étapes → examiner les paramètres | Construire les agrégats atomiques → vérifier la convergence → aligner les spectres → affiner quelques paramètres géométriques → comparer plusieurs points de départ |
| Résultats | DPJ pouvant être rechargé, tableaux k1/k2/k3 et R1/R2/R3, paramètres et compte rendu | Tableaux données/calcul/résidus, paramètres et comparaison des modèles, PNG/SVG, structures, entrées et journaux |
| Détails | [Guide EXAFS (anglais)](references/exafs-guide.en.md) | [Guide XANES / FDMNES (anglais)](references/xanes-fdmnes.md) |

**La branche XANES possède sa propre procédure et ses propres fichiers de résultats ; la calibration EXAFS de S₀², les fenêtres k/R et un DPJ ne sont pas des prérequis.** L’ajustement par combinaison linéaire de spectres de référence (LCF) est une autre méthode, non implémentée dans cette branche XANES.

## Exemples de demande

**EXAFS :**

```text
Utilise $artemis-xafs-fit-skill pour ajuster mes données EXAFS. Détermine S₀² avec un étalon mesuré au même seuil et de coordination connue, ajuste l’échantillon et fournis un DPJ pouvant être rechargé, les tableaux numériques k/R, les paramètres et le compte rendu.
```

**XANES :**

```text
Utilise $artemis-xafs-fit-skill pour calculer les spectres XANES avec FDMNES et affiner la structure locale de mon échantillon à sites monoatomiques. Construis des modèles candidats à partir de la composition et des résultats EXAFS disponibles, vérifie la convergence, compare plusieurs points de départ et fournis les superpositions, les résidus et les fichiers nécessaires à la reproduction.
```

## Données à fournir

- Pour les deux méthodes : élément absorbeur et seuil, correspondance entre fichiers et échantillons, conditions de mesure, définition des colonnes, référence de calibration en énergie et spectres numériques. Conserver les mesures répétées.
- EXAFS : de préférence un étalon au même seuil, le fichier Athena `.prj`, χ(k) non pondéré avec ses paramètres de traitement et les fichiers CIF/FEFF. Pour reprendre un ajustement, joindre aussi le `.fpj`/`.dpj` et les journaux.
- XANES : μ(E) normalisé, ou μ(E) avec des fenêtres de normalisation adaptées. Les comptages bruts du détecteur doivent d’abord être convertis selon le mode de mesure. Fournir un CIF ou des coordonnées atomiques explicites ; identifier les structures hypothétiques comme des candidates.

Une capture d’écran facilite les explications, mais un ajustement exige des données numériques. En l’absence de fichier structural, des modèles candidats peuvent d’abord être construits à partir de la composition et de preuves indépendantes.

## Installation et exécution

Télécharger une [release](https://github.com/catdaog/artemis-xafs-fit-skill/releases) ou cloner le dépôt. Placer le dossier nommé `artemis-xafs-fit-skill` dans le répertoire des skills, par exemple `~/.codex/skills/`. Depuis ce dossier, installer les dépendances dans l’environnement Python utilisé :

```shell
python -m pip install -r requirements.txt -r requirements-xanes.txt
```

EXAFS nécessite une installation séparée de [Demeter](https://bruceravel.github.io/demeter/) / [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html). Télécharger FDMNES pour XANES depuis sa [distribution officielle](https://fdmnes.neel.cnrs.fr/download/). Ces programmes externes ne sont pas inclus. Sous Windows :

```powershell
.\scripts\run_xanes.ps1 -Mode install -Archive C:\path\fdmnes.zip
.\scripts\run_xanes.ps1 -Mode probe
.\scripts\run_xanes.ps1 -Mode simulate -Config examples\xanes\fe-n4.json -Output C:\work\xanes_sim
.\scripts\run_xanes.ps1 -Mode fit -Config C:\work\xanes.json -Output C:\work\xanes_fit
```

La variable `FDMNES_EXE` peut aussi désigner un exécutable existant. Consulter le guide XANES pour la configuration et les commandes. Ces pages traduisent les instructions ; les noms d’arguments et de fichiers restent identiques.

## Résultats et validation

La version 1.4.0 a passé 23 tests locaux, dont la récupération de paramètres à partir d’un spectre synthétique calculé avec le véritable FDMNES et un calcul par différences finies. GitHub CI exécute les tests sans moteur externe. Ce test synthétique vérifie l’exécution du logiciel et la récupération des paramètres, pas la structure d’un catalyseur réel.

Simulation, alignement spectral et ajustement structural sont identifiés séparément. La convergence numérique nécessite encore l’examen des résidus, corrélations, bornes et effets du point de départ. Un accord XANES ne prouve à lui seul ni une dispersion monoatomique ni l’unicité de la structure.

## Documentation et exemples

- [Guide EXAFS détaillé (anglais)](references/exafs-guide.en.md)
- [Procédure XANES / FDMNES (anglais)](references/xanes-fdmnes.md)
- [Modèle de traitement EXAFS par lots](examples/pipeline.template.json)
- [Exemple XANES : modèle illustratif à cinq atomes](examples/xanes/fe-n4.json)
- [Point d’entrée et contraintes du skill (anglais)](SKILL.md)
- [Historique des modifications (chinois/anglais)](CHANGELOG.md)

Licence : le code source du skill est sous [MIT](LICENSE) ; les programmes de calcul externes conservent leurs propres licences.

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)
