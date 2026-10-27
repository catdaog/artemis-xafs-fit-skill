# XAFS Fit Skill · EXAFS + XANES

[![test](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)

**一个 skill，两种拟合：EXAFS 定量配位分析 + XANES 近边模拟与结构拟合。**

`artemis-xafs-fit-skill` 调用本机真实计算程序，保留原始数据、结构来源、输入输出与拟合记录。支持单独运行任一分支，也可结合两者检验同一候选结构。

## 选择拟合类型

| 项目 | EXAFS 拟合 | XANES 近边拟合 |
|---|---|---|
| 主要问题 | 配位数、键长、Debye–Waller 因子及散射路径 | 候选配位构型、局部几何及近边谱形是否匹配 |
| 计算程序 | Athena / Artemis / Demeter + FEFF | FDMNES：Green 多重散射或有限差分 |
| 核心输入 | 数值谱或未加权 χ(k)、处理信息、同边标准样、结构/FEFF 模型 | 能量–吸收数值谱、校准/归一化依据、候选原子结构 |
| 工作方式 | 标样确定 S₀² → 路径核验 → 分阶段拟合 → 参数审查 | 模型建簇 → 收敛检查 → 谱线对齐 → 少量几何参数优化 → 多起点比较 |
| 结果文件 | 可回读 DPJ、k1/k2/k3 与 R1/R2/R3 数值表、参数表和流程记录 | 实验/计算/残差表、参数与模型比较、PNG/SVG、结构、输入及日志 |
| 详细说明 | [EXAFS 中文指南](references/exafs-guide.zh-CN.md) | [XANES / FDMNES 指南](references/xanes-fdmnes.md) |

**近边拟合使用独立流程与交付规则，不需要把 EXAFS 的 S₀²、k/R 窗口或 DPJ 作为前置条件。** 参考谱线性组合（LCF）属于另一种方法，本近边分支尚未实现。

## 快速调用

**EXAFS：**

```text
使用 $artemis-xafs-fit-skill，对我的样品进行 EXAFS 拟合。先用同吸收边、已知配位数的标准样确定 S₀²，再拟合样品，交付可回读的 DPJ、k/R 数值表、参数表和流程记录。
```

**XANES：**

```text
使用 $artemis-xafs-fit-skill，对我的单原子样品进行 FDMNES 近边计算与结构拟合。结合组成和已有 EXAFS 结果建立候选模型，检查收敛并进行多起点比较，交付叠图、残差和可复现文件。
```

## 需要提供什么

- 共同信息：吸收元素/边、样品与文件对应关系、测量状态、列含义、能量校准依据和数值谱；有重复扫描时一并保留。
- EXAFS：尽量提供同边标准样、Athena `.prj`、未加权 χ(k) 及处理参数、CIF/FEFF；继续已有拟合时附 `.fpj`/`.dpj` 和日志。
- XANES：提供归一化 μ(E)，或可用于归一化的 μ(E) 及窗口；原始探测器计数需先按测量模式转换。结构可用 CIF 或显式原子坐标，假设结构应标为候选。

截图可用于解释，实际拟合需要数值数据。没有结构文件时，可先根据材料组成和独立证据建立候选模型。

## 安装与运行

下载 [Release](https://github.com/catdaog/artemis-xafs-fit-skill/releases) 或克隆仓库，将目录命名为 `artemis-xafs-fit-skill`，放入 skills 目录（例如 `~/.codex/skills/`）。在该目录、所用 Python 环境中安装依赖：

```shell
python -m pip install -r requirements.txt -r requirements-xanes.txt
```

EXAFS 需要另行安装 [Demeter](https://bruceravel.github.io/demeter/) / [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html)。XANES 需要从 [FDMNES 官网](https://fdmnes.neel.cnrs.fr/download/)获取程序。本仓库不捆绑这些外部程序。Windows 可使用：

```powershell
.\scripts\run_xanes.ps1 -Mode install -Archive C:\path\fdmnes.zip
.\scripts\run_xanes.ps1 -Mode probe
.\scripts\run_xanes.ps1 -Mode simulate -Config examples\xanes\fe-n4.json -Output C:\work\xanes_sim
.\scripts\run_xanes.ps1 -Mode fit -Config C:\work\xanes.json -Output C:\work\xanes_fit
```

也可用 `FDMNES_EXE` 指向已有程序。完整配置和命令见近边指南；多语言页面提供使用说明，程序参数名和文件名保持一致。

## 结果与验证

v1.4.0 已通过 23 项本地测试，包括真实 FDMNES 合成谱恢复和有限差分计算；GitHub CI 运行无需外部引擎的测试。合成谱测试验证软件执行与参数恢复，不代表真实催化剂结构已被证实。

结构模拟、谱线对齐和结构拟合分别标记；数值收敛后仍需检查残差、参数相关性、边界和不同起点。XANES 匹配不能单独证明单原子分散或唯一结构。

## 文档与示例

- [EXAFS 详细指南（中文）](references/exafs-guide.zh-CN.md)
- [XANES / FDMNES 流程](references/xanes-fdmnes.md)
- [EXAFS 批量流程模板](examples/pipeline.template.json)
- [XANES 示例配置（五原子教学模型）](examples/xanes/fe-n4.json)
- [技能入口与约束](SKILL.md)
- [更新日志](CHANGELOG.md)

许可：本 skill 源码采用 [MIT](LICENSE)；外部计算程序适用各自的许可条款。

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)
