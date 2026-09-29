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
- 默认九文件精简交付：DPJ、k1/k2/k3、R1/R2/R3、一个参数表和一个拟合流程 TXT；
- 数值网格、残差和参数算术关系的自动验证；完整来源与审计包可按需启用。

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

## 使用前需要上传什么文件

最稳妥的原则是：**原始扫描负责可追溯性，Athena 工程负责复现数据处理，Artemis 工程负责复现拟合，CIF/FEFF 文件负责复现结构模型。** 如果文件齐全，建议将下列内容按文件夹打包成一个 `.zip` 上传；不要只上传拟合截图。

### 不同任务的最小文件组合

| 使用场景 | 必须上传 | 强烈建议同时上传 | 缺失时的影响 |
|---|---|---|---|
| 从原始数据开始完整拟合 | 样品原始扫描、同吸收边参考箔/标准样、列说明和实验信息、候选结构 CIF | Athena `.prj`（如已处理）、全部重复扫描、beamline 记录 | 没有同边标准样时，能量校准与 `S0²`/绝对 CN 的可信度下降 |
| 已经在 Athena 中处理完成 | Athena `.prj`、候选结构 CIF | 原始扫描、参考箔/标准样、Athena 导出的未加权 `χ(k)` | 只有 `.prj` 而没有原始扫描时，仍可复核多数处理步骤，但原始采集与部分校准问题不能完全追溯 |
| 继续已有 Artemis 拟合 | Artemis `.fpj` 或 `.dpj`、`fit.log`、对应 CIF/FEFF 目录 | Athena `.prj`、原始扫描、已有参数表、注明需要继续的 fit 快照 | 缺少 FEFF 路径或工程文件时，无法可靠恢复路径选择、约束和相关性 |
| 只有 Athena 导出数据 | 未加权 `k, χ(k)` 数值文件、Athena 处理参数、候选结构 CIF/FEFF 模型 | 归一化 `μ(E)`、数值 `χ(R)`、数据来源与许可信息 | 不能完整重查能量校准、扫描合并、归一化和 AUTOBK 背景扣除 |
| 分析论文或外部数据库数据 | 可下载的原始数值文件、来源/DOI、样品与测量条件 | 作者提供的工程文件、CIF、许可证或复用说明 | 只有论文图片时只能做定性判断，不能声称完成可重复的定量拟合 |

### 1. 原始光谱：优先上传什么格式

推荐优先级如下：

1. **`.xdi`：首选。** 它通常同时保存能量、探测器列、单位和实验元数据，最利于自动检查。
2. **beamline 原始 `.txt`、`.dat` 或 `.csv`：完全可以。** 必须保留原始表头、全部数据行、原始顺序、分隔符和单位，不要手工重采样、删点、平滑或减少小数位。
3. **Athena `.prj`：强烈推荐，但最好与原始扫描一起上传。** `.prj` 适合复现校准、合并、归一化和背景扣除；它不能总是替代未经修改的 beamline 原始文件。
4. **`.xlsx`：仅在原始文本确实不可用时接受。** 每列必须有唯一名称和单位，不能使用合并单元格、图表读数或隐藏的手工公式作为唯一数据来源。

原始文件至少应包含以下列：

| 测量模式 | 最少列 | 推荐附加列/说明 |
|---|---|---|
| 透射 | `energy_eV`, `I0`, `It` | `Iref` 或参考箔通道、各电离室含义、任何增益切换记录 |
| 荧光 | `energy_eV`, `I0`, `If`，或每个探测器通道 | `Iref`、死时间校正状态、被排除的通道、总和列的计算方式 |
| 已计算的 `μ(E)` | `energy_eV`, `mu` | 如仍有 `I0/It/If`，请一并保留；说明 `mu` 的计算式与校正步骤 |
| Athena 导出的 EXAFS | `k_A^-1`, **未加权** `chi(k)` | 可附加 `kchi`, `k2chi`, `k3chi`，但不要只给一条加权曲线 |

文件名应能明确区分样品、扫描编号和参考箔，例如 `sampleA_scan01.xdi`、`sampleA_scan02.xdi`、`Fe_foil_scan01.xdi`。所有重复扫描都应上传，包括后来判为异常的扫描；只需在元数据中标记排除原因，不要静默删除。

### 2. 标准样和参考文件

若目标包括绝对配位数，必须尽可能提供与样品**相同吸收边**、在相同 beamtime 或相同单色器状态下测得的金属箔或已知配位标准样：

- 能量校准用参考箔的原始扫描或包含该参考通道的 Athena `.prj`；
- 用于确定 `S0²` 的标准样原始扫描、结构信息和已知配位数；
- 标准样和未知样的能量校准约定、`k`/`R` 拟合范围和窗口函数说明。

如果没有合适的同边标准样，可以使用有依据的文献值或受约束的 `S0²`，但必须标记来源并进行敏感性分析；此时不应把拟合 CN 报告成不受模型影响的绝对值。

### 3. Athena 已处理文件应怎样上传

如果已经在 Athena 中完成校准、合并或背景扣除，建议上传：

- Athena 工程 `.prj`；
- 生成该工程的全部原始扫描；
- Athena 导出的未加权 `χ(k)` 文本文件；
- 如有，归一化 `μ(E)` 与数值 `χ(R)` 导出；
- 处理参数：`E0`、归一化区间、`Rbkg`、`kmin/kmax`、`dk`、窗口类型和合并规则。

**只有 Athena 导出的 `.txt/.dat` 也可以开始拟合**，但最低要求是两列数值 `k` 和未加权 `χ(k)`，并同时给出上述处理参数。只给 `k²χ(k)`、`|χ(R)|` 或图片不足以完整恢复拟合输入。

### 4. 继续已有 Artemis 工程时

请尽量将下列文件一起上传：

- Artemis `.fpj` 文件，或完整 `.dpj` 工程目录；
- 对应的 `fit.log`，以及已有 `summary.tsv`、CSV/XLSX 参数表或拟合报告；
- 与当前工程完全对应的 CIF、`feff.inp`、`paths.dat`、`feffNNNN.dat`，最好直接上传完整 FEFF 计算目录；
- Athena `.prj` 与原始扫描；
- 一份简短说明，写明需要继续的是哪一个 fit、哪些参数固定、哪些路径启用，以及是否存在未保存的手工修改。

不要只上传 `.fpj/.dpj` 的截图或复制出的参数表，因为它们不能恢复 GDS 约束、路径映射、相关矩阵和实际残差。

### 5. 结构与实验元数据

结构模型优先上传实验相对应的 `.cif`。若没有 CIF，请提供材料化学式、物相、空间群、晶胞参数、掺杂/缺陷/表面位点假设及其来源。若使用表面、缺陷或无序的显式模型，应与实验平均结构 CIF 分开命名，避免把理论模型误当成实验精修结构。

另外提供 `metadata.csv` 或 `README.txt`，至少说明：

- 样品名称与文件名映射、吸收元素和吸收边；
- beamline、测量日期、透射/荧光模式、温度、气氛或电化学条件；
- 各数据列定义、单位、参考箔位置与能量校准约定；
- 重复扫描的合并规则、异常扫描和坏通道的排除理由；
- 预期比较的问题，例如 CN、键长、无序度、不同样品共用参数或多边联合拟合。

### 6. 不应单独作为拟合输入的文件

下列内容可以作为辅助说明，但不能替代数值数据和工程文件：

- PNG/JPG 截图、PDF 图、Origin 图或只有图层而没有导出数值表的 `.opju`；
- Word/PowerPoint 中的曲线或手工复制、四舍五入后的数据表；
- 只有 `|χ(R)|` 而没有实部、虚部或原始 `χ(k)` 的曲线；
- 只有一条 `k²χ(k)`/`k³χ(k)`，却没有未加权 `χ(k)`；
- 只有 CIF 而没有光谱，或只有光谱而没有结构/FEFF 模型。

### 7. 推荐上传目录

```text
sample_xafs_input/
├── 01_raw/
│   ├── sampleA_scan01.xdi
│   ├── sampleA_scan02.xdi
│   └── reference_foil_scan01.xdi
├── 02_athena/
│   ├── sample_and_foil.prj
│   └── sampleA_chik.dat
├── 03_existing_fit/
│   ├── sampleA.fpj                 # 或完整 .dpj 目录
│   ├── fit.log
│   └── summary.tsv
├── 04_structure_and_feff/
│   ├── phase.cif
│   ├── feff.inp
│   └── feffNNNN.dat
├── metadata.csv
└── README.txt
```

若只能上传一个压缩包，优先保证顺序为：**原始样品扫描 + 同边参考/标准样 + 元数据 + CIF/FEFF + Athena `.prj` + Artemis 工程**。

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
| 10. 打包与验证 | 构建默认九文件目录并复核网格、残差和参数关系 | DPJ 已载入检查，k/R 网格和 `R=Reff+ΔR` 正确 | DPJ、k1/2/3、R1/2/3、一个参数表、`FIT_WORKFLOW.txt` |

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

一次实际执行的拟合必须输出数值文件，而不是只有图片或文字总结。默认只交付九个文件：

```text
<sample>_xafs_delivery/
├── <final-fit>.dpj
├── k1_data_fit.csv
├── k2_data_fit.csv
├── k3_data_fit.csv
├── R1_data_fit.csv
├── R2_data_fit.csv
├── R3_data_fit.csv
├── fit_parameters.tsv
└── FIT_WORKFLOW.txt
```

`k1/k2/k3` 文件分别保存 k¹/k²/k³ 加权的数据、拟合和残差。`R1/R2/R3` 不是幅值/实部/虚部的简称，而是同一最终拟合在 k 权重 1、2、3 下的 R 空间变换；每个 R 文件同时保存：

- `data_mag`, `fit_mag`, `residual_mag`；
- `data_real`, `fit_real`, `residual_real`；
- `data_imag`, `fit_imag`, `residual_imag`。

Demeter 的 R-space magnitude residual 是复数残差的模：

```text
|χdata(R) - χfit(R)|
```

它一般不等于 `|χdata(R)| - |χfit(R)|`。`FIT_WORKFLOW.txt` 记录输入、校准和预处理依据、FEFF 路径、固定/拟合参数、k/R 窗口、模型选择、导出步骤以及 DPJ 的重新打开/载入检查，让最终结果可追溯。

原始扫描、CIF、`feff.inp`、日志、哈希和 QA 文件仍需在工作目录中保留，但默认不重复交付；只有用户要求完整审计材料时才使用 `--profile audit`。详细规范见 [`references/deliverables.md`](references/deliverables.md)。

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

打包版本可从 [GitHub Releases](https://github.com/catdaog/artemis-xafs-fit-skill/releases) 下载。仓库同时将 `@catdaog/artemis-xafs-fit-skill` 发布到 GitHub Packages；npm 包只是分发载体，安装后的技能目录仍需复制到 Codex skills 目录。

## 调用示例

在 Codex 中直接调用：

```text
使用 $artemis-xafs-fit-skill 校准我的金属箔，确定 S0²，运行第一壳层拟合，
并按默认九文件格式输出 DPJ、k1/k2/k3、R1/R2/R3、一个参数表和拟合流程 TXT。
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
| `build_xafs_delivery.py` | 默认构建并验证九文件精简交付；`--profile audit` 生成完整审计包 |

探测本机 Demeter：

```powershell
.\scripts\run_demeter.ps1 -Action probe
```

构建标准交付包：

```powershell
python scripts/build_xafs_delivery.py build `
  --output sample_xafs_delivery `
  --sample "Sample name" `
  --artemis-project fit.dpj `
  --fit-k1 fit_k1.dat --fit-k2 fit_k2.dat --fit-k3 fit_k3.dat `
  --fit-r1-mag fit_r1_mag.dat --fit-r1-re fit_r1_re.dat --fit-r1-im fit_r1_im.dat `
  --fit-r2-mag fit_r2_mag.dat --fit-r2-re fit_r2_re.dat --fit-r2-im fit_r2_im.dat `
  --fit-r3-mag fit_r3_mag.dat --fit-r3-re fit_r3_re.dat --fit-r3-im fit_r3_im.dat `
  --parameters fit_parameters.tsv `
  --workflow-source FIT_WORKFLOW.txt `
  --project-check "已用匹配的 Demeter project loader 成功载入"

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

打包器拒绝覆盖已有目标目录。重新拟合时请创建带版本号的新目录。完整原始数据、FEFF/CIF、日志、统计和 QA 材料可用 `--profile audit` 生成。

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
- a default nine-file delivery: DPJ, k1/k2/k3, R1/R2/R3, one parameter table, and one workflow TXT;
- automatic verification of numerical grids, residuals, and derived-parameter arithmetic, with an optional extended audit package.

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

## What to upload before fitting

The safest rule is: **raw scans provide traceability, an Athena project reproduces data processing, an Artemis project reproduces the fit, and CIF/FEFF files reproduce the structural model.** When possible, place the items below in one `.zip` archive. Do not upload fit screenshots as the only input.

### Minimum package for each use case

| Use case | Required | Strongly recommended | Consequence if missing |
|---|---|---|---|
| Start a complete fit from raw data | sample raw scans, same-edge reference foil/standard, column definitions and experiment metadata, candidate CIF | Athena `.prj` if processing has begun, every repeat scan, beamline notes | without a same-edge standard, energy calibration and `S0²`/absolute CN are less secure |
| Processing is complete in Athena | Athena `.prj`, candidate CIF | raw scans, reference foil/standard, Athena-exported unweighted `χ(k)` | a `.prj` alone supports most processing checks, but not a full audit of acquisition and every calibration issue |
| Continue an existing Artemis fit | Artemis `.fpj` or `.dpj`, `fit.log`, matching CIF/FEFF directory | Athena `.prj`, raw scans, current parameter table, identification of the intended fit snapshot | without FEFF paths or the project, path selection, constraints, and correlations cannot be recovered reliably |
| Only Athena exports are available | numerical unweighted `k, χ(k)`, Athena processing settings, candidate CIF/FEFF model | normalized `μ(E)`, numerical `χ(R)`, provenance and license | energy calibration, merging, normalization, and AUTOBK cannot be fully re-audited |
| Analyze published or external data | downloadable numerical data, source/DOI, sample and measurement conditions | author project files, CIF, license or reuse statement | a paper figure alone permits only qualitative assessment, not a reproducible quantitative fit |

### 1. Raw spectra: preferred formats

Use this order of preference:

1. **`.xdi`: preferred.** It commonly preserves energy, detector columns, units, and experimental metadata in one machine-readable file.
2. **Beamline-native `.txt`, `.dat`, or `.csv`: fully acceptable.** Keep the original header, every row, row order, delimiter, and unit. Do not manually resample, delete points, smooth the spectrum, or reduce numerical precision.
3. **Athena `.prj`: strongly recommended, but preferably together with raw scans.** It helps reproduce calibration, merging, normalization, and background removal, but it does not always replace untouched beamline files.
4. **`.xlsx`: acceptable only when the original text file is unavailable.** Every column must have a unique name and unit; merged cells, values read from a chart, and hidden manual formulas must not be the sole data source.

At minimum, the raw file should contain:

| Measurement mode | Minimum columns | Recommended additions |
|---|---|---|
| Transmission | `energy_eV`, `I0`, `It` | `Iref` or foil channel, ion-chamber definitions, gain-change records |
| Fluorescence | `energy_eV`, `I0`, `If`, or individual detector channels | `Iref`, dead-time correction status, excluded channels, definition of any summed channel |
| Precomputed `μ(E)` | `energy_eV`, `mu` | retain `I0/It/If` when available and state the equation and corrections used to calculate `mu` |
| Athena EXAFS export | `k_A^-1`, **unweighted** `chi(k)` | `kchi`, `k2chi`, and `k3chi` may be included, but do not provide only one weighted curve |

File names should distinguish the sample, repeat, and reference, for example `sampleA_scan01.xdi`, `sampleA_scan02.xdi`, and `Fe_foil_scan01.xdi`. Upload every repeat, including scans later judged abnormal. Mark the exclusion and its reason in metadata instead of silently deleting the file.

### 2. Standards and references

If absolute coordination numbers are a target, provide a metal foil or known-coordination standard measured at the **same absorption edge**, preferably during the same beamtime or under the same monochromator state:

- the raw reference-foil scan or an Athena `.prj` that contains the reference channel;
- raw data and structural information for the standard used to determine `S0²`, including its known coordination number;
- the calibration convention, `k`/`R` fit ranges, and window used for both the standard and unknown sample.

If no suitable same-edge standard exists, a justified literature value or constrained `S0²` may be used only with a cited source and sensitivity test. The resulting CN must not be presented as a model-independent absolute value.

### 3. Uploading Athena-processed data

If calibration, merging, or background removal has already been completed in Athena, upload:

- the Athena `.prj` project;
- every raw scan used to create it;
- an Athena text export of unweighted `χ(k)`;
- normalized `μ(E)` and numerical `χ(R)` exports when available;
- processing settings: `E0`, normalization ranges, `Rbkg`, `kmin/kmax`, `dk`, window type, and merge rule.

**An Athena-exported `.txt` or `.dat` file is sufficient to begin a fit** when it contains at least two numerical columns, `k` and unweighted `χ(k)`, and the processing settings above are supplied. A lone `k²χ(k)`, `|χ(R)|`, or image is not enough to reconstruct the full fitting input.

### 4. Continuing an Artemis project

Upload as many of these files together as possible:

- the Artemis `.fpj` file or complete `.dpj` project directory;
- its exact `fit.log`, plus any existing `summary.tsv`, CSV/XLSX parameter table, or fit report;
- the CIF, `feff.inp`, `paths.dat`, and `feffNNNN.dat` files that match the project; the complete FEFF calculation directory is best;
- the Athena `.prj` and original raw scans;
- a short note identifying the fit to continue, fixed parameters, enabled paths, and any unsaved manual changes.

Do not provide only a screenshot of the `.fpj/.dpj` project or a copied parameter table. Those cannot restore GDS constraints, path mappings, the correlation matrix, or the actual residuals.

### 5. Structural and experimental metadata

Prefer an experimental `.cif` that matches the measured phase. If no CIF exists, provide the chemical composition, phase, space group, unit cell, dopant/defect/surface-site hypothesis, and source. Name explicit surface, defect, or disordered models separately from the experimental average structure so that a theoretical model is not mistaken for an experimentally refined structure.

Also include a `metadata.csv` or `README.txt` containing at least:

- the sample-to-file mapping, absorber, and absorption edge;
- beamline, measurement date, transmission/fluorescence mode, temperature, atmosphere, or electrochemical condition;
- column definitions, units, reference-foil position, and calibration convention;
- repeat-merging rule and reasons for excluding scans or detector channels;
- the scientific comparison requested, such as CN, bond length, disorder, shared parameters across samples, or a multi-edge joint fit.

### 6. Files that are not sufficient on their own

These items may accompany the data, but cannot replace numerical inputs and project files:

- PNG/JPG screenshots, PDF figures, Origin plots, or an `.opju` containing plots without exported numerical worksheets;
- curves embedded in Word/PowerPoint or manually copied and rounded tables;
- `|χ(R)|` without the real/imaginary components or the original `χ(k)`;
- only one `k²χ(k)`/`k³χ(k)` curve when unweighted `χ(k)` is unavailable;
- a CIF without spectra, or spectra without a structural/FEFF model.

### 7. Recommended upload layout

```text
sample_xafs_input/
├── 01_raw/
│   ├── sampleA_scan01.xdi
│   ├── sampleA_scan02.xdi
│   └── reference_foil_scan01.xdi
├── 02_athena/
│   ├── sample_and_foil.prj
│   └── sampleA_chik.dat
├── 03_existing_fit/
│   ├── sampleA.fpj                 # or the complete .dpj directory
│   ├── fit.log
│   └── summary.tsv
├── 04_structure_and_feff/
│   ├── phase.cif
│   ├── feff.inp
│   └── feffNNNN.dat
├── metadata.csv
└── README.txt
```

If only one archive can be uploaded, prioritize: **raw sample scans + same-edge reference/standard + metadata + CIF/FEFF + Athena `.prj` + Artemis project**.

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
| 10. Package and verify | Build the default nine-file directory and verify grids, residuals, and arithmetic | DPJ load check, valid k/R grids, and `R=Reff+ΔR` | DPJ, k1/2/3, R1/2/3, one table, `FIT_WORKFLOW.txt` |

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

Every executed fit must return numerical files, not only plots or narrative. The default delivery contains only nine files:

```text
<sample>_xafs_delivery/
├── <final-fit>.dpj
├── k1_data_fit.csv
├── k2_data_fit.csv
├── k3_data_fit.csv
├── R1_data_fit.csv
├── R2_data_fit.csv
├── R3_data_fit.csv
├── fit_parameters.tsv
└── FIT_WORKFLOW.txt
```

The k1/k2/k3 files contain k¹/k²/k³-weighted data, fit, and residual. R1/R2/R3 are not aliases for magnitude/real/imaginary; they are the R-space transforms at k weights 1, 2, and 3. Each R file contains magnitude, real, and imaginary data, fit, and residual columns. Demeter's R-space magnitude residual is the magnitude of the complex residual,

```text
|χdata(R) - χfit(R)|
```

and is generally not equal to `|χdata(R)| - |χfit(R)|`. `FIT_WORKFLOW.txt` records the inputs, calibration and preprocessing basis, FEFF paths, fixed/fitted parameters, k/R windows, model decision, exports, and the DPJ reopen/load check.

Keep raw scans, CIF, `feff.inp`, logs, hashes, and QA records in the working directory, but do not duplicate them in the default delivery. Use `--profile audit` only when the user requests the extended provenance package. See [`references/deliverables.md`](references/deliverables.md) for the exact file and column contract.

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
and deliver the default DPJ, k1/k2/k3, R1/R2/R3, one parameter table, and workflow TXT.
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
| `build_xafs_delivery.py` | build and verify the default nine-file delivery; use `--profile audit` for the extended package |

Probe the local Demeter installation:

```powershell
.\scripts\run_demeter.ps1 -Action probe
```

Build and verify a delivery package:

```powershell
python scripts/build_xafs_delivery.py build `
  --output sample_xafs_delivery `
  --sample "Sample name" `
  --artemis-project fit.dpj `
  --fit-k1 fit_k1.dat --fit-k2 fit_k2.dat --fit-k3 fit_k3.dat `
  --fit-r1-mag fit_r1_mag.dat --fit-r1-re fit_r1_re.dat --fit-r1-im fit_r1_im.dat `
  --fit-r2-mag fit_r2_mag.dat --fit-r2-re fit_r2_re.dat --fit-r2-im fit_r2_im.dat `
  --fit-r3-mag fit_r3_mag.dat --fit-r3-re fit_r3_re.dat --fit-r3-im fit_r3_im.dat `
  --parameters fit_parameters.tsv `
  --workflow-source FIT_WORKFLOW.txt `
  --project-check "Loaded successfully with the matching Demeter project loader"

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

The builder refuses to overwrite an existing destination. Use a new versioned directory for every rerun. Add `--profile audit` when raw inputs, FEFF/CIF, logs, statistics, hashes, and QA files are explicitly requested.

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
