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
> - 自本轮起，后续所有新增或修改代码默认必须补充清晰中文注释，并同步维护注释规范文档。

---

## 1. 项目概览

| 字段 | 内容 |
| :--- | :--- |
| 项目名称 | QuantTrade |
| 项目类型 | 个人自动化交易系统（ATS） |
| 开发基线 | [README_DEV.md](/Users/andy/Documents/QuantTrade/README_DEV.md) |
| 原始需求 | [README.md](/Users/andy/Documents/QuantTrade/README.md) |
| 当前阶段 | 阶段 3/5/6：完整回测、执行状态机与 Dashboard 历史视图 |
| 当前状态 | 进行中 |
| 默认技术方向 | Python + DuckDB + YAML + Web Dashboard + Docker |
| 目标环境 | Mac mini |

---

## 2. 总体阶段表

| 阶段 | 名称 | 目标 | 预计产出 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 0 | 需求整理 | 把理念型需求整理成开发型说明书 | 开发基线文档 | 已完成 |
| 1 | 项目骨架 | 搭建目录结构、配置、CLI、核心模块骨架 | 可运行的最小链路 | 已完成 |
| 2 | 数据层 | 导入历史行情并落库到 DuckDB | 可查询的本地行情库 | 已完成 |
| 3 | 回测引擎 | 基于历史数据跑完整回测 | 回测结果与核心指标 | 进行中 |
| 4 | 风控完善 | 完成账户级与标的级风控规则 | 风控拦截与风控日志 | 未开始 |
| 5 | 模拟执行 | 完成订单、成交、持仓、账户状态变更 | 模拟盘闭环 | 进行中 |
| 6 | Dashboard | 展示参数、日志、净值、持仓、策略状态 | 基础 Web 面板 | 进行中 |
| 7 | Schwab 接入 | 实现认证、账户同步、基础下单能力 | 实盘基础接入 | 未开始 |
| 8 | 通知与告警 | 推送交易动作与风险事件 | 手机通知闭环 | 未开始 |
| 9 | 稳定性增强 | 断网重连、状态对账、异常恢复 | 可试运行版本 | 进行中 |

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
| W-035 | Dashboard | 在历史页展示订单生命周期摘要 | 把 `order_id`、final status、status path 直接显示在历史 HTML 中 | 已完成 |
| W-036 | Dashboard | 增加历史页订单生命周期统计卡片 | 展示 lifecycle filled/cancelled/repriced 等摘要数量 | 已完成 |
| W-037 | Dashboard | 增加历史页生命周期状态筛选 | 支持按 all/filled/cancelled/open/repriced 过滤生命周期表 | 已完成 |
| W-038 | Dashboard | 增加历史页订单生命周期详情联动 | 点击 lifecycle 行即可查看该订单的原始事件明细 | 已完成 |
| W-039 | Dashboard | 增加历史页深链接与 run/order 联动 | 支持 URL hash 定位、run scope 筛选和跨表联动跳转 | 已完成 |
| W-040 | Dashboard | 增加历史页多条件筛选与复制链接 | 支持 run/status/side 组合筛选和当前上下文链接复制 | 已完成 |
| W-041 | Dashboard | 增加历史页异常聚焦模式 | 支持一键聚焦未完成、撤单、重定价等更值得排查的订单 | 已完成 |
| W-042 | 工程规范 | 为项目代码补充系统性中文注释并固化规则 | 让主流程、状态机和测试场景对新人也足够可读 | 已完成 |
| W-043 | 执行层 | 增加 broker 状态语义映射准备层 | 为订单事件补充 broker_status/status_detail，并同步到查询与历史页 | 已完成 |
| W-044 | Dashboard | 增加历史页 broker 状态筛选 | 支持按 pending_new/working/replaced/filled 等 broker 语义过滤订单生命周期 | 已完成 |
| W-045 | 稳定性 | 增强回测执行记录的重试与保护模式元数据 | 记录 attempt_number、连续失败次数、recovered count 和 protection mode | 已完成 |
| W-046 | Dashboard | 增加执行尝试的查询与历史页可视化 | 支持 execution detail、执行摘要卡片、执行表和保护模式联动查看 | 已完成 |
| W-047 | Dashboard | 增加执行尝试状态筛选 | 支持按 completed/failed/abandoned/running/protection 收缩执行排错范围 | 已完成 |
| W-048 | 稳定性 | 增加可配置自动重试与 protection mode 拦截动作 | 让 persist backtest 遇到瞬时失败可重试，遇到保护模式可直接 blocked 返回 | 已完成 |
| W-049 | Dashboard | 把 blocked execution 接入历史页摘要与筛选 | 展示 blocked 计数，并支持按 blocked 状态筛选执行尝试 | 已完成 |
| W-050 | 稳定性 | 为同一次回测触发增加 request_id 关联链路 | 把同一轮调用产生的多次 execution attempt 串成同一个请求上下文 | 已完成 |
| W-051 | Dashboard | 增加 request 级执行链查询与历史页联动 | 支持 execution request 列表、request detail、request 级摘要卡片与页面联动 | 已完成 |
| W-052 | Dashboard | 升级单次回测 dashboard 页面骨架 | 增加运行上下文、参数面板、审计摘要和更完整的研究布局 | 已完成 |
| W-053 | 稳定性 | 增加失败分类与重试决策记录 | 区分 retryable / non-retryable / blocked，并记录 failure_class 与 retry_decision | 已完成 |
| W-054 | 稳定性 / Dashboard | 增加可配置退避策略与 request 级异常聚合 | 支持线性/指数退避、最大退避封顶、request 健康度/异常分数/失败类别摘要 | 已完成 |
| W-055 | 稳定性 / CLI / Dashboard | 增加保护模式冷却恢复与状态查询 | 支持冷却窗口、自动恢复、`protection-status` 命令、cooldown 可视化 | 已完成 |
| W-056 | 通知 / Dashboard / CLI | 增加本地通知事件与 outbox 骨架 | 支持 notification_events、`notifications` 命令、history 告警面板和 JSONL outbox | 已完成 |
| W-057 | 通知 / Dashboard / CLI | 增加通知投递 worker 状态机 | 支持 `notifications-deliver`、投递尝试次数/失败原因/adapter dispatch log、history 告警状态筛选与统计 | 已完成 |
| W-058 | 通知 / Dashboard | 增加通知重投退避时间窗 | 支持 `next_delivery_attempt_at`、通知独立退避策略、history `Next Try` 展示和延后重投 | 已完成 |
| W-059 | 通知 / Dashboard / CLI | 增加告警静默窗口与汇总视图 | 支持重复告警压缩、`notification-summary`、history `Notification Summary` 和 suppressed duplicate 统计 | 已完成 |
| W-060 | 通知 / Dashboard / CLI | 增加通知确认（ack）能力 | 支持 `notification-ack`、ack 时间/备注持久化、history 已确认/未确认统计与展示 | 已完成 |
| W-061 | 通知 / Dashboard / CLI | 增加未确认告警升级标记 | 支持 `notification-escalate`、escalated_at/level/reason、history 升级统计与展示 | 已完成 |
| W-062 | 通知 / Dashboard / CLI | 增加告警责任分派工作流 | 支持 `notification-assign`、assigned_to/assigned_at/assignment_note、history owner 过滤与责任统计 | 已完成 |
| W-063 | 通知 / Dashboard / CLI | 增加 owner 负载汇总视图 | 支持 `notification-owner-summary`、按 owner 聚合未确认/升级/高优先级告警，以及 history `Notification Owners` 面板 | 已完成 |
| W-064 | 通知 / Dashboard / CLI | 增加 assignment SLA 过期视图 | 支持 `assignment_sla_seconds`、`notification-sla`、history `Notification SLA` 面板和 SLA Breached 统计 | 已完成 |
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
| 2026-03-27 | 历史页订单生命周期展示 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml history-html --runs-limit 5 --events-limit 10 --output var/reports/history.html` | 通过 |
| 2026-03-27 | 历史页生命周期统计卡片 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml history-html --runs-limit 5 --events-limit 10 --output var/reports/history.html` | 通过 |
| 2026-03-27 | 历史页生命周期状态筛选 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml history-html --runs-limit 5 --events-limit 10 --output var/reports/history.html` | 通过 |
| 2026-03-27 | 历史页订单生命周期详情联动 | `PYTHONPATH=src python3 -m quanttrade.cli --config configs/settings.example.yaml history-html --runs-limit 5 --events-limit 10 --output var/reports/history.html` | 通过 |
| 2026-03-27 | 历史页深链接与 run/order 联动 | `PYTHONPATH=src python3 -m unittest tests.test_history_html -v` | 通过 |
| 2026-03-28 | 历史页多条件筛选与复制链接 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-28 | 历史页异常聚焦模式 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-28 | 系统性中文注释覆盖与规范固化 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-28 | broker 状态语义映射准备层 | `PYTHONPATH=src python3 -m unittest discover -s tests -v` | 通过 |
| 2026-03-28 | 历史页 broker 状态筛选 | `PYTHONPATH=src python3 -m unittest tests.test_history_html -v` | 通过 |
| 2026-03-28 | 执行记录重试与保护模式元数据 | `PYTHONPATH=src python3 -m unittest tests.test_data_import_and_backtest -v` | 通过 |
| 2026-03-28 | 单次 dashboard 页面骨架升级 | `PYTHONPATH=src python -m unittest discover -s tests -v` | 通过 |

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
| 2026-03-27 | 历史 dashboard 优先展示 order lifecycle 而不只展示 event stream | 研究和排错更关心“订单最终经历了什么”而不是只看孤立事件 | 历史页信息密度更高，也更适合后续接实盘订单排查 |
| 2026-03-27 | 历史 dashboard 增加 lifecycle 聚合卡片 | 长表格之外需要一眼看出订单状态分布，方便快速复盘 | 历史页开始兼顾总览和明细两种阅读方式 |
| 2026-03-27 | 历史页筛选先做前端静态过滤 | 当前页面是静态 HTML，前端内筛选比新增后端接口更轻量且足够解决大部分复盘需求 | 不改数据接口也能提升历史页可用性 |
| 2026-03-27 | 历史页订单详情先做同页联动而不是页面跳转 | 静态 HTML 下同页联动实现成本更低、体验也更顺滑 | 先满足复盘排错需求，后续若做服务端再扩展深链接 |
| 2026-03-27 | 历史页上下文定位先采用 URL hash | 静态 HTML 不适合引入服务端路由，但复盘又需要可分享的具体上下文 | 同一份历史页即可支持 run/order/filter 深链接和跨表联动 |
| 2026-03-28 | 历史页分享态优先用当前上下文直接生成链接 | 静态页面里最实用的分享方式不是导出更多页面，而是把当前筛选状态直接编码进链接 | 同一个历史页现在可同时承担查看、定位和分享上下文三种用途 |
| 2026-03-28 | 异常聚焦优先做成轻量前端模式而不是新增独立页面 | 异常订单的判定逻辑仍在演化，先做可调整的前端聚焦模式更灵活 | 可以快速提升排错效率，同时保留后续迭代异常定义的空间 |
| 2026-03-28 | 后续代码默认强制补充中文注释 | 当前项目已进入中期，模块变多后仅靠函数名和结构已不足以保证可维护性 | 以后新增功能时，代码可读性和教学性将成为默认交付标准之一 |
| 2026-03-28 | 先补 broker 语义映射准备层，再接真实券商 | 直接把当前本地状态机硬绑到 Schwab 容易造成概念错位，后期改造成本更高 | 订单事件现在开始同时拥有本地状态和更接近券商语义的状态字段 |
| 2026-03-28 | broker 语义一旦落到历史页，就要同步提供筛选能力 | 只有展示没有筛选，排错时仍然要手动扫表，价值会打折扣 | 历史页现在既能按本地状态筛，也能按 broker 语义筛 |
| 2026-03-28 | 运行记录要先具备保护模式元数据，再谈自动重试 | 如果系统连“已经连续失败了几次、是否应进入保护模式”都不知道，自动重试就会很危险 | 现在执行记录开始具备更接近真实运行控制器的基础字段 |
| 2026-03-28 | 单次 dashboard 先补研究上下文与参数面板，再做更深交互 | 当前单次页虽然能看结果，但还不够像研究工作台；先把输入参数、运行上下文和审计摘要放进同一页，才能支撑后续 drill-down | 单次 dashboard 现在从“结果页”升级为更完整的静态研究页 |

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
| P0 | 继续完善订单状态机 | 引入更多对账字段、order modify 细分原因、broker 状态映射 |
| P0 | 继续强化稳定性层 | 启动恢复细化、失败重试、实盘级运行锁 |
| P0 | 继续深化单次 dashboard 交互 | 增加更细的图表注解、明细联动和研究视角切换 |
| P1 | 提升绩效指标丰富度 | 增加更多风险稳定性指标 |
| P1 | 增加日志持久化查询视图 | 为 dashboard 和排错提供历史日志 |
| P1 | 增加历史页更强的分享态 | 支持复制上下文链接、默认聚焦异常订单、扩展摘要信息 |
| P1 | 继续深化异常定义 | 增加按状态族、重定价频次、长时间未完成等异常口径 |
| P1 | 推进 broker 语义映射细化 | 继续扩展 cancel/replace/detail reason，并准备 Schwab 状态映射表 |
| P1 | 增加 execution 保护模式可视化 | 在查询或页面里直观看到 attempt/protection/consecutive failures |
| P1 | 持续补齐新功能中文注释 | 确保后续每轮新增代码都满足教学级可读性 |

---

## 9. 每日/每轮开发记录（教学版）

后续每推进一轮，在这里追加一条。教学版要求是：除了记录“做了什么”，还要明确写出“为什么先做这一步”，这样以后回看时不仅能看见结果，也能理解推进顺序。

### 2026-03-27 第 1 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 从空仓库起步，建立开发基线和首版工程骨架 |
| 输入 | 原始需求文档 `README.md` |
| 产出 | `README_DEV.md`、项目骨架、CLI、配置、策略、风控、回测、测试 |
| 结果 | 最小可运行链路已打通 |
| 为什么这么做 | 因为自动化交易系统是长链路工程，先把最小闭环跑通，后面加数据、风控、执行、可视化时才不会一直在“没有地基”的状态下返工。 |
| 未完成 | 数据导入、完整回测、DuckDB、Dashboard、Schwab、通知 |
| 备注 | 后续开发以“每轮交付一个真实能力”为原则推进 |

### 2026-03-27 第 2 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 打通历史数据导入、本地存储、完整多 bar 回测 |
| 输入 | 首版项目骨架与开发基线文档 |
| 产出 | 数据表结构、CSV 导入器、行情仓储、指标预处理、完整回测 CLI |
| 结果 | 历史数据导入、本地存储、完整回测与结果导出已跑通 |
| 为什么这么做 | 因为没有真实历史数据和完整序列回放，前面的策略、风控、执行只能算样例程序；这一轮是把项目从“能演示”推进到“能研究”。 |
| 未完成 | 更丰富绩效指标、订单模型细化、dashboard 输入格式 |
| 备注 | 先用过渡方案打通功能，随后已切回正式 DuckDB 后端 |

### 2026-03-27 第 3 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 强化账户状态与模拟执行闭环 |
| 输入 | 已跑通的 DuckDB 数据层与回测链路 |
| 产出 | 统一成交事件、现金更新、已实现/未实现盈亏、账户摘要输出 |
| 结果 | 回测结果已包含账户状态，执行层与回测层职责更清晰 |
| 为什么这么做 | 因为只看信号和成交点不够，交易系统最终关心的是现金、仓位和盈亏如何变化；先把账户闭环补上，后续风控和实盘接入才有统一状态基础。 |
| 未完成 | 订单状态机、撤单、滑点与手续费模型 |
| 备注 | 这一步是后续接模拟盘和实盘前的重要收敛层 |

### 2026-03-27 第 4 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把回测结果从“粗结果”提升到“更适合正式分析” |
| 输入 | 已有 DuckDB 回测链路与账户闭环 |
| 产出 | 手续费、滑点、Profit Factor、平均每笔盈亏等指标 |
| 结果 | 回测结果已经更接近真实交易摩擦成本 |
| 为什么这么做 | 因为零成本回测会系统性高估策略表现，越早把手续费和滑点纳入模型，越能避免后面围绕错误结果做优化。 |
| 未完成 | Sharpe、Sortino、手续费模型细化、更多风险指标 |
| 备注 | 这一步会直接影响后续 dashboard 和策略评估可信度 |

### 2026-03-27 第 5 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让回测指标更接近正式环境决策需要 |
| 输入 | 已有交易成本、账户状态、回测链路 |
| 产出 | Sharpe、Sortino、最长水下期、流动性与滑点容忍拦截 |
| 结果 | 风险收益视角比之前更完整，回测摘要更适合拿来比较策略 |
| 为什么这么做 | 因为交易系统不是只看赚不赚钱，还要看波动、回撤和可执行性；这一轮是在把“收益结果”提升成“可决策结果”。 |
| 未完成 | 更完整订单状态机、dashboard 数据接口、更多长期稳定性指标 |
| 备注 | 这一步是把“能回测”往“能评估是否值得实盘”推进 |

### 2026-03-27 第 6 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 为 dashboard 准备可直接消费的数据结构 |
| 输入 | 已完成的回测、账户、绩效指标与交易记录 |
| 产出 | summary cards、equity curve、drawdown curve、recent trades |
| 结果 | 后续前端不需要自己拼装回测数据 |
| 为什么这么做 | 因为 UI 层如果直接拼底层数据，很快会变得脆弱且难维护；先把面向展示的数据接口整理好，前后端职责才会清楚。 |
| 未完成 | 真正的 dashboard 页面与交互 |
| 备注 | 这是进入 UI 阶段前的关键过渡层 |

### 2026-03-27 第 7 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 dashboard 数据可以被直接查看，而不是只停留在 JSON |
| 输入 | 已准备好的 dashboard 数据接口 |
| 产出 | 静态 HTML dashboard 导出能力 |
| 结果 | 回测结果现在可以直接生成一页可读的研究看板 |
| 为什么这么做 | 因为先交付静态 HTML，比直接上完整 Web 应用更轻、更快，也更适合尽早验证“哪些信息真的值得展示”。 |
| 未完成 | 更完整的交互式页面与参数编辑区 |
| 备注 | 这是正式 UI 前的第一版可视化交付 |

### 2026-03-27 第 8 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把执行闭环再往正式交易系统靠近一步 |
| 输入 | 已有回测、交易、dashboard 静态导出能力 |
| 产出 | 订单记录、审计事件流、dashboard 订单区和事件区 |
| 结果 | 系统不再只输出成交结果，也开始输出执行过程本身 |
| 为什么这么做 | 因为真实交易系统最怕“结果有了，但过程不可解释”；先把订单事件和审计事件记录下来，后续排错、对账、风控才能有依据。 |
| 未完成 | 撤单、部分成交、重复下单保护、持久化日志 |
| 备注 | 这一步对未来实盘排错和风控审计很关键 |

### 2026-03-27 第 9 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把回测结果从“生成一次”提升到“可以被持续追踪” |
| 输入 | 已有回测、订单事件、审计事件和 DuckDB 数据层 |
| 产出 | `backtest_runs`、`order_events`、`audit_events` 表，以及 `runs` 查询命令 |
| 结果 | 系统开始拥有可追溯的回测历史，而不只是单次输出 |
| 为什么这么做 | 因为没有历史持久化，就无法做回归比较、历史复盘和长期研究；这一轮是把系统从“一次性脚本”变成“可积累研究资产的平台”。 |
| 未完成 | 更完整的日志查询、运行对比、实盘事件持久化 |
| 备注 | 这是后续做历史对比、回归分析和 dashboard 历史页的基础 |

### 2026-03-27 第 10 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让持久化结果不仅能存，还能被查询与汇总 |
| 输入 | 已有 `backtest_runs`、`order_events`、`audit_events` |
| 产出 | `run-detail`、`orders`、`audit-events`、`history` 查询能力 |
| 结果 | 系统开始具备真正的历史视图后端能力 |
| 为什么这么做 | 因为“写得进去”不等于“用得起来”，持久化如果没有查询层，数据价值基本发挥不出来；这一轮是在把数据库变成真正可消费的历史接口。 |
| 未完成 | dashboard 历史页 UI、运行对比、日志筛选 |
| 备注 | 这一步让第 4 层和第 6 层开始真正连接起来 |

### 2026-03-27 第 11 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让持久化历史数据可以被直接可视化查看 |
| 输入 | 已有 history 查询与 persisted run/order/audit 数据 |
| 产出 | `history-html` 静态历史页面导出能力 |
| 结果 | 研究端开始拥有“当前报告页 + 历史报告页”双页面结构 |
| 为什么这么做 | 因为研究系统不仅要看单次回测，还要看多次运行之间的脉络；历史页是把“持续积累的数据”变成“可读的复盘材料”。 |
| 未完成 | 交互式历史筛选、运行对比、更多页面组件 |
| 备注 | 这一步把 dashboard 从单次回测展示推进到“多运行历史展示” |

### 2026-03-27 第 12 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 降低 DuckDB 锁冲突，并增强运行结果追溯能力 |
| 输入 | 已有回测持久化和历史查询能力 |
| 产出 | 跨进程数据库锁、`account_snapshots` 表、旧 run 兼容快照回退 |
| 结果 | 读取/写入更稳定，回测详情开始具备账户快照 |
| 为什么这么做 | 因为一旦开始频繁跑回测和查历史，稳定性问题会比新功能更快暴露；这一轮先补运行地基，避免系统在扩大使用时变脆。 |
| 未完成 | 启动恢复、重复执行保护、实盘级运行锁 |
| 备注 | 这是正式环境可用性里非常关键的一层地基 |

### 2026-03-27 第 13 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 为持久化回测补上执行生命周期和同标的重复执行保护 |
| 输入 | 已有数据库锁、回测持久化、历史查询能力 |
| 产出 | `backtest_executions` 表、`executions` CLI、stale execution recovery、symbol/timeframe 运行锁 |
| 结果 | 系统现在能区分 running/completed/abandoned，并在同标的重复触发时即时拒绝 |
| 为什么这么做 | 因为能运行还不够，系统还要知道“自己现在处于什么运行状态”；否则重复执行、异常中断、恢复启动都会变成黑盒。 |
| 未完成 | 失败重试策略、恢复后自动续跑、实盘级运行状态机 |
| 备注 | 这一步把“能落库”继续推进到“能管住运行过程本身” |

### 2026-03-27 第 14 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把模拟执行从“全成/拒绝”推进到更接近真实订单生命周期 |
| 输入 | 已有回测、订单落库、执行生命周期跟踪能力 |
| 产出 | `partially_filled` / `cancelled` 状态、按 bar 成交容量限制、重复入场保护、filled/remaining quantity 持久化 |
| 结果 | 订单记录现在能表达部分成交和剩余撤单，回测与 dashboard 对执行细节更敏感 |
| 为什么这么做 | 因为全成/拒绝模型太理想化，很多策略在这种模型下会被高估；补上部分成交和撤单后，系统才开始像真实执行环境。 |
| 未完成 | pending/open order、超时撤单、部分成交后的跨 bar 续撮合、实盘对账字段 |
| 备注 | 这是从研究型回测器走向真正执行系统的重要过渡层 |

### 2026-03-27 第 15 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 open order 不只停在单 bar，而是能跨 bar 延续并最终超时撤单 |
| 输入 | 已有 partial fill、cancelled、execution lifecycle 与 order persistence |
| 产出 | `open` 状态、`order_id` 追踪、跨 bar 续撮合、timeout cancel、旧库查询自动迁移 |
| 结果 | 回测开始能表达“订单提交后继续等待成交”的真实流程，订单历史可按同一 `order_id` 串起来看 |
| 为什么这么做 | 因为很多真实订单不会在一个 bar 内完成，若不能跨 bar 持续存在，订单状态机仍然是截断的，后续对接券商时会出现巨大语义落差。 |
| 未完成 | replace/modify 订单、跨 bar 价格偏离重定价、实盘对账字段、broker 状态映射 |
| 备注 | 这一步让执行层更像一个真正的订单状态机，而不只是成交事件生成器 |

### 2026-03-27 第 16 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 open order 在继续等待时也能显式表达价格调整，而不是只有 open/cancel |
| 输入 | 已有 open order、timeout cancel、order_id 持续追踪能力 |
| 产出 | `replaced` 状态、等待成交期间的重定价事件、dashboard 订单摘要补充 replaced count |
| 结果 | 订单历史开始能反映“继续等待成交但价格已随市场更新”的过程，订单语义更接近真实执行系统 |
| 为什么这么做 | 因为真实挂单经常会改价重挂，如果没有 `replaced` 语义，历史里只能看到“在等”，却看不见“为了等而做了什么调整”。 |
| 未完成 | 更细的 modify 原因、broker 状态映射、实盘级 replace/cancel 约束 |
| 备注 | 这一步是在为后续接真实券商 API 时减少语义落差 |

### 2026-03-27 第 17 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把订单查询从“事件列表”提升到“单笔订单生命周期”视角 |
| 输入 | 已有 `order_id` 追踪、created/open/replaced/filled/cancelled 事件流 |
| 产出 | `order-detail` CLI、`fetch_order_detail` 仓储接口、`run-detail` 中的 `order_lifecycles` 摘要 |
| 结果 | 现在可以直接查看单笔订单的 `status_path`、最终状态、已成交/剩余数量和相关 run 信息 |
| 为什么这么做 | 因为人复盘订单时关注的是“一笔订单最终经历了什么”，而不是数据库里散落的几条事件；生命周期视角更符合排错和研究习惯。 |
| 未完成 | 历史页里可视化 order lifecycle、按状态筛选和按 run/order 联动跳转 |
| 备注 | 这是后续做排错、策略复盘和实盘对账时非常重要的分析入口 |

### 2026-03-27 第 18 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把订单生命周期摘要真正展示到历史 dashboard，而不只停在 CLI 查询 |
| 输入 | 已有 `order-detail` 查询、`order_lifecycles` 摘要数据结构 |
| 产出 | 历史页 `Order Lifecycles` 面板，展示 `order_id`、final status、requested/filled quantity、status path |
| 结果 | 历史 HTML 现在更适合做订单级复盘和排错，不用只靠最近订单事件表倒推 |
| 为什么这么做 | 因为真正高频使用的信息不能只藏在 CLI 里；把生命周期直接放到历史页，才能让研究和排错进入“看一眼就知道大概发生了什么”的状态。 |
| 未完成 | 状态筛选、订单详情跳转、更多生命周期统计卡片 |
| 备注 | 这一步把执行状态机能力真正向研究/运维视图传导了出去 |

### 2026-03-27 第 19 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页先具备 lifecycle 总览，而不只是订单明细表 |
| 输入 | 已有 `order_lifecycles` 数据结构和历史页生命周期表格 |
| 产出 | `Order Lifecycles` 统计卡片，包括 total/filled/cancelled/repriced 等指标 |
| 结果 | 历史 dashboard 现在既能做订单级细读，也能做状态分布级快速浏览 |
| 为什么这么做 | 因为表格适合查细节，但不适合先做全局判断；统计卡片能先回答“这一批订单整体正常吗”，再决定是否往下钻取。 |
| 未完成 | 生命周期状态筛选、点击单笔订单查看 detail、更多统计口径 |
| 备注 | 这一步是在把订单历史页从“表格展示”推进到“研究/运维面板” |

### 2026-03-27 第 20 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页里的订单生命周期表具备基础筛选能力 |
| 输入 | 已有 lifecycle 表格和状态统计卡片 |
| 产出 | `all / filled / cancelled / open / repriced` 前端筛选下拉框 |
| 结果 | 历史 HTML 现在能更快聚焦异常订单，而不需要手动在表格里查找 |
| 为什么这么做 | 因为历史一多，靠肉眼扫表会迅速失效；哪怕是静态页面，也应该尽早具备最基本的异常聚焦能力。 |
| 未完成 | 按 run/order 跳转、多条件筛选、详情联动 |
| 备注 | 这是静态 dashboard 走向“轻交互研究面板”的小一步 |

### 2026-03-27 第 21 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页中的订单生命周期不只可筛选，还能直接查看明细事件 |
| 输入 | 已有 lifecycle 表、状态筛选和 `order_lifecycle_details` 数据 |
| 产出 | `Lifecycle Detail` 面板，点击某个 `order_id` 即联动展示该订单的事件流 |
| 结果 | 现在在一页内就能完成“发现异常订单 -> 查看状态路径 -> 查看原始事件”的闭环 |
| 为什么这么做 | 因为真正高效的排错流程应该尽量少跳转页面；把发现问题和查看明细放在同一页，复盘速度会明显更快。 |
| 未完成 | URL 深链接、多条件筛选、跨 run/order 的联动导航 |
| 备注 | 这一步让历史页更接近一个轻量的订单排错工作台 |

### 2026-03-27 第 22 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页具备可分享的上下文定位能力，并把 run/order/filter 在同一页联动起来 |
| 输入 | 已有 lifecycle 表、详情联动、状态筛选和历史 run/order/audit 数据 |
| 产出 | `run-filter`、URL hash 深链接、run/order 联动跳转、上下文清除按钮、按 run 作用域过滤的 runs/orders/audit 视图 |
| 结果 | 现在同一份 `history.html` 可以直接定位到某个 run、某种 lifecycle 状态和某笔订单，复盘上下文可被保留下来并复用 |
| 为什么这么做 | 因为历史页一旦开始承担排错职责，就不能只“展示信息”，还要能稳定地回到某个具体上下文；深链接和联动是让静态页面真正可协作的关键一步。 |
| 未完成 | 多条件组合筛选、复制链接体验、更多异常摘要与实盘语义映射 |
| 备注 | 这一步把静态历史页继续推进成“可分享的轻量排错台” |

### 2026-03-28 第 23 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页上下文不只可定位，还能做组合筛选并直接复制给别人复现同一视图 |
| 输入 | 已有 URL hash 深链接、run/order 联动和生命周期筛选能力 |
| 产出 | `side-filter`、run/status/side 组合筛选、匹配数量上下文提示、`Copy Link` 按钮 |
| 结果 | 历史页现在可以在同一份 HTML 内快速收缩到更具体的订单子集，并把当前上下文一键复制出去 |
| 为什么这么做 | 因为真正的排错不是看完整大表，而是不断缩小问题范围；组合筛选和复制链接能把“我看到的问题”稳定地传递成“你也能立即看到的同一个问题”。 |
| 未完成 | 异常订单默认聚焦、更强的异常摘要、订单状态机里的更多对账和 broker 语义 |
| 备注 | 这一步让静态历史页进一步具备协作排错能力，而不只是个人查看工具 |

### 2026-03-28 第 24 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页能一键把注意力集中到更值得排查的异常订单，而不是总从全量列表开始看 |
| 输入 | 已有 run/status/side 组合筛选、深链接和上下文分享能力 |
| 产出 | `focus-filter`、异常行高亮、异常聚焦 URL 状态同步、异常数量随上下文联动 |
| 结果 | 历史页现在可以快速只看 cancelled/open/repriced 等更可能需要人工复盘的订单集合 |
| 为什么这么做 | 因为排错的第一步通常不是“看全部”，而是“先找最有问题的那一小撮”；异常聚焦模式能让历史页更接近日常运维和复盘的真实使用方式。 |
| 未完成 | 更细粒度的异常口径、异常摘要卡片、订单状态机里的更多 broker 语义与对账字段 |
| 备注 | 这一步让历史页从通用查询面板继续靠近“异常优先”的排错工作台 |

### 2026-03-28 第 25 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 给项目代码补齐系统性中文注释，并把后续开发必须带中文注释写入正式文档 |
| 输入 | 已经逐步复杂化的策略、回测、执行、数据、Dashboard 与测试代码 |
| 产出 | 核心源码中文模块说明、函数说明、关键分支注释；测试中文说明；`README_DEV.md` 注释规范章节；工作记录规则更新 |
| 结果 | 现在核心代码不再只是“能读结构”，而是可以顺着中文注释理解主流程、状态机和测试意图，后续也有明确规范可继续遵守 |
| 为什么这么做 | 因为项目进入中期以后，真正限制迭代速度的往往不是功能本身，而是代码越来越难读；把注释提升成正式工程标准，能显著降低后续维护、交接和复盘成本。 |
| 未完成 | 新功能继续开发时仍需按同样标准持续补充中文注释，不能只做一次性补丁 |
| 备注 | 这一轮属于“工程可维护性升级”，目的是把项目从个人记忆驱动，推进到文档和代码双可读状态 |

### 2026-03-28 第 26 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 给订单事件补上更接近券商接口的语义层，避免后续接 Schwab 时把当前状态机整体推倒 |
| 输入 | 已有本地订单状态机、生命周期查询、历史页排错能力 |
| 产出 | `broker_status`、`status_detail` 字段，数据库迁移，查询接口同步，历史页展示 broker 语义 |
| 结果 | 订单事件现在同时具备“本地状态”和“更接近券商语义的状态”，后续接真实订单接口时映射成本更低 |
| 为什么这么做 | 因为 `filled/open/cancelled` 这些本地状态虽然够当前项目内部使用，但还不足以表达真实券商世界里的 `pending_new/working/replaced/...` 语义；越早补这层映射，后面越不容易返工。 |
| 未完成 | 继续细化 broker 状态映射表、补更多 cancel/replace reason、接真实 Schwab 状态时做最终对齐 |
| 备注 | 这一步属于“实盘接入前的概念对齐工作”，价值在于降低后续接券商 API 的语义落差 |

### 2026-03-28 第 27 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让历史页不仅能显示 broker 语义，还能直接按 broker 状态收缩排错范围 |
| 输入 | 已有 `broker_status` / `status_detail` 字段和历史页订单生命周期表 |
| 产出 | `broker-filter`、URL hash 同步、orders/lifecycles 联动的 broker 状态筛选 |
| 结果 | 现在历史页可以直接按 `pending_new/working/replaced/filled/cancelled/rejected` 等 broker 语义过滤 |
| 为什么这么做 | 因为 broker 语义真正有价值的场景，是快速找出“哪些单在 working、哪些单被 replaced、哪些单被 rejected”；没有筛选，这层信息只会停留在展示层。 |
| 未完成 | broker 状态摘要卡片、更细的 broker detail 聚合、真实 Schwab 状态对齐 |
| 备注 | 这一步把 broker 语义从“被记录”推进到“可直接用于排错” |

### 2026-03-28 第 28 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让回测执行记录具备更接近真实运行控制器的重试与保护模式元数据 |
| 输入 | 已有 `backtest_executions` 生命周期记录、stale recovery 和重复执行保护 |
| 产出 | `attempt_number`、`recovered_execution_count`、`consecutive_failures_before_start`、`protection_mode`、`protection_reason` 字段与测试 |
| 结果 | 系统现在不只是知道一次执行成功或失败，还知道这是第几次尝试、启动前已连续失败几次，以及是否已经进入保护模式 |
| 为什么这么做 | 因为自动重试和运行保护不是一个按钮，而是一套状态判断；只有先把这些元数据记录清楚，后面做自动重试、保护停机和恢复策略才不会变成黑盒。 |
| 未完成 | 把 protection mode 做到可视化、再往上扩展真正的自动重试策略 |
| 备注 | 这一步是在给未来的运行控制器铺地基，不是最终形态，但非常关键 |

### 2026-03-28 第 29 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让执行重试与保护模式信息不只存在数据库里，还能被直接查询、展示和复盘 |
| 输入 | 已有 `backtest_executions` 重试/保护模式字段，但尚未接到 CLI 和历史页 |
| 产出 | `execution-detail` CLI、execution detail 查询接口、历史页执行摘要卡片、`Recent Executions` / `Execution Detail` 面板、执行上下文深链接联动 |
| 结果 | 现在不仅能看到回测 run 和订单生命周期，还能看到“这次执行是第几次尝试、启动前已经失败了几次、是否进入保护模式、最终关联到哪个 run” |
| 为什么这么做 | 因为运行控制问题和订单执行问题不是一个层级：前者回答“任务有没有健康启动和结束”，后者回答“订单后来怎么演化”。只有把 execution 这一层也显式展示出来，历史页才真正具备完整的复盘链路。 |
| 未完成 | 真正的自动重试策略、保护模式自动停机动作、execution 级别的更细粒度筛选 |
| 备注 | 这一步把执行控制元数据从“后端内部字段”推进成了“可日常使用的排错视图” |

### 2026-03-28 第 30 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让执行尝试面板从“可查看”继续推进到“可快速聚焦异常执行” |
| 输入 | 已有 `Recent Executions` / `Execution Detail` 面板，但尚未支持按执行状态快速收缩范围 |
| 产出 | `execution-status-filter`、URL hash 同步、按 `completed/failed/abandoned/running/protection` 过滤执行表 |
| 结果 | 现在排查运行控制问题时，可以直接只看失败执行、被恢复的中断执行，或已经进入保护模式的启动尝试 |
| 为什么这么做 | 因为执行层的真实排错动作通常不是浏览全部记录，而是先把视角压缩到最可疑的那几类尝试；没有筛选，执行面板就还只是展示层，而不是排错工具。 |
| 未完成 | execution 级异常摘要卡片、更细的失败原因聚合、自动重试策略的真正执行动作 |
| 备注 | 这一步把执行视图进一步从“观察面板”推进成“可操作的排错面板” |

### 2026-03-28 第 31 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让回测执行生命周期真正具备“失败后再试”和“保护模式下主动拦截”的控制动作 |
| 输入 | 已有 execution 元数据、attempt number、连续失败计数和 protection mode 标记，但还没有实际控制流 |
| 产出 | `max_retry_attempts`、`protection_mode_failure_threshold`、`skip_run_on_protection_mode` 配置；`persist_backtest_run` 自动重试；`blocked` 执行状态；对应集成测试 |
| 结果 | 现在一次持久化回测调用如果遇到瞬时失败，会自动新建下一次 execution 重试；如果启动前已经连续失败到阈值，且配置要求拦截，就会直接返回 `blocked` 而不是继续盲目运行 |
| 为什么这么做 | 因为“知道自己已经连续失败了很多次”和“真的停止继续撞墙”是两回事。只有把重试和拦截动作落实到主流程里，execution 元数据才真正变成运行控制器，而不是事后统计字段。 |
| 未完成 | 区分可重试/不可重试错误类型、指数退避、更加细粒度的保护模式恢复策略 |
| 备注 | 这是项目第一次把运行控制从“观察能力”推进到“实际控制动作” |

### 2026-03-28 第 32 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让新引入的 `blocked` 执行状态在历史页里和其它状态一样可见、可筛、可总结 |
| 输入 | 已有执行表和执行状态筛选，但新增 `blocked` 后还没有同步到摘要卡片和过滤器 |
| 产出 | `Execution Blocked` 摘要卡片、`blocked` 筛选项、历史页字符串与测试更新 |
| 结果 | 现在 protection mode 主动拦截的执行不再只是数据库里的一个状态，而是会直接进入历史页的常规排错视图 |
| 为什么这么做 | 因为一旦运行控制开始做“主动拦截”，这些事件就和普通失败一样重要，甚至更值得第一时间被看见；如果历史页不接住它，控制器和观测面就会再次脱节。 |
| 未完成 | blocked 执行的失败原因聚合、按保护原因分组统计、更加明确的异常优先排序 |
| 备注 | 这一步确保了“控制动作变化”也同步变成“观察能力变化” |

### 2026-03-28 第 33 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 给自动重试链路补上“同一次外部触发”的关联标识，避免多次 attempt 在历史中看起来像彼此无关 |
| 输入 | 已有自动重试与 blocked 状态，但 execution 之间还缺少同一次请求级关联 |
| 产出 | `request_id` 字段、execution 查询返回 request_id、历史页执行表展示 request_id、集成测试与 CLI smoke |
| 结果 | 现在同一次 `persist_backtest_run` 调用产生的多次 execution attempt 会共享同一个 `request_id`，后续做更复杂的重试链、恢复链和对账链时都有了稳定锚点 |
| 为什么这么做 | 因为有了自动重试之后，单看 `attempt_number` 还不够，它只能说明“这是第几次尝试”，却不能说明“这些尝试本来是不是同一轮调用”。`request_id` 补的就是这层跨 attempt 的关联语义。 |
| 未完成 | 基于 request_id 的历史页聚合、单次请求级摘要卡片、retry chain 可视化 |
| 备注 | 这一步是在给“真正的运行控制器链路追踪”继续打底 |

### 2026-03-28 第 34 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 `request_id` 不只存在于字段层，而是变成可以直接用于复盘整条重试链的查询和页面能力 |
| 输入 | 已有 `request_id` 字段与 execution attempt 记录，但还缺少 request 级聚合查询和历史页联动 |
| 产出 | `execution-requests` / `execution-request-detail` CLI、request 级 repository 查询、历史页 `Execution Requests` / `Execution Request Detail` 面板、request 级摘要卡片 |
| 结果 | 现在同一次 `persist_backtest_run` 调用产生的多次 execution attempt，不只是共享同一个 `request_id`，还可以作为一整条 retry chain 被列出、点开、联动查看 |
| 为什么这么做 | 因为一旦系统开始自动重试，真正需要排查的对象就不再只是单个 execution，而是“这一整次外部请求最终经历了什么”。request 级视图补上的就是这层更接近真实运维的观察方式。 |
| 未完成 | request 级失败原因聚合、按 request 粒度的异常优先排序、更强的 retry chain 可视化 |
| 备注 | 这一步让 execution retry control flow 真正具备了“请求链级别”的可观测性 |

### 2026-03-28 第 35 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 把单次回测 dashboard 从“结果展示页”推进成更完整的静态研究工作台 |
| 输入 | 已有摘要卡片、净值/回撤曲线、近期成交/订单和审计表，但还缺少参数面板与运行上下文 |
| 产出 | `run_context` / `chart_summary` / `audit_summary` / `config_sections` payload；升级后的单次 dashboard HTML 布局；对应测试更新 |
| 结果 | 现在单次 dashboard 会同时展示研究输入、账户结果、执行健康度和审计活动，页面结构已经更接近正式研究面板，而不只是单次结果回显 |
| 为什么这么做 | 因为研究系统不只要告诉你“这次赚没赚钱”，还要把“用了什么参数、跑了哪段数据、最近发生了哪些审计动作”一起放在眼前；否则单次 dashboard 依然只能算结果页，难以支撑后续复盘与调参。 |
| 未完成 | 更细的图表注解、点击联动、参数对比视图、日志持久化后的更深 drill-down |
| 备注 | 这一步完成了下一步计划里“更完整 dashboard 页面骨架”的第一阶段落地 |

### 2026-03-28 第 36 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让自动重试从“看见异常就再试”升级成“先判断失败类型，再决定是否继续”的可解释运行控制策略 |
| 输入 | 已有自动重试、request 链追踪和 execution/request 历史页，但失败仍然缺少明确分类和决策说明 |
| 产出 | `RetryableExecutionError` / `NonRetryableExecutionError`、`retry_backoff_seconds` 配置、`retryable` / `retry_decision` / `failure_class` 持久化字段、带决策语义的日志、历史页展示与测试 |
| 结果 | 现在系统不仅知道某次 execution 失败了，还知道它是不是可重试、这次被标记成 `retry_scheduled` / `final_failure` / `blocked_protection_mode` / `completed` 的哪一种决策，并按这个判断真正继续或停止 |
| 为什么这么做 | 因为真正危险的不是“没有重试”，而是“对所有错误都盲目重试”。输入错误、业务错误和瞬时错误应该用不同策略处理；把失败分类和决策理由显式化，运行控制器才既稳又可解释。 |
| 未完成 | 更细的错误类别映射、指数退避、按失败类别聚合 request 级异常、实盘环境下的错误分层 |
| 备注 | 这一轮把运行控制从“有重试动作”推进到了“有重试策略” |

### 2026-03-28 第 37 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让运行控制器不只知道“要不要重试”，还知道“该等多久、哪条 request 链最异常、应该先看哪一条” |
| 输入 | 已有失败分类和重试决策，但退避策略仍然固定，request 级视图也还缺少健康度、异常分数和失败类别聚合 |
| 产出 | `retry_backoff_strategy` / `retry_backoff_multiplier` / `max_retry_backoff_seconds` 配置；退避计算与日志；request 级 `health_label` / `anomaly_score` / `failure_classes` / `dominant_failure_class` 聚合；历史页 `Request Anomalies` 面板与摘要卡片；对应测试 |
| 结果 | 现在系统不仅能区分“该不该重试”，还能按线性或指数退避真正等待，并把最值得优先排查的 request 链直接排出来，显示它到底是因为最终失败、保护模式还是某类失败反复出现而变得异常 |
| 为什么这么做 | 因为真实运行控制里，最耗时间的往往不是“重试动作本身”，而是值班时判断“应该先看哪条链、它危险在哪里、这次等待是不是合理”。把退避和异常聚合显式化，控制器才更接近真正可运维的形态。 |
| 未完成 | 更细的错误类别映射、按错误类别定制退避策略、跨 request 的失败趋势分析、通知层告警联动 |
| 备注 | 这一轮把运行控制继续从“可解释策略”推进成了“可排序、可优先级排查的控制器视图” |

### 2026-03-28 第 38 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 protection mode 不只是“触发后一直卡住”，而是具备可配置冷却窗口、自动恢复和显式状态查询 |
| 输入 | 已有 protection mode 拦截，但还缺少“多久后允许恢复”这一层控制，也缺少独立查询当前守护状态的命令 |
| 产出 | `protection_mode_cooldown_seconds` 配置；`protection_cooldown_until` 持久化字段；create execution 时的冷却判断；到期后自动恢复日志；`protection-status` CLI；历史页 cooldown 摘要和表格字段；对应测试 |
| 结果 | 现在系统在连续失败后不仅能进入保护模式，还能在冷却窗口内继续拦截、在冷却期过后自动允许恢复，并把“何时解封”明确记录在 execution/request/history 视图里 |
| 为什么这么做 | 因为真实守护器不能只会“拉闸”，还要知道“什么时候可以安全地重新送电”。没有冷却恢复，保护模式只能靠人工介入；加上冷却和状态查询后，系统才更接近长期运行的自动控制器。 |
| 未完成 | 更细的冷却策略、按失败类别设置不同冷却时间、保护模式通知告警、跨天失败趋势分析 |
| 备注 | 这一轮把 protection mode 从“单纯拦截”推进成了“有恢复窗口的守护模式” |

### 2026-03-28 第 39 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让关键运行控制事件不只存在于日志和历史页里，而是提升成真正可消费、可转发的通知事件 |
| 输入 | 已有重试、拦截、冷却恢复等控制动作，但通知系统还只有配置壳子，没有实际事件落地与消费出口 |
| 产出 | `notification_events` 表、本地 JSONL outbox、`notifications` CLI、history 页 `Recent Notifications` 面板、关键 execution 事件的通知触发点、对应测试 |
| 结果 | 现在执行重试、最终失败、保护模式拦截、冷却恢复这些关键运行事件都会被记录成通知事件；启用通知后还会写入本地 outbox，为后续接 Telegram/微信留出稳定接口 |
| 为什么这么做 | 因为“系统自己知道出事了”和“外部有人能收到可消费的告警”是两回事。先把通知事件和 outbox 骨架搭起来，后面接真实渠道时就不用再回头侵入业务主流程。 |
| 未完成 | 真实 Telegram/微信发送器、失败重投、通知去重、告警聚合压缩和静默窗口 |
| 备注 | 这一轮把通知层从“配置占位”推进成了“有事件、有出口、有页面可见性”的真实骨架 |

### 2026-03-28 第 40 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让通知系统从“只会产生 queued 事件”升级成“有 worker、会尝试投递、会记录失败原因和最终放弃”的完整骨架 |
| 输入 | 已有 `notification_events`、本地 outbox、`notifications` CLI 和 history 告警面板，但还缺少真正的投递推进过程 |
| 产出 | `delivery_log_path` / `max_delivery_attempts` 配置；notification delivery 字段 `delivery_attempts` / `delivered_at` / `last_error`；本地 adapter worker；`notifications-deliver` CLI；history 页通知状态筛选、Attempts/Last Error 展示和新的告警统计卡片；对应测试 |
| 结果 | 现在通知事件不再只停留在 `queued`，而是可以被本地 worker 继续推进到 `dispatched`、`delivery_failed_retryable`、`delivery_failed_final`；系统能清楚看到每条通知试了几次、最后一次为什么失败、还有没有继续重试的必要 |
| 为什么这么做 | 因为真正的通知系统不是“把事件写进 outbox 就结束了”，而是要回答三个更实际的问题：这条告警有没有被 worker 接手、worker 试了几次、最终到底发成了还是放弃了。先把这个内层状态机做扎实，后面接 Telegram/微信时才能稳稳地替换 adapter，而不是重新改一遍整条业务链。 |
| 未完成 | 真实 Telegram/微信 provider、按渠道配置 target、投递去重、批量聚合、静默窗口、定时 worker |
| 备注 | 这一轮把通知层从“有告警事件”推进成了“有投递推进过程和失败闭环的运维骨架” |

### 2026-03-28 第 41 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让通知重投不再是“立刻反复重撞”，而是具备独立的退避时间窗和“下一次最早何时再试”的可见性 |
| 输入 | 已有通知 worker、投递尝试次数和失败原因，但失败后还缺少重投节奏控制，也看不到哪条通知暂时不该再试 |
| 产出 | `delivery_retry_backoff_seconds` / `delivery_retry_backoff_strategy` / `delivery_retry_backoff_multiplier` / `max_delivery_retry_backoff_seconds` 配置；`next_delivery_attempt_at` 字段；通知 worker 的延后重投逻辑；history 页 `Retrying Alerts` 卡片和 `Next Try` 列；对应测试 |
| 结果 | 现在通知在 adapter 失败后，不会无脑立刻再次处理，而是会带着 `next_delivery_attempt_at` 进入下一轮等待；只有到了允许的时间点，worker 才会重新接手这条告警 |
| 为什么这么做 | 因为通知渠道的失败通常和交易任务失败不是一回事。交易任务可能需要尽快再试，但通知渠道如果瞬时异常，立刻重复撞击往往只会制造更多噪音。给通知系统单独加上退避时间窗，才能让告警链路既可恢复，又不会把自己变成新的噪音源。 |
| 未完成 | 真实定时 worker、按 provider 区分退避策略、静默窗口、聚合压缩、外部渠道确认回执 |
| 备注 | 这一轮把通知层从“会失败重试”推进成了“有节奏地延后重投”的更真实运维骨架 |

### 2026-03-28 第 42 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让通知系统学会“少说废话”：同类告警短时间内不重复刷屏，同时提供聚合视角快速看近况 |
| 输入 | 已有通知事件、worker、退避时间窗，但同类失败仍可能频繁出现，history 里也还缺少一个更偏值班的告警聚合视图 |
| 产出 | `silence_window_seconds` 配置；通知 `notification_key` / `silenced_until` / `suppressed_duplicate_count` / `last_suppressed_at` 字段；重复告警压缩逻辑；`notification-summary` CLI；history 页 `Notification Summary` 面板、Silenced/Suppressed 展示与摘要卡片；对应测试 |
| 结果 | 现在同类告警在静默窗口内会被压到已有通知事件上，而不是重复写新行和新 outbox；同时可以直接按 category / severity / status 看近期香港告警汇总，而不用逐条翻最近事件 |
| 为什么这么做 | 因为真正影响人效率的，往往不是“没有告警”，而是“太多重复告警把真正重要的信号淹没了”。先让通知系统学会降噪，再提供聚合视角，值班时才能更快看出最近到底是哪一类问题最活跃、哪类告警被压得最多。 |
| 未完成 | 更细粒度静默策略、按 provider/类别分别配置窗口、批量 digest、人工确认/ack、外部渠道回执 |
| 备注 | 这一轮把通知层从“会发、会重试”推进成了“会降噪、会聚合”的更成熟运维视角 |

### 2026-03-28 第 43 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让通知不只是“发出来”，还要能被显式标记成“我已经看过/处理过” |
| 输入 | 已有通知事件、静默窗口和聚合视图，但仍缺少一个最基础的运维动作：把某条告警从“待关注”切换成“已确认” |
| 产出 | `notification-ack` CLI；`acknowledged_at` / `acknowledged_note` 字段；通知确认仓储与应用方法；history 页 Acked/Unacked 摘要卡片和列展示；对应测试 |
| 结果 | 现在通知事件不只是被系统生成、投递、静默和汇总，还能被明确打上“已确认”状态，方便在历史页区分哪些是仍需关注的告警，哪些已经被人接手 |
| 为什么这么做 | 因为真正的值班闭环里，“告警发出”只是开始，不是结束。如果没有确认状态，页面里永远只有“发生过什么”，却没有“哪些已经有人处理”。把 ack 加进去后，通知系统才开始具备最基本的运维协作语义。 |
| 未完成 | 按人记录确认者、撤销确认、批量 ack、告警升级/分派、外部渠道双向回执 |
| 备注 | 这一轮把通知层从“系统视角可见”推进成了“人与系统可协作”的更完整闭环 |

### 2026-03-28 第 44 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让高优先级告警在长时间无人确认时，不只是“躺在那里”，而是能被系统明确升级标记出来 |
| 输入 | 已有通知 ack 和聚合视图，但仍缺少一个关键运维动作：识别并标记“长期未确认的重要告警” |
| 产出 | `escalation_window_seconds` / `escalation_min_severity` 配置；`escalated_at` / `escalation_level` / `escalation_reason` 字段；`notification-escalate` CLI；history 升级统计与表格列；对应测试 |
| 结果 | 现在系统可以扫描最近通知，把超过阈值且仍未确认的高优先级告警标记成 `stale_unacknowledged` 升级状态，并把升级时间与原因明确记录下来 |
| 为什么这么做 | 因为很多真正危险的问题，不是“告警没发出来”，而是“告警发出来了，但没人处理，也没人知道它已经拖了多久”。把未确认超时的告警提升成明确的升级状态，值班视角才真正开始有优先级和时效语义。 |
| 未完成 | 真正的分派/升级路线、升级通知二次发送、按人/班次 SLA、批量 ack/批量 escalate、外部协作系统联动 |
| 备注 | 这一轮把通知层从“可确认”推进成了“可升级”的更完整值班闭环 |

### 2026-03-28 第 45 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让告警不只是“有人看过”，还要明确“现在是谁负责继续跟进” |
| 输入 | 已有通知 ack 和 escalation，但页面里仍缺少责任归属语义，导致高优先级告警即使升级了，也很难快速看出有没有人接手 |
| 产出 | `notification-assign` CLI；`assigned_to` / `assigned_at` / `assignment_note` 字段；通知分派仓储与应用方法；history 页 Owner 过滤、Assigned/Unassigned/Escalated Unowned 摘要卡片，以及通知表 Owner/Assigned At/Assign Note 展示；对应测试 |
| 结果 | 现在通知事件除了能被确认、升级，还能被明确分派给某个负责人；历史页可以直接看哪些告警已经有人接手，哪些升级告警仍然无人负责 |
| 为什么这么做 | 因为值班闭环里真正容易掉链子的，不是“页面上没有状态”，而是“页面上有很多状态，却没人知道自己到底该接哪一条”。把 assignment 语义补进去后，系统才开始真正回答“这件事归谁”，而不是只停留在“这件事发生过、有人看过没有”。 |
| 未完成 | 分派撤销、按班次/角色自动分派、批量分派、SLA 超时再升级、外部协作系统同步 |
| 备注 | 这一轮把通知层从“可升级”推进成了“可归属、可协作”的更完整值班骨架 |

### 2026-03-28 第 46 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 owner assignment 不只是写进单条告警，还能一眼看出“谁手上压了多少活” |
| 输入 | 已有 assignment 字段和 owner 过滤，但还缺少一个汇总视角，导致 operator 仍要逐条翻通知表才能判断每个 owner 的当前负载 |
| 产出 | `notification-owner-summary` CLI；按 owner 聚合的 `event_count` / `unacknowledged_count` / `escalated_count` / `open_high_priority_count`；history 页 `Notification Owners` 面板；对应测试 |
| 结果 | 现在系统可以直接回答“ops.alice 手上还有多少未确认告警、多少已经升级、多少仍是高优先级未处理”，也能快速识别 `(unassigned)` 桶里是否还压着风险项 |
| 为什么这么做 | 因为 assignment 解决的是“这件事归谁”，但值班管理还需要回答“这个人现在压了多少事”。只有把 owner 负载汇总出来，assignment 才真正从单条字段升级成可运营的工作视图。 |
| 未完成 | 自动负载均衡分派、按班次/角色看 owner 汇总、owner 级 SLA、批量移交、外部值班系统同步 |
| 备注 | 这一轮把通知层从“能分派责任”推进成了“能看责任负载”的更成熟协作视角 |

### 2026-03-28 第 47 轮

| 项目 | 内容 |
| :--- | :--- |
| 目标 | 让 owner 视图不只是看负载，还能指出“哪些已接手事项已经拖过 SLA” |
| 输入 | 已有 assignment 和 owner workload，但仍缺少一个明确的超时视角，导致 operator 只能知道“手上有多少事”，却不知道“哪些已经拖太久” |
| 产出 | `assignment_sla_seconds` 配置；`notification-sla` CLI；history `Notification SLA` 面板；`SLA Breached` 摘要卡片；基于 `assigned_at` / `acknowledged_at` 动态计算的 SLA 过期视图；对应测试 |
| 结果 | 现在系统可以直接列出“已分派但仍未确认且超出 SLA”的告警，并显示负责人、分派时间、当前年龄、SLA 阈值和超时秒数 |
| 为什么这么做 | 因为 assignment 只能说明“这件事归谁”，却不能说明“归他之后已经拖了多久”。对真实环境的单人操作而言，SLA 过期视图可以把“我知道这件事存在”升级成“我知道它已经拖到必须先处理”。 |
| 未完成 | 分级 SLA、按 severity/类别设置不同阈值、SLA 到期自动再次升级、owner 级告警催办、外部值班工具同步 |
| 备注 | 这一轮把通知层从“可分派、可汇总”推进成了“可追踪处理时效”的更完整运维视图 |

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

当前这个记录表已经升级为教学版。后续如果你愿意，我还可以继续把它拆成：

- 看板版：更像项目管理表
- 里程碑版：更适合看进度
- 复盘版：更强调踩坑、取舍和经验总结
