# Artemis XAFS Fit Skill

[![test](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](#中文) | [English](#english)

---

# 中文

## 简介

`artemis-xafs-fit-skill` 是一套面向 Codex 的可复现 XAFS/EXAFS 工作流技能，覆盖：

- Athena 能量校准、归一化和背景扣除；
- 同吸收元素、同吸收边标准样的 `S0²` 标定；
- 实验 CIF 获取、来源记录和结构检查；
- FEFF 路径生成、`ipot`、简并度和散射路径检查；
- Artemis/Demeter 分阶段 EXAFS 拟合；
- CN、`ΔE0`、`ΔR`、`σ²`、独立点数和参数相关性审计；
- 原始数据、k 空间、R 空间、拟合工程、日志和参数表的标准化交付；
- SHA256、数值网格和参数算术关系的自动验证。

本技能的目标不是只得到一张“拟合得很好看”的图，而是建立一条可以追溯、复算和审查的证据链：

```text
原始数据 → 能量校准 → Athena处理 → 标准样S0² → CIF/FEFF
        → 第一壳层 → 远壳层/多重散射 → 稳健性检查
        → k/R数值导出 → 参数审计 → 可验证交付包
```

## 适用范围

适用于：

- 金属箔或已知配位化合物标准样；
- K-edge、L-edge 等常见 XAFS/EXAFS 数据；
- Athena、Artemis、Demeter 和 FEFF 工作流；
- 配位数、键长、无序度和多壳层模型拟合；
- 需要原始数据、拟合曲线和参数表文件的可复现项目；
- Windows Demeter 0.9.26 的自动化运行与项目导出。

不适用于：

- 仅进行 XANES 线性组合拟合而完全不涉及 EXAFS；
- 在没有原始数据、FEFF 路径或实际运行结果时生成“拟合数据”；
- 用一个低 R-factor 代替结构合理性、参数可识别性和残差检查；
- 将理论模型、模拟曲线或未运行结果标记为实验拟合结果。

## 完整工作流

| 阶段 | 核心任务 | 必须检查 | 主要输出 |
|---|---|---|---|
| 1. 保存与盘点 | 复制原始数据，记录测量条件与 SHA256 | 元素、吸收边、beamline、模式、扫描编号、温度、参考通道 | 原始文件清单、哈希、测量记录 |
| 2. 能量校准 | 使用同步测量金属箔或认可标准校准 | `dμ/dE`、线站约定特征、同批次传播范围 | 校准偏移、导数图、校准记录 |
| 3. Athena 处理 | pre-edge、normalization、AUTOBK、χ(k) | `Rbkg`、k 范围、glitch、重复扫描一致性、高 k 噪声 | Athena 工程、处理后 `χ(k)` |
| 4. 标定 `S0²` | 用已知 CN 标准样进行低参数第一壳层拟合 | 同吸收元素/同吸收边、理论简并度固定、结果对窗口稳定 | `S0² ± uncertainty`、标准样工程和日志 |
| 5. CIF 与 FEFF | 获取正确相的实验 CIF并生成 FEFF 路径 | 化学式、晶相、空间群、占位、无序、吸收原子、`ipot`、简并度 | CIF、来源记录、`feff.inp`、路径清单 |
| 6. 第一壳层拟合 | 固定 `S0²`，使用最少可识别参数 | 完整第一壳层、共享/分组 `ΔR` 和 `σ²`、一个数据集共用 `ΔE0` | 初始 DPJ/FPJ、fit log、k/R 拟合曲线 |
| 7. 扩展模型 | 按 R 范围加入远壳层和多重散射 | 不遗漏主要路径，不因追求低 R-factor 盲目增加变量 | 候选模型和模型比较表 |
| 8. 参数与稳健性审计 | 检查参数限制、相关性和窗口依赖 | `Nind/Nvar`、边界命中、误差、相关系数、k/R 窗口与 k-weight 扰动 | audit JSON、接受/拒绝模型记录 |
| 9. 数值导出 | 从同一已接受拟合快照导出全部曲线 | k¹/k²/k³、R magnitude/real/imaginary 使用一致网格 | 原始 χ(k)、k 空间和 R 空间 CSV/DAT |
| 10. 打包与验证 | 构建标准目录并复核哈希和算术关系 | 原始文件未覆盖、网格单调、残差和参数关系正确 | 完整交付目录、参数表、`manifest.json` |

详细流程见 [`references/workflow.md`](references/workflow.md)。

## 关键科学约束

下列数值主要是警戒线或推荐起点，不是适用于所有元素、吸收边和温度的硬定律。

| 参数/指标 | 推荐做法 | 警戒或拒绝条件 |
|---|---|---|
| `S0²` | 使用同吸收元素、同吸收边、已知 CN 标准样确定，样品拟合时固定 | `<0.6` 或 `>1.1`通常需要检查；负值拒绝；不能与 CN 无约束同时自由拟合 |
| CN | 先固定理论简并度，再逐个释放有效振幅 | 负 CN、超过结构允许值、来自不完整或重复计数路径 |
| `ΔE0` | 每个数据集通常共用一个，初值 0 eV | 校准后 `|ΔE0| > 10 eV`为明显警告 |
| `ΔR` | 初值 0 Å，仅对结构相关路径共享 | `|ΔR| > 0.10 Å`需解释；边界命中通常表示模型问题 |
| `σ²` | 许多室温第一壳层可从 `0.003–0.008 Å²`开始 | 负值直接拒绝；`>0.015–0.020 Å²`需检查壳层分裂或无序模型 |
| 参数相关性 | 检查完整相关矩阵 | `0.90–0.95`强警告；绝对值 `>0.95`通常需要重构模型 |
| 独立点数 | `Nind ≈ 2ΔkΔR/π + 2` | 必须满足 `Nvar < Nind`；建议 `Nvar ≤ 2/3 Nind` |
| 键长 | 报告 `Rfit = Reff + ΔR` | 不能把 `Reff` 或未相位校正 R 空间峰位直接当作键长 |

联合使用 k-weight 1、2、3 不会使独立点数简单增加三倍。完整限制和稳健性测试见 [`references/parameter-constraints.md`](references/parameter-constraints.md)。

## 标准交付内容

一次实际执行的拟合必须输出文件，而不是只有图片或文字总结：

```text
<sample>_xafs_delivery/
├── DELIVERY.md
├── manifest.json
├── 01_raw/
│   └── 001_<original-name>                 原始文件逐字节副本
├── 02_processed/
│   ├── chi_k_source.dat                    原始处理导出
│   └── chi_k.csv                           k, χ, kχ, k²χ, k³χ, window
├── 03_fit/
│   ├── source_exports/                     Demeter 原始拟合导出
│   ├── kspace_fit_k1.csv                   data, fit, residual, window
│   ├── kspace_fit_k2.csv
│   ├── kspace_fit_k3.csv
│   └── rspace_fit.csv                      magnitude/real/imaginary
├── 04_parameters/
│   ├── source_fit_parameters.tsv           未修改参数导出
│   ├── fit_parameters.tsv                  规范化机器可读表
│   ├── fit_parameters.md                   Markdown 参数表
│   └── fit_statistics.tsv
├── 05_models_projects/                     CIF、feff.inp、DPJ/FPJ、fit.log
└── 06_qa/                                  校准、审计、模型比较、来源记录
```

`rspace_fit.csv` 同时保存：

- `data_mag`, `fit_mag`, `residual_mag`；
- `data_real`, `fit_real`, `residual_real`；
- `data_imag`, `fit_imag`, `residual_imag`。

注意：Demeter 的 R-space magnitude residual 是复数残差的模：

```text
|χdata(R) - χfit(R)|
```

它一般不等于 `|χdata(R)| - |χfit(R)|`。详细文件规范见 [`references/deliverables.md`](references/deliverables.md)。

## 拟合参数表

标准参数表将理论值、拟合值、派生值和固定值分开：

| 字段 | 含义 |
|---|---|
| `sample` | 样品名称 |
| `path_index`, `path`, `scatterer` | FEFF 路径编号、名称与散射原子 |
| `degeneracy_theory` | FEFF 理论路径简并度 |
| `amplitude_factor` | 相对理论配位数的振幅比例 |
| `cn_fit` | `degeneracy_theory × amplitude_factor` |
| `reff_A` | FEFF 几何路径距离 |
| `delr_A`, `delr_error_A` | 拟合距离修正及误差 |
| `r_fit_A` | `reff_A + delr_A` |
| `sigma2_A2`, `sigma2_error_A2` | Debye–Waller 因子及误差 |
| `e0_eV`, `e0_error_eV` | `ΔE0`及误差 |
| `s02`, `s02_status` | `S0²`及其 fixed/fitted 状态 |
| `r_factor`, `fit_status`, `notes` | 拟合统计、审核状态和约束说明 |

## 安装与更新

全新安装：

```powershell
git clone https://github.com/catdaog/artemis-xafs-fit-skill.git `
  "$env:USERPROFILE\.codex\skills\artemis-xafs-fit-skill"
```

更新通过 Git 安装的版本：

```powershell
git -C "$env:USERPROFILE\.codex\skills\artemis-xafs-fit-skill" pull --ff-only
```

也可以下载 GitHub ZIP，并将解压后的目录复制到：

```text
~/.codex/skills/artemis-xafs-fit-skill
```

## 调用示例

在 Codex 中直接调用：

```text
使用 $artemis-xafs-fit-skill 校准我的金属箔，确定 S0²，运行第一壳层拟合，
并输出原始数据、k 空间、R 空间、拟合工程、审计文件和参数表。
```

也可以让 Codex 根据 Athena、Artemis、FEFF、EXAFS、配位数拟合或 R 空间导出等请求自动选择本技能。

## 自动化脚本

| 脚本 | 用途 |
|---|---|
| `fetch_reference.py` | 下载并验证 CIF/XAS 参考文件，记录 URL、SHA256 和来源信息 |
| `foil_calibrate.py` | 列出导数峰候选并应用人工确认的能量校准 |
| `suggest_xafs_settings.py` | 根据吸收原子、吸收边和散射原子建议标准结构与 k-weight 起点 |
| `run_demeter.ps1` | 在独立短路径环境中探测并运行 Windows Demeter |
| `demeter_first_shell_fit.pl` | 固定 `S0²`、显式路径、可分组 `σ²`的第一壳层拟合 |
| `audit_fit_log.py` | 审计负 `σ²`、极端位移、参数数目和高相关性 |
| `build_xafs_delivery.py` | 构建并验证完整 XAFS 数值交付包 |

探测本机 Demeter：

```powershell
.\scripts\run_demeter.ps1 -Action probe
```

构建标准交付包：

```powershell
python scripts/build_xafs_delivery.py build `
  --output sample_xafs_delivery `
  --sample "Sample name" `
  --raw raw_scan_01.dat --raw raw_scan_02.dat `
  --processed-chi chi_k.dat `
  --fit-k1 fit_k1.dat --fit-k2 fit_k2.dat --fit-k3 fit_k3.dat `
  --fit-rmag fit_rmag.dat --fit-rre fit_rre.dat --fit-rim fit_rim.dat `
  --parameters fit_parameters.tsv `
  --statistics fit_statistics.tsv `
  --artifact fit.dpj --artifact fit.log --artifact feff.inp --artifact phase.cif `
  --qa audit.json --qa calibration.json --qa model_comparison.csv

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

打包器拒绝覆盖已有目标目录。重新拟合时请创建带版本号的新目录。

## 仓库结构

```text
artemis-xafs-fit-skill/
├── SKILL.md                              技能入口与强制约束
├── agents/openai.yaml                    Codex 界面信息
├── references/
│   ├── workflow.md                       完整标准样到样品流程
│   ├── basic-principles.md               EXAFS 原理与参数相关性
│   ├── parameter-constraints.md          参数限制与接受标准
│   ├── deliverables.md                   交付包文件规范
│   ├── element-guidance.md               元素、吸收边、标准样和 k-weight
│   ├── software-and-sample-preparation.md 软件与透射样品制备
│   ├── demeter-api.md                    Demeter 自动化接口
│   └── sources.md                        数据、CIF 和软件来源政策
├── scripts/                              可复用工具
└── tests/                                标准库单元测试
```

## 验证

运行 Python 标准库测试：

```powershell
python -m unittest discover -s tests -v
```

运行技能结构验证：

```powershell
python <skill-creator>/scripts/quick_validate.py .
```

仓库通过 GitHub Actions 自动执行脚本语法检查和交付包测试。

## 官方软件与参考工具

- [Demeter](https://bruceravel.github.io/demeter/)：Athena、Artemis 和 Hephaestus。
- [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html)：FEFF 官方下载。
- [XAFSmass](https://xafsmass.readthedocs.io/)：粉末质量、厚度和边跃迁计算。
- [CatMass](https://web.slac.stanford.edu/coaccess/resources/software)：负载型催化剂和复杂组成质量计算。
- [CLS X-Mass](https://xasdb.lightsource.ca/xafsmass)：在线样品/稀释剂质量计算。
- Teo and Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, [DOI: 10.1021/ja00505a003](https://doi.org/10.1021/ja00505a003)。

使用任何 CIF 或外部 XAS 数据前，应核对晶相、测量条件、许可证、来源页面和引用信息。完整来源政策见 [`references/sources.md`](references/sources.md)。

---

# English

## Overview

`artemis-xafs-fit-skill` is a reproducible Codex workflow for XAFS/EXAFS analysis. It covers:

- Athena energy calibration, normalization, and background removal;
- same-absorber, same-edge `S0²` determination from a known-coordination standard;
- acquisition, provenance recording, and validation of experimental CIFs;
- FEFF path generation and checks of absorber, `ipot`, degeneracy, and scattering sequence;
- staged Artemis/Demeter EXAFS fitting;
- auditing of CN, `ΔE0`, `ΔR`, `σ²`, independent points, and parameter correlations;
- standardized delivery of raw data, k-space and R-space curves, projects, logs, and parameter tables;
- automatic verification of hashes, numerical grids, residuals, and derived-parameter arithmetic.

The goal is not merely to produce an attractive fit plot. The skill builds a traceable, rerunnable, and auditable evidence chain:

```text
raw data → energy calibration → Athena processing → standard S0² → CIF/FEFF
         → first shell → higher shells/multiple scattering → robustness tests
         → numerical k/R exports → parameter audit → verified delivery package
```

## Scope

Use this skill for:

- elemental foils and known-coordination compound standards;
- common K-edge, L-edge, and related XAFS/EXAFS measurements;
- Athena, Artemis, Demeter, and FEFF workflows;
- coordination-number, bond-distance, disorder, and multi-shell fitting;
- projects that require downloadable raw, fitted, and tabulated numerical files;
- automated Windows Demeter 0.9.26 execution and export.

Do not use it to:

- perform XANES linear-combination fitting alone with no EXAFS task;
- fabricate fitted data when raw spectra, FEFF paths, or an executed fit are missing;
- treat a low R-factor as a substitute for physical validity, identifiability, and residual inspection;
- label theoretical, simulated, reconstructed, or unexecuted output as an experimental fit.

## End-to-end workflow

| Stage | Main task | Required checks | Main outputs |
|---|---|---|---|
| 1. Preserve and inventory | Copy raw inputs and record conditions and SHA256 | element, edge, beamline, mode, scan IDs, temperature, reference channel | raw inventory, hashes, measurement record |
| 2. Energy calibration | Calibrate with a simultaneously measured foil or accepted standard | `dμ/dE`, beamline convention, valid propagation group | energy shift, derivative plot, calibration record |
| 3. Athena processing | Pre-edge, normalization, AUTOBK, and χ(k) extraction | `Rbkg`, k range, glitches, scan agreement, high-k noise | Athena project and processed `χ(k)` |
| 4. Determine `S0²` | Fit a low-parameter first shell of a known-CN standard | same absorber/edge, fixed crystallographic degeneracy, window stability | `S0² ± uncertainty`, standard project and log |
| 5. CIF and FEFF | Obtain the correct experimental phase and generate paths | formula, phase, space group, occupancy, disorder, absorber, `ipot`, degeneracy | CIF, provenance, `feff.inp`, path inventory |
| 6. First-shell fit | Fix `S0²` and use the smallest identifiable model | complete first shell, justified `ΔR`/`σ²` groups, one `ΔE0` per data set | initial DPJ/FPJ, fit log, k/R fit curves |
| 7. Extend the model | Add higher shells and multiple scattering as required by the R range | no material missing paths; no parameter inflation solely to lower R-factor | candidate fits and model-comparison table |
| 8. Parameter and robustness audit | Test limits, correlations, and window dependence | `Nind/Nvar`, boundary hits, errors, correlations, k/R and k-weight perturbations | audit JSON and accepted/rejected model record |
| 9. Numerical export | Export every curve from the same accepted fit snapshot | consistent grids for k¹/k²/k³ and R magnitude/real/imaginary | raw χ(k), k-space, and R-space tables |
| 10. Package and verify | Build the standard directory and verify hashes and arithmetic | no overwritten source, monotonic grids, valid residuals and parameter relations | complete delivery directory, tables, `manifest.json` |

See [`references/workflow.md`](references/workflow.md) for the detailed procedure.

## Scientific guardrails

The values below are warning thresholds or starting ranges, not universal hard bounds for every absorber, edge, temperature, and phase.

| Parameter/metric | Recommended treatment | Warning or rejection condition |
|---|---|---|
| `S0²` | Determine from a known-CN standard at the same absorber and edge, then fix for sample fits | `<0.6` or `>1.1` usually requires investigation; reject negative values; do not freely covary with CN without an independent constraint |
| CN | Begin with theoretical degeneracy and release effective amplitude groups one at a time | negative CN, values beyond the structural model, incomplete or double-counted path sets |
| `ΔE0` | Normally one value per data set, initialized at 0 eV | `|ΔE0| > 10 eV` after calibration is a strong warning |
| `ΔR` | Initialize at 0 Å and share only across structurally related paths | `|ΔR| > 0.10 Å` requires justification; a boundary hit usually signals a model problem |
| `σ²` | `0.003–0.008 Å²` is a useful starting range for many room-temperature first shells | reject negative values; `>0.015–0.020 Å²` requires a disorder or shell-splitting review |
| Correlation | Inspect the complete matrix | `0.90–0.95` is a strong warning; absolute correlation `>0.95` usually requires reparameterization |
| Information content | `Nind ≈ 2ΔkΔR/π + 2` | require `Nvar < Nind`; prefer `Nvar ≤ 2/3 Nind` |
| Distance | Report `Rfit = Reff + ΔR` | do not report `Reff` or an uncorrected R-space peak maximum as the fitted bond distance |

Simultaneous k weights 1, 2, and 3 do not triple the independent information content. See [`references/parameter-constraints.md`](references/parameter-constraints.md) for the complete acceptance rules and robustness tests.

## Required delivery files

Every executed fit must return files, not only plots or narrative:

```text
<sample>_xafs_delivery/
├── DELIVERY.md
├── manifest.json
├── 01_raw/
│   └── 001_<original-name>                 byte-for-byte raw copy
├── 02_processed/
│   ├── chi_k_source.dat                    unchanged processed export
│   └── chi_k.csv                           k, χ, kχ, k²χ, k³χ, window
├── 03_fit/
│   ├── source_exports/                     unchanged Demeter fit exports
│   ├── kspace_fit_k1.csv                   data, fit, residual, window
│   ├── kspace_fit_k2.csv
│   ├── kspace_fit_k3.csv
│   └── rspace_fit.csv                      magnitude/real/imaginary
├── 04_parameters/
│   ├── source_fit_parameters.tsv           unchanged parameter export
│   ├── fit_parameters.tsv                  normalized machine-readable table
│   ├── fit_parameters.md                   Markdown table
│   └── fit_statistics.tsv
├── 05_models_projects/                     CIF, feff.inp, DPJ/FPJ, fit.log
└── 06_qa/                                  calibration, audit, model comparison, provenance
```

`rspace_fit.csv` contains magnitude, real, and imaginary data, fit, and residual columns. Demeter's R-space magnitude residual is the magnitude of the complex residual,

```text
|χdata(R) - χfit(R)|
```

and is generally not equal to `|χdata(R)| - |χfit(R)|`. See [`references/deliverables.md`](references/deliverables.md) for the exact file and column contract.

## Fit-parameter table

The standardized table separates theoretical, fitted, derived, and fixed quantities:

| Field | Meaning |
|---|---|
| `sample` | sample name |
| `path_index`, `path`, `scatterer` | FEFF path index, label, and scatterer |
| `degeneracy_theory` | theoretical FEFF path degeneracy |
| `amplitude_factor` | amplitude relative to theoretical coordination |
| `cn_fit` | `degeneracy_theory × amplitude_factor` |
| `reff_A` | FEFF geometric path distance |
| `delr_A`, `delr_error_A` | fitted distance correction and uncertainty |
| `r_fit_A` | `reff_A + delr_A` |
| `sigma2_A2`, `sigma2_error_A2` | Debye–Waller factor and uncertainty |
| `e0_eV`, `e0_error_eV` | `ΔE0` and uncertainty |
| `s02`, `s02_status` | `S0²` and fixed/fitted status |
| `r_factor`, `fit_status`, `notes` | fit metric, review status, and constraint notes |

## Installation and update

Fresh installation:

```powershell
git clone https://github.com/catdaog/artemis-xafs-fit-skill.git `
  "$env:USERPROFILE\.codex\skills\artemis-xafs-fit-skill"
```

Update an existing Git installation:

```powershell
git -C "$env:USERPROFILE\.codex\skills\artemis-xafs-fit-skill" pull --ff-only
```

Alternatively, download the GitHub ZIP and copy the extracted directory to:

```text
~/.codex/skills/artemis-xafs-fit-skill
```

## Invocation example

Use the skill explicitly in Codex:

```text
Use $artemis-xafs-fit-skill to calibrate my foil, determine S0², run a first-shell fit,
and deliver the raw, k-space, R-space, project, audit, and parameter-table files.
```

Codex may also select the skill automatically for Athena, Artemis, FEFF, EXAFS, coordination-number fitting, and numerical R-space export requests.

## Helper scripts

| Script | Purpose |
|---|---|
| `fetch_reference.py` | download and validate CIF/XAS references with URL, SHA256, and provenance |
| `foil_calibrate.py` | list derivative candidates and apply a reviewed calibration feature |
| `suggest_xafs_settings.py` | suggest standard structures and starting k weights from absorber, edge, and scatterers |
| `run_demeter.ps1` | probe and run Windows Demeter in an isolated short-path runtime |
| `demeter_first_shell_fit.pl` | run a fixed-`S0²`, explicit-path first-shell fit with grouped `σ²` |
| `audit_fit_log.py` | audit negative `σ²`, extreme shifts, parameter counts, and high correlations |
| `build_xafs_delivery.py` | build and verify the complete numerical XAFS delivery package |

Probe the local Demeter installation:

```powershell
.\scripts\run_demeter.ps1 -Action probe
```

Build and verify a delivery package:

```powershell
python scripts/build_xafs_delivery.py build `
  --output sample_xafs_delivery `
  --sample "Sample name" `
  --raw raw_scan_01.dat --raw raw_scan_02.dat `
  --processed-chi chi_k.dat `
  --fit-k1 fit_k1.dat --fit-k2 fit_k2.dat --fit-k3 fit_k3.dat `
  --fit-rmag fit_rmag.dat --fit-rre fit_rre.dat --fit-rim fit_rim.dat `
  --parameters fit_parameters.tsv `
  --statistics fit_statistics.tsv `
  --artifact fit.dpj --artifact fit.log --artifact feff.inp --artifact phase.cif `
  --qa audit.json --qa calibration.json --qa model_comparison.csv

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

The builder refuses to overwrite an existing destination. Use a new versioned directory for every rerun.

## Repository layout

```text
artemis-xafs-fit-skill/
├── SKILL.md                              entry point and required invariants
├── agents/openai.yaml                    Codex interface metadata
├── references/
│   ├── workflow.md                       complete standard-to-sample workflow
│   ├── basic-principles.md               EXAFS theory and parameter correlations
│   ├── parameter-constraints.md          limits and acceptance rules
│   ├── deliverables.md                   delivery-package file contract
│   ├── element-guidance.md               elements, edges, standards, and k weights
│   ├── software-and-sample-preparation.md software and transmission-sample preparation
│   ├── demeter-api.md                    Demeter automation interface
│   └── sources.md                        data, CIF, and software source policy
├── scripts/                              reusable tools
└── tests/                                standard-library unit tests
```

## Validation

Run the standard-library tests:

```powershell
python -m unittest discover -s tests -v
```

Run the Codex skill validator:

```powershell
python <skill-creator>/scripts/quick_validate.py .
```

GitHub Actions runs Python compilation and delivery-package tests on every push and pull request.

## Official software and references

- [Demeter](https://bruceravel.github.io/demeter/) — Athena, Artemis, and Hephaestus.
- [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html) — official FEFF downloads.
- [XAFSmass](https://xafsmass.readthedocs.io/) — powder mass, thickness, and edge-step calculations.
- [CatMass](https://web.slac.stanford.edu/coaccess/resources/software) — supported catalysts and complex-composition mass calculations.
- [CLS X-Mass](https://xasdb.lightsource.ca/xafsmass) — browser-based sample/diluent mass calculation.
- Teo and Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, [DOI: 10.1021/ja00505a003](https://doi.org/10.1021/ja00505a003).

Before using an external CIF or XAS data set, verify its phase, measurement conditions, license, landing page, and citation. See [`references/sources.md`](references/sources.md) for the complete source policy.

## License

MIT. See [`LICENSE`](LICENSE).
