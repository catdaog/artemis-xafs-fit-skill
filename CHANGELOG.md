# 更新日志 / Changelog

## v1.4.0 — 2026-10-27

### 新增 / Added

- FDMNES XANES 近边模拟与结构拟合分支，整合进现有 XAFS skill 的任务路由。
- 真实引擎的独立目录运行、可核验缓存、超时/计算次数限制、程序与数据哈希、原生输出和错误日志。
- 已核验 CIF → 显式 Cartesian 团簇导出，保留吸收原子、位点、周期平移和来源信息。
- 模拟、半径检查、固定几何能量对齐、受限几何优化、多起点和模型比较。
- 数值谱与残差、参数表、条件局部误差/相关性、PNG/SVG 叠图、最优结构和可复现记录。
- Windows 启动器、`requirements-xanes.txt`、示例配置、近边指南和真实引擎回归测试。

### 行为 / Behavior

- 近边分支使用独立交付规则，不强制 S₀²、k/R 窗口或 DPJ；原有 EXAFS 流程保留。
- 明确区分模拟、谱线对齐、结构拟合及合成测试数据。
- 数值收敛保留科学审查状态，报告起点依赖、边界、秩亏和高相关性等问题。
- 发布包加入近边依赖清单、示例和本更新日志；FDMNES 程序仍从官方渠道单独安装。

### 验证与限制 / Validation and limitations

- 23 项测试通过，包含既有 EXAFS 测试和真实 FDMNES 合成谱恢复测试；已运行 Green 和有限差分模式。
- 合成真值 Fe–N = 2.030 Å、能移 0.600 eV，恢复约 2.029999 Å、0.600002 eV。
- 该五原子模型仅用于软件测试，不能代表某种催化剂的真实位点。自旋/多重态、任意电子组态及混合位点比例尚未自动反演。
- FDMNES-backed XANES simulation, geometry refinement and auditable exports are now available alongside EXAFS. Numerical convergence is not scientific acceptance; synthetic recovery is not experimental validation.

## v1.3.0 — 2026-10-23

- 增加 COD 检索、CIF 检查/生成/超胞/替换/空位、来源记录和 K 边 CIF → FEFF 团簇导出。
- 增加标准样确定 S₀² → 审计 → 样品批量拟合入口，附 MoO₃/MoO₂ 配置模板。
- 明确固定与拟合 CN、schema v3 状态/误差字段；DPJ 必须真实回读并核对数值导出。
- 原 release 记录 13 项测试通过；科学接受仍需人工审查。
