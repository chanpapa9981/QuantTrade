# QuantTrade 项目工作记录表

> 目的：持续记录项目从 0 到 1 的搭建过程，让后续任何时候都能清晰回答这几个问题：
>
> - 现在做到哪一步了？
> - 为什么这样设计？
> - 每一阶段产出了什么？
> - 哪些已经完成，哪些还没完成？
> - 下一步应该做什么？

> 使用规则：
>
> - 后续开发默认持续更新本文件；
> - 每完成一个真实能力，就补一条记录；
> - 每遇到关键设计选择，就记录在“决策日志”；
> - 每发现风险或阻塞，就记录在“风险与阻塞”。

---

## 1. 项目概览

| 字段 | 内容 |
| :--- | :--- |
| 项目名称 | QuantTrade |
| 项目类型 | 个人自动化交易系统（ATS） |
| 开发基线 | [README_DEV.md](/Users/andy/Documents/QuantTrade/README_DEV.md) |
| 原始需求 | [README.md](/Users/andy/Documents/QuantTrade/README.md) |
| 当前阶段 | 阶段 2：数据层与完整回测 |
| 当前状态 | 进行中 |
| 默认技术方向 | Python + DuckDB + YAML + Web Dashboard + Docker |
| 目标环境 | Mac mini |

---

## 2. 总体阶段表

| 阶段 | 名称 | 目标 | 预计产出 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 0 | 需求整理 | 把理念型需求整理成开发型说明书 | 开发基线文档 | 已完成 |
| 1 | 项目骨架 | 搭建目录结构、配置、CLI、核心模块骨架 | 可运行的最小链路 | 已完成 |
| 2 | 数据层 | 导入历史行情并落库到 DuckDB | 可查询的本地行情库 | 进行中 |
| 3 | 回测引擎 | 基于历史数据跑完整回测 | 回测结果与核心指标 | 进行中 |
| 4 | 风控完善 | 完成账户级与标的级风控规则 | 风控拦截与风控日志 | 未开始 |
| 5 | 模拟执行 | 完成订单、成交、持仓、账户状态变更 | 模拟盘闭环 | 未开始 |
| 6 | Dashboard | 展示参数、日志、净值、持仓、策略状态 | 基础 Web 面板 | 未开始 |
| 7 | Schwab 接入 | 实现认证、账户同步、基础下单能力 | 实盘基础接入 | 未开始 |
| 8 | 通知与告警 | 推送交易动作与风险事件 | 手机通知闭环 | 未开始 |
| 9 | 稳定性增强 | 断网重连、状态对账、异常恢复 | 可试运行版本 | 未开始 |

---

## 3. 工作分解表（WBS）

| 编号 | 模块 | 任务 | 说明 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| W-001 | 文档 | 整理开发基线文档 | 从原始 README 提炼为开发版说明书 | 已完成 |
| W-002 | 基础设施 | 初始化 Python 项目结构 | 建立 `src`、`configs`、`tests` 等目录 | 已完成 |
| W-003 | 配置系统 | 实现配置加载器 | 支持从配置文件读取系统参数 | 已完成 |
| W-004 | 核心域模型 | 定义市场、账户、仓位、信号类型 | 作为后续模块共享模型 | 已完成 |
| W-005 | 策略层 | 搭建 ATR-DTF 首版策略 | 支持单步信号生成 | 已完成 |
| W-006 | 风控层 | 搭建风控引擎首版 | 支持基础账户级拦截 | 已完成 |
| W-007 | 执行层 | 搭建模拟执行器首版 | 支持 entry / exit 模拟执行 | 已完成 |
| W-008 | 回测层 | 搭建单步回测链路 | 跑通策略 -> 风控 -> 执行 | 已完成 |
| W-009 | 工具层 | 建立 CLI 入口 | 支持 `doctor` 与 `run-sample` | 已完成 |
| W-010 | 测试 | 增加基础单元测试 | 配置与 ATR-DTF 基础测试 | 已完成 |
| W-011 | 数据层 | 设计行情表结构 | 明确 `bars` 等表字段 | 已完成 |
| W-012 | 数据层 | 实现 CSV / API 导入 | 导入历史行情到 DuckDB | 已完成 |
| W-013 | 回测层 | 实现历史序列回测 | 从单步扩展到多 bar 回放 | 已完成 |
| W-014 | 回测层 | 输出绩效指标 | 计算收益、回撤、Sharpe 等 | 已完成 |
| W-015 | 风控层 | 完善标的级风控 | 滑点、流动性、权重保护 | 未开始 |
| W-016 | 执行层 | 完善订单模型 | 挂单、撤单、成交、对账 | 进行中 |
| W-017 | UI | 建立 Dashboard 原型 | 参数台、日志台、净值图 | 未开始 |
| W-018 | 券商接入 | 集成 Schwab OAuth2 | 完成认证与续期 | 未开始 |
| W-019 | 券商接入 | 实盘状态同步 | 读取账户、仓位、订单 | 未开始 |
| W-020 | 通知 | 集成 Telegram/微信 | 推送交易与风控消息 | 未开始 |

---

## 4. 当前已完成内容

### 4.1 文档与基线

| 内容 | 路径 | 结果 |
| :--- | :--- | :--- |
| 原始需求文档保留 | [README.md](/Users/andy/Documents/QuantTrade/README.md) | 未覆盖 |
| 开发版基线文档 | [README_DEV.md](/Users/andy/Documents/QuantTrade/README_DEV.md) | 已建立 |
| 项目工作记录表 | [PROJECT_WORKLOG.md](/Users/andy/Documents/QuantTrade/PROJECT_WORKLOG.md) | 已建立 |

### 4.2 已落地代码

| 模块 | 路径 | 说明 |
| :--- | :--- | :--- |
| CLI | [src/quanttrade/cli.py](/Users/andy/Documents/QuantTrade/src/quanttrade/cli.py) | 命令行入口 |
| 应用装配 | [src/quanttrade/app.py](/Users/andy/Documents/QuantTrade/src/quanttrade/app.py) | 系统初始化与样例运行 |
| 配置加载 | [src/quanttrade/config/loader.py](/Users/andy/Documents/QuantTrade/src/quanttrade/config/loader.py) | 读取示例配置 |
| 配置模型 | [src/quanttrade/config/models.py](/Users/andy/Documents/QuantTrade/src/quanttrade/config/models.py) | 配置数据结构 |
| 核心类型 | [src/quanttrade/core/types.py](/Users/andy/Documents/QuantTrade/src/quanttrade/core/types.py) | 市场、账户、仓位、信号 |
| ATR-DTF 策略 | [src/quanttrade/strategies/atr_dtf.py](/Users/andy/Documents/QuantTrade/src/quanttrade/strategies/atr_dtf.py) | 单步策略逻辑 |
| 风控引擎 | [src/quanttrade/risk/engine.py](/Users/andy/Documents/QuantTrade/src/quanttrade/risk/engine.py) | 基础风控校验 |
| 模拟执行 | [src/quanttrade/execution/simulator.py](/Users/andy/Documents/QuantTrade/src/quanttrade/execution/simulator.py) | 模拟进出场 |
| 回测引擎 | [src/quanttrade/backtest/engine.py](/Users/andy/Documents/QuantTrade/src/quanttrade/backtest/engine.py) | 单步回测链路 |
| 数据目录准备 | [src/quanttrade/data/storage.py](/Users/andy/Documents/QuantTrade/src/quanttrade/data/storage.py) | 初始化数据路径 |
| 数据表结构 | [src/quanttrade/data/schema.py](/Users/andy/Documents/QuantTrade/src/quanttrade/data/schema.py) | 建立 `bars` 表 |
| 数据仓储 | [src/quanttrade/data/repository.py](/Users/andy/Documents/QuantTrade/src/quanttrade/data/repository.py) | 读写历史行情 |
| CSV 导入 | [src/quanttrade/data/importer.py](/Users/andy/Documents/QuantTrade/src/quanttrade/data/importer.py) | 导入 OHLCV 历史数据 |
| 指标预处理 | [src/quanttrade/data/indicators.py](/Users/andy/Documents/QuantTrade/src/quanttrade/data/indicators.py) | 计算 Donchian / ATR / ADX |
| 模拟执行 | [src/quanttrade/execution/simulator.py](/Users/andy/Documents/QuantTrade/src/quanttrade/execution/simulator.py) | 统一处理成交、现金、仓位、已实现盈亏 |

### 4.3 配置与测试

| 内容 | 路径 | 结果 |
| :--- | :--- | :--- |
| 示例配置 | [configs/settings.example.yaml](/Users/andy/Documents/QuantTrade/configs/settings.example.yaml) | 已建立 |
| 项目配置 | [pyproject.toml](/Users/andy/Documents/QuantTrade/pyproject.toml) | 已建立 |
| 配置测试 | [tests/test_config_loader.py](/Users/andy/Documents/QuantTrade/tests/test_config_loader.py) | 通过 |
| 策略测试 | [tests/test_atr_dtf.py](/Users/andy/Documents/QuantTrade/tests/test_atr_dtf.py) | 通过 |
| 数据与回测测试 | [tests/test_data_import_and_backtest.py](/Users/andy/Documents/QuantTrade/tests/test_data_import_and_backtest.py) | 已建立 |
| 样例行情文件 | [examples/sample_aapl_daily.csv](/Users/andy/Documents/QuantTrade/examples/sample_aapl_daily.csv) | 已建立 |

---

## 5. 验证记录

| 日期 | 验证项 | 命令 | 结果 |
| :--- | :--- | :--- | :--- |
| 2026-03-27 | 代码编译检查 | `python3 -m compileall src` | 通过 |
| 2026-03-27 | 配置与应用检查 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml doctor` | 通过 |
| 2026-03-27 | 样例策略链路 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml run-sample` | 通过 |
| 2026-03-27 | 单元测试 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-27 | 历史数据导入 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml import-csv --csv examples/sample_aapl_daily.csv --symbol AAPL --timeframe 1d` | 通过 |
| 2026-03-27 | 完整历史回测 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml backtest --symbol AAPL --timeframe 1d --initial-equity 100000` | 通过 |
| 2026-03-27 | 回测结果导出 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml backtest --symbol AAPL --timeframe 1d --initial-equity 100000 --output var/reports/aapl-backtest.json` | 通过 |
| 2026-03-27 | 账户状态闭环增强 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |

---

## 6. 决策日志

| 日期 | 决策 | 原因 | 影响 |
| :--- | :--- | :--- | :--- |
| 2026-03-27 | 保留原始 README，不覆盖 | 原文更像愿景说明，需保留原始意图 | 新增开发基线文档 |
| 2026-03-27 | 新增 `README_DEV.md` 作为开发基线 | 便于后续按工程方式推进 | 统一后续开发依据 |
| 2026-03-27 | 首版优先做可运行骨架 | 先把策略、风控、执行、回测链路打通 | 后续业务功能更易迭代 |
| 2026-03-27 | 首版尽量避免外部依赖 | 当前环境未预装 `PyYAML`、`pytest` | 提升开箱可运行性 |
| 2026-03-27 | 数据层先使用可切换后端设计 | 当前环境缺少 `duckdb` 依赖，但不能阻塞真实功能开发 | 先交付可运行数据链路，后续可无痛切回 DuckDB |
| 2026-03-27 | 当前数据层正式切回 DuckDB | `duckdb` 已安装，可回到目标技术方案 | 数据底座与项目设计重新一致 |
| 2026-03-27 | DuckDB 命令验证按顺序执行 | DuckDB 对同一数据库文件的并发锁更严格 | CLI 使用上避免并发导入与回测同库 |

---

## 7. 风险与阻塞

| 日期 | 类型 | 描述 | 当前处理状态 |
| :--- | :--- | :--- | :--- |
| 2026-03-27 | 环境 | 本地环境缺少 `PyYAML` 和 `pytest` | 已通过标准库回退方案解决 |
| 2026-03-27 | 环境 | 本地环境缺少 `duckdb` 包 | 已解决，DuckDB 已安装并切回正式后端 |
| 2026-03-27 | 运行特性 | DuckDB 同库并发访问更容易触发文件锁 | 已明确通过顺序执行规避，后续可在应用层加串行控制 |
| 2026-03-27 | 外部依赖 | Schwab 接入细节尚未验证 | 后续接入阶段处理 |

---

## 8. 下一步计划

| 优先级 | 任务 | 目标结果 |
| :--- | :--- | :--- |
| P0 | 校验数据导入与回测输出 | 确认真实命令链路可运行 |
| P0 | 完善订单与账户状态模型 | 为模拟执行闭环做准备 |
| P0 | 完善订单与账户状态模型 | 为模拟执行闭环做准备 |
| P0 | 增加回测结果导出 | 为 dashboard 提供输入文件 |
| P1 | 提升绩效指标丰富度 | 增加 Sharpe、Profit Factor 等 |
| P1 | 准备 dashboard 数据接口 | 为前端展示做后端整理 |

---

## 9. 每日/每轮开发记录

后续每推进一轮，在这里追加一条。

### 2026-03-27 第 1 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 从空仓库起步，建立开发基线和首版工程骨架 |
| 输入 | 原始需求文档 `README.md` |
| 产出 | `README_DEV.md`、项目骨架、CLI、配置、策略、风控、回测、测试 |
| 结果 | 最小可运行链路已打通 |
| 未完成 | 数据导入、完整回测、DuckDB、Dashboard、Schwab、通知 |
| 备注 | 后续开发以“每轮交付一个真实能力”为原则推进 |

### 2026-03-27 第 2 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 打通历史数据导入、本地存储、完整多 bar 回测 |
| 输入 | 首版项目骨架与开发基线文档 |
| 产出 | 数据表结构、CSV 导入器、行情仓储、指标预处理、完整回测 CLI |
| 结果 | 历史数据导入、本地存储、完整回测与结果导出已跑通 |
| 未完成 | 更丰富绩效指标、订单模型细化、dashboard 输入格式 |
| 备注 | 先用过渡方案打通功能，随后已切回正式 DuckDB 后端 |

### 2026-03-27 第 3 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 强化账户状态与模拟执行闭环 |
| 输入 | 已跑通的 DuckDB 数据层与回测链路 |
| 产出 | 统一成交事件、现金更新、已实现/未实现盈亏、账户摘要输出 |
| 结果 | 回测结果已包含账户状态，执行层与回测层职责更清晰 |
| 未完成 | 订单状态机、撤单、滑点与手续费模型 |
| 备注 | 这一步是后续接模拟盘和实盘前的重要收敛层 |

---

## 10. 完整项目搭建观察框架

这个部分是给你以后复盘项目时看的。一个完整项目通常就是这样被搭出来的：

| 阶段 | 核心问题 | 交付物 |
| :--- | :--- | :--- |
| 需求整理 | 做什么，不做什么 | 开发说明书 |
| 架构起步 | 模块怎么拆 | 目录结构、基础接口 |
| 最小链路 | 最小闭环能不能跑 | CLI、样例流程、测试 |
| 数据落地 | 数据从哪来、怎么存 | 数据导入、数据库表 |
| 业务成型 | 真实功能能不能工作 | 回测、风控、执行 |
| 交互与观测 | 人如何看见系统状态 | Dashboard、日志、通知 |
| 外部集成 | 怎么和券商/服务互通 | OAuth、API、同步 |
| 稳定性 | 出问题时能不能自保 | 重试、对账、恢复 |
| 交付 | 能不能长期维护 | 文档、测试、部署方式 |

如果后续你愿意，我可以把这个记录表继续升级成：

- 看板版：更像项目管理表
- 里程碑版：更适合看进度
- 教学版：每一轮都解释“为什么这么做”
