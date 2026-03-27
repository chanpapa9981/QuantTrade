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
| W-021 | 风控层 | 增加真实交易成本与流动性约束 | 手续费、滑点、流动性过滤 | 已完成 |
| W-022 | 回测层 | 丰富风险收益指标 | Sharpe、Sortino、最长水下期等 | 已完成 |
| W-017 | UI | 建立 Dashboard 原型 | 参数台、日志台、净值图 | 未开始 |
| W-023 | Dashboard | 准备 dashboard 数据接口 | 摘要卡片、曲线数据、近期交易 | 已完成 |
| W-024 | Dashboard | 导出静态 dashboard 页面 | 生成可直接查看的 HTML 报告 | 已完成 |
| W-025 | 执行层 | 增加订单状态记录与审计事件流 | 为实盘前状态机和审计提供基础 | 已完成 |
| W-026 | 数据层 | 持久化回测运行结果 | 落库存储回测、订单、审计事件 | 已完成 |
| W-027 | 数据层 | 增加运行历史查询接口 | 查询 run detail、order events、audit events | 已完成 |
| W-028 | Dashboard | 增加历史视图静态页面 | 把 persisted runs/order/audit 生成 HTML | 已完成 |
| W-029 | 稳定性 | 增加数据库文件锁与账户快照落库 | 降低 DuckDB 锁冲突并提升追溯性 | 已完成 |
| W-030 | 稳定性 | 增加回测执行生命周期与重复执行保护 | 跟踪 running/completed/abandoned 并拦截同标的重复执行 | 已完成 |
| W-031 | 执行层 | 升级订单状态机为部分成交/撤单感知 | 增加 partial fill、cancelled、重复入场保护和剩余数量记录 | 已完成 |
| W-032 | 执行层 | 增加跨 bar 挂单续撮合与超时撤单 | 支持 open order、继续撮合、timeout cancel、order_id 追踪 | 已完成 |
| W-033 | 执行层 | 增加 open order 重定价事件 | 支持 `replaced` 状态并记录等待成交时的价格更新 | 已完成 |
| W-034 | 数据层 | 增加订单生命周期明细查询 | 按 `order_id` 汇总状态路径并查询完整订单事件流 | 已完成 |
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
| 2026-03-27 | 交易成本与绩效增强 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-27 | 风险收益指标增强 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml backtest --symbol AAPL --timeframe 1d --initial-equity 100000` | 通过 |
| 2026-03-27 | Dashboard 数据接口 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml dashboard-data --symbol AAPL` | 待验证 |
| 2026-03-27 | Dashboard HTML 导出 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml dashboard-html --symbol AAPL` | 待验证 |
| 2026-03-27 | 订单与审计增强 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 待验证 |
| 2026-03-27 | 回测结果持久化 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml backtest --symbol AAPL --timeframe 1d --initial-equity 100000 --persist` | 通过 |
| 2026-03-27 | 回测运行记录查询 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml runs --limit 5` | 通过 |
| 2026-03-27 | 历史摘要查询 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml history --runs-limit 5 --events-limit 5` | 通过 |
| 2026-03-27 | 历史 HTML 导出 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml history-html --runs-limit 5 --events-limit 5` | 待验证 |
| 2026-03-27 | 数据库锁与快照持久化 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml backtest --symbol AAPL --timeframe 1d --initial-equity 100000 --persist` | 通过 |
| 2026-03-27 | 回测执行生命周期与重复执行保护 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-27 | 回测执行记录查询 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml executions --limit 5` | 通过 |
| 2026-03-27 | 订单状态机升级（部分成交/撤单） | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-27 | 订单状态机持久化链路 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml backtest --symbol AAPL --timeframe 1d --initial-equity 100000 --persist` | 通过 |
| 2026-03-27 | 跨 bar 挂单续撮合与超时撤单 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-27 | 订单查询兼容旧库迁移 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml orders --limit 5` | 通过 |
| 2026-03-27 | open order 重定价事件 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-27 | 订单生命周期明细查询 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml order-detail --order-id <order_id>` | 通过 |

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
| 2026-03-27 | 持久化回测增加 execution lifecycle | 需要区分“运行中 / 完成 / 中断恢复”，并阻止同标的重复触发 | 为启动恢复和稳定性观测提供统一入口 |
| 2026-03-27 | 模拟执行按 bar 流动性模拟部分成交 | 只有全成/拒绝会让执行层过于理想化，无法支撑后续撤单与实盘适配 | 订单、持久化、Dashboard 全部开始感知 filled / partial / cancelled |
| 2026-03-27 | open order 在回测层而非执行器内部持有 | 跨 bar 生命周期需要和策略评估、审计日志、超时规则一起编排 | 订单可以被继续撮合、超时取消，并保持完整事件历史 |
| 2026-03-27 | open order 在继续等待时显式记录 `replaced` 事件 | 真实系统里挂单跨 bar 往往伴随重定价或重新提交，仅靠 `open` 无法表达价格变化 | 历史页与审计流开始具备更真实的订单修改语义 |
| 2026-03-27 | 订单分析默认提升到 order lifecycle 视角 | 仅靠 event list 不利于定位单笔订单最终发生了什么 | 查询层开始同时提供原始事件流和归并后的状态路径摘要 |

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
| P0 | 开始更完整的 dashboard 页面骨架 | 增加参数面板、日志区和更细的图表布局 |
| P0 | 继续完善订单状态机 | 引入更多对账字段、order modify 细分原因、broker 状态映射 |
| P0 | 开始 dashboard 历史页 | 使用已落库的 run/order/audit 数据 |
| P0 | 继续完善订单状态机 | 引入更多对账字段、order modify 细分原因、broker 状态映射 |
| P0 | 继续强化稳定性层 | 启动恢复细化、失败重试、实盘级运行锁 |
| P1 | 提升绩效指标丰富度 | 增加更多风险稳定性指标 |
| P1 | 增加日志持久化查询视图 | 为 dashboard 和排错提供历史日志 |
| P1 | 增加 order lifecycle 历史页组件 | 在历史 dashboard 中直接展示单笔订单状态路径 |

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

### 2026-03-27 第 4 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把回测结果从“粗结果”提升到“更适合正式分析” |
| 输入 | 已有 DuckDB 回测链路与账户闭环 |
| 产出 | 手续费、滑点、Profit Factor、平均每笔盈亏等指标 |
| 结果 | 回测结果已经更接近真实交易摩擦成本 |
| 未完成 | Sharpe、Sortino、手续费模型细化、更多风险指标 |
| 备注 | 这一步会直接影响后续 dashboard 和策略评估可信度 |

### 2026-03-27 第 5 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让回测指标更接近正式环境决策需要 |
| 输入 | 已有交易成本、账户状态、回测链路 |
| 产出 | Sharpe、Sortino、最长水下期、流动性与滑点容忍拦截 |
| 结果 | 风险收益视角比之前更完整，回测摘要更适合拿来比较策略 |
| 未完成 | 更完整订单状态机、dashboard 数据接口、更多长期稳定性指标 |
| 备注 | 这一步是把“能回测”往“能评估是否值得实盘”推进 |

### 2026-03-27 第 6 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 为 dashboard 准备可直接消费的数据结构 |
| 输入 | 已完成的回测、账户、绩效指标与交易记录 |
| 产出 | summary cards、equity curve、drawdown curve、recent trades |
| 结果 | 后续前端不需要自己拼装回测数据 |
| 未完成 | 真正的 dashboard 页面与交互 |
| 备注 | 这是进入 UI 阶段前的关键过渡层 |

### 2026-03-27 第 7 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 dashboard 数据可以被直接查看，而不是只停留在 JSON |
| 输入 | 已准备好的 dashboard 数据接口 |
| 产出 | 静态 HTML dashboard 导出能力 |
| 结果 | 回测结果现在可以直接生成一页可读的研究看板 |
| 未完成 | 更完整的交互式页面与参数编辑区 |
| 备注 | 这是正式 UI 前的第一版可视化交付 |

### 2026-03-27 第 8 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把执行闭环再往正式交易系统靠近一步 |
| 输入 | 已有回测、交易、dashboard 静态导出能力 |
| 产出 | 订单记录、审计事件流、dashboard 订单区和事件区 |
| 结果 | 系统不再只输出成交结果，也开始输出执行过程本身 |
| 未完成 | 撤单、部分成交、重复下单保护、持久化日志 |
| 备注 | 这一步对未来实盘排错和风控审计很关键 |

### 2026-03-27 第 9 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把回测结果从“生成一次”提升到“可以被持续追踪” |
| 输入 | 已有回测、订单事件、审计事件和 DuckDB 数据层 |
| 产出 | `backtest_runs`、`order_events`、`audit_events` 表，以及 `runs` 查询命令 |
| 结果 | 系统开始拥有可追溯的回测历史，而不只是单次输出 |
| 未完成 | 更完整的日志查询、运行对比、实盘事件持久化 |
| 备注 | 这是后续做历史对比、回归分析和 dashboard 历史页的基础 |

### 2026-03-27 第 10 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让持久化结果不仅能存，还能被查询与汇总 |
| 输入 | 已有 `backtest_runs`、`order_events`、`audit_events` |
| 产出 | `run-detail`、`orders`、`audit-events`、`history` 查询能力 |
| 结果 | 系统开始具备真正的历史视图后端能力 |
| 未完成 | dashboard 历史页 UI、运行对比、日志筛选 |
| 备注 | 这一步让第 4 层和第 6 层开始真正连接起来 |

### 2026-03-27 第 11 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让持久化历史数据可以被直接可视化查看 |
| 输入 | 已有 history 查询与 persisted run/order/audit 数据 |
| 产出 | `history-html` 静态历史页面导出能力 |
| 结果 | 研究端开始拥有“当前报告页 + 历史报告页”双页面结构 |
| 未完成 | 交互式历史筛选、运行对比、更多页面组件 |
| 备注 | 这一步把 dashboard 从单次回测展示推进到“多运行历史展示” |

### 2026-03-27 第 12 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 降低 DuckDB 锁冲突，并增强运行结果追溯能力 |
| 输入 | 已有回测持久化和历史查询能力 |
| 产出 | 跨进程数据库锁、`account_snapshots` 表、旧 run 兼容快照回退 |
| 结果 | 读取/写入更稳定，回测详情开始具备账户快照 |
| 未完成 | 启动恢复、重复执行保护、实盘级运行锁 |
| 备注 | 这是正式环境可用性里非常关键的一层地基 |

### 2026-03-27 第 13 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 为持久化回测补上执行生命周期和同标的重复执行保护 |
| 输入 | 已有数据库锁、回测持久化、历史查询能力 |
| 产出 | `backtest_executions` 表、`executions` CLI、stale execution recovery、symbol/timeframe 运行锁 |
| 结果 | 系统现在能区分 running/completed/abandoned，并在同标的重复触发时即时拒绝 |
| 未完成 | 失败重试策略、恢复后自动续跑、实盘级运行状态机 |
| 备注 | 这一步把“能落库”继续推进到“能管住运行过程本身” |

### 2026-03-27 第 14 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把模拟执行从“全成/拒绝”推进到更接近真实订单生命周期 |
| 输入 | 已有回测、订单落库、执行生命周期跟踪能力 |
| 产出 | `partially_filled` / `cancelled` 状态、按 bar 成交容量限制、重复入场保护、filled/remaining quantity 持久化 |
| 结果 | 订单记录现在能表达部分成交和剩余撤单，回测与 dashboard 对执行细节更敏感 |
| 未完成 | pending/open order、超时撤单、部分成交后的跨 bar 续撮合、实盘对账字段 |
| 备注 | 这是从研究型回测器走向真正执行系统的重要过渡层 |

### 2026-03-27 第 15 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 open order 不只停在单 bar，而是能跨 bar 延续并最终超时撤单 |
| 输入 | 已有 partial fill、cancelled、execution lifecycle 与 order persistence |
| 产出 | `open` 状态、`order_id` 追踪、跨 bar 续撮合、timeout cancel、旧库查询自动迁移 |
| 结果 | 回测开始能表达“订单提交后继续等待成交”的真实流程，订单历史可按同一 `order_id` 串起来看 |
| 未完成 | replace/modify 订单、跨 bar 价格偏离重定价、实盘对账字段、broker 状态映射 |
| 备注 | 这一步让执行层更像一个真正的订单状态机，而不只是成交事件生成器 |

### 2026-03-27 第 16 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 open order 在继续等待时也能显式表达价格调整，而不是只有 open/cancel |
| 输入 | 已有 open order、timeout cancel、order_id 持续追踪能力 |
| 产出 | `replaced` 状态、等待成交期间的重定价事件、dashboard 订单摘要补充 replaced count |
| 结果 | 订单历史开始能反映“继续等待成交但价格已随市场更新”的过程，订单语义更接近真实执行系统 |
| 未完成 | 更细的 modify 原因、broker 状态映射、实盘级 replace/cancel 约束 |
| 备注 | 这一步是在为后续接真实券商 API 时减少语义落差 |

### 2026-03-27 第 17 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把订单查询从“事件列表”提升到“单笔订单生命周期”视角 |
| 输入 | 已有 `order_id` 追踪、created/open/replaced/filled/cancelled 事件流 |
| 产出 | `order-detail` CLI、`fetch_order_detail` 仓储接口、`run-detail` 中的 `order_lifecycles` 摘要 |
| 结果 | 现在可以直接查看单笔订单的 `status_path`、最终状态、已成交/剩余数量和相关 run 信息 |
| 未完成 | 历史页里可视化 order lifecycle、按状态筛选和按 run/order 联动跳转 |
| 备注 | 这是后续做排错、策略复盘和实盘对账时非常重要的分析入口 |

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
