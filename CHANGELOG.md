# 更新日志 / Changelog

## v1.5.0 — 2026-11-11

- 新增 NumPy Morlet EXAFS 小波分支，默认 κ=10、σ=1，明确母小波、零均值校正、尺度到 R 的换算与归一化定义。
- 新增 Origin 可导入的纯数值幅值矩阵（行 R、列 k）、独立共享归一化矩阵、复系数、坐标/参数记录和数值读回核验。
- 支持独立 χ(k) 处理、统一网格批量比较，以及 χ实验−χ拟合残差的小波分析；输入已加 k 权重时显式去权。
- 新增 Windows 启动器、可选 NumPy 依赖、小波配置模板、方法指南及拟合后可选小波调用；WT 与九文件拟合交付分别核验。
- Add reproducible Morlet EXAFS WT with explicit κ=10/σ=1 convention, Origin matrices, complex residual analysis, shared normalization and readback verification. Standalone WT does not require a fitted model or DPJ.

- 整理首页，以并列表格展示 EXAFS 与 XANES 两种拟合的输入、程序、流程和交付。
- 新增德语、日语和法语完整快速使用页；中文、英文同步采用相同结构和语言导航。
- 保留原有中英文 EXAFS 长篇说明为详细指南，并修正迁移后的相对链接。
- 将多语言 README 和可选小波依赖清单纳入分发包。
- Reorganizes the two-workflow homepage, adds German/Japanese/French quick starts, and preserves the detailed Chinese/English EXAFS guides.

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
