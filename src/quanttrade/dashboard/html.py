"""静态 HTML 渲染器。

这个文件负责把 Python 侧准备好的 payload 直接拼成完整 HTML 页面。
其中页面内的 JS 只做轻量交互，不依赖后端服务。
"""

from __future__ import annotations

import json
from pathlib import Path


def render_dashboard_html(payload: dict[str, object], output_path: str) -> str:
    """渲染单次回测 dashboard 页面。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data_json = json.dumps(payload, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QuantTrade Dashboard</title>
  <style>
    :root {{
      --bg: #09111f;
      --panel: #101b2e;
      --panel-alt: #13233b;
      --panel-alt-2: #162945;
      --line: rgba(255, 255, 255, 0.08);
      --text: #e8f0ff;
      --muted: #8ea5c6;
      --accent: #4fb3ff;
      --accent-2: #8ce99a;
      --warn: #ffb65c;
      --danger: #ff7b7b;
      --shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(79, 179, 255, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(140, 233, 154, 0.10), transparent 24%),
        linear-gradient(180deg, #06101d 0%, var(--bg) 100%);
      color: var(--text);
    }}

    .shell {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}

    .hero {{
      display: grid;
      gap: 16px;
      margin-bottom: 24px;
    }}

    .eyebrow {{
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent);
      font-size: 12px;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(32px, 5vw, 58px);
      line-height: 0.95;
      font-weight: 700;
    }}

    .subcopy {{
      max-width: 760px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
    }}

    .context-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .context-chip {{
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--line);
      color: var(--text);
      font-size: 13px;
    }}

    .context-chip strong {{
      color: var(--accent);
      font-weight: 600;
      margin-right: 6px;
    }}

    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}

    .card, .panel {{
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)), var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
    }}

    .card {{
      padding: 18px;
      min-height: 126px;
    }}

    .card-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 14px;
    }}

    .card-value {{
      font-size: 30px;
      font-weight: 700;
      letter-spacing: -0.03em;
    }}

    .layout {{
      display: grid;
      grid-template-columns: 1.55fr 1fr;
      gap: 16px;
    }}

    .stack {{
      display: grid;
      gap: 16px;
    }}

    .panel {{
      padding: 18px;
      overflow: hidden;
    }}

    .panel-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 16px;
    }}

    .panel-title {{
      margin: 0;
      font-size: 18px;
      font-weight: 650;
    }}

    .panel-note {{
      color: var(--muted);
      font-size: 13px;
    }}

    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}

    .stats-grid.compact .stat dd {{
      font-size: 18px;
    }}

    .stat {{
      padding: 14px;
      border-radius: 16px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
    }}

    .stat dt {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }}

    .stat dd {{
      margin: 0;
      font-size: 22px;
      font-weight: 650;
    }}

    .chart {{
      height: 260px;
      position: relative;
      background:
        linear-gradient(180deg, rgba(79,179,255,0.05), transparent 55%),
        var(--panel-alt);
      border-radius: 18px;
      border: 1px solid var(--line);
      padding: 12px;
    }}

    svg {{
      width: 100%;
      height: 100%;
      display: block;
    }}

    .config-stack {{
      display: grid;
      gap: 12px;
    }}

    .config-section {{
      padding: 14px;
      border-radius: 16px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
    }}

    .config-title {{
      margin: 0 0 12px;
      font-size: 14px;
      color: var(--text);
      letter-spacing: 0.02em;
    }}

    .kv-list {{
      display: grid;
      gap: 8px;
    }}

    .kv-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      font-size: 13px;
    }}

    .kv-row:last-child {{
      border-bottom: 0;
      padding-bottom: 0;
    }}

    .kv-label {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 11px;
    }}

    .kv-value {{
      color: var(--text);
      text-align: right;
      max-width: 58%;
      word-break: break-word;
    }}

    .table-wrap {{
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}

    th, td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }}

    th {{
      color: var(--muted);
      font-weight: 600;
    }}

    .buy {{ color: var(--accent-2); }}
    .sell {{ color: var(--warn); }}
    .muted {{ color: var(--muted); }}
    .danger {{ color: var(--danger); }}
    .empty {{
      color: var(--muted);
      text-align: center;
      padding: 20px 0;
    }}

    @media (max-width: 980px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}

      .stats-grid {{
        grid-template-columns: 1fr;
      }}

      .kv-row {{
        align-items: flex-start;
        flex-direction: column;
      }}

      .kv-value {{
        max-width: 100%;
        text-align: left;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">QuantTrade Report</div>
      <h1>Backtest Dashboard</h1>
      <div class="subcopy">
        A static research workspace generated from the QuantTrade backtest pipeline.
        It surfaces strategy parameters, execution constraints, audit activity, account state,
        and recent order flow in one page so a single run can be reviewed without starting a server.
      </div>
      <div id="run-context-strip" class="context-strip"></div>
    </section>

    <section id="summary-cards" class="card-grid"></section>

    <section class="layout">
      <div class="stack">
        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Equity Curve</h2>
            <div class="panel-note">Mark-to-market account equity by bar</div>
          </div>
          <div class="chart"><svg id="equity-chart" viewBox="0 0 800 260" preserveAspectRatio="none"></svg></div>
          <dl id="chart-summary" class="stats-grid compact" style="margin-top: 14px;"></dl>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Drawdown Curve</h2>
            <div class="panel-note">Peak-to-current drawdown percentage</div>
          </div>
          <div class="chart"><svg id="drawdown-chart" viewBox="0 0 800 260" preserveAspectRatio="none"></svg></div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Recent Trades</h2>
            <div class="panel-note">Latest fills from the backtest run</div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Price</th>
                  <th>Qty</th>
                  <th>Commission</th>
                  <th>PnL</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="recent-trades"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Recent Orders</h2>
            <div class="panel-note">Order lifecycle records from the simulator</div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Status</th>
                  <th>Req Qty</th>
                  <th>Filled</th>
                  <th>Remaining</th>
                  <th>Request</th>
                  <th>Fill</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="recent-orders"></tbody>
            </table>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Run Context</h2>
            <div class="panel-note">Snapshot of the current research run</div>
          </div>
          <div id="run-context" class="kv-list"></div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Parameter Panels</h2>
            <div class="panel-note">Strategy, risk, and execution inputs used for this run</div>
          </div>
          <div id="config-sections" class="config-stack"></div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Account Summary</h2>
            <div class="panel-note">End-of-run account state</div>
          </div>
          <dl id="account-summary" class="stats-grid"></dl>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Performance Summary</h2>
            <div class="panel-note">Compact performance snapshot</div>
          </div>
          <dl id="performance-summary" class="stats-grid"></dl>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Order Summary</h2>
            <div class="panel-note">Execution pipeline health snapshot</div>
          </div>
          <dl id="order-summary" class="stats-grid"></dl>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Audit Summary</h2>
            <div class="panel-note">Signal and controller activity condensed into counters</div>
          </div>
          <dl id="audit-summary" class="stats-grid"></dl>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Audit Timeline</h2>
            <div class="panel-note">Latest strategy and order events</div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>Signal</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="audit-log"></tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  </main>

  <script>
    const payload = {data_json};

    // 统一数字格式化，避免各个渲染函数各自处理小数位。
    function fmt(value) {{
      if (typeof value === "boolean") {{
        return value ? "true" : "false";
      }}
      return typeof value === "number" ? value.toLocaleString(undefined, {{ maximumFractionDigits: 4 }}) : value;
    }}

    function prettyKey(value) {{
      return String(value).replace(/_/g, " ");
    }}

    function emptyRow(colspan, label) {{
      return `<tr><td colspan="${{colspan}}" class="empty">${{label}}</td></tr>`;
    }}

    // 顶部卡片只负责回答“这次回测结果大概怎么样”。
    function renderCards() {{
      const target = document.getElementById("summary-cards");
      target.innerHTML = payload.summary_cards.map(card => `
        <article class="card">
          <div class="card-label">${{card.label}}</div>
          <div class="card-value">${{fmt(card.value)}}</div>
        </article>
      `).join("");
    }}

    function renderContextStrip() {{
      const target = document.getElementById("run-context-strip");
      const context = payload.run_context || {{}};
      const chips = [
        ["symbol", context.symbol],
        ["timeframe", context.timeframe],
        ["bars", context.bars_processed],
        ["strategy", context.strategy_name],
      ];
      target.innerHTML = chips.map(([label, value]) => `
        <div class="context-chip"><strong>${{label}}</strong>${{fmt(value)}}</div>
      `).join("");
    }}

    // 统计区域用于展示账户、绩效、订单健康度等成组信息。
    function renderStats(id, stats) {{
      const target = document.getElementById(id);
      target.innerHTML = Object.entries(stats).map(([key, value]) => `
        <div class="stat">
          <dt>${{prettyKey(key)}}</dt>
          <dd>${{fmt(value)}}</dd>
        </div>
      `).join("");
    }}

    function renderKeyValueList(id, values) {{
      const target = document.getElementById(id);
      target.innerHTML = Object.entries(values).map(([key, value]) => `
        <div class="kv-row">
          <div class="kv-label">${{prettyKey(key)}}</div>
          <div class="kv-value">${{fmt(value)}}</div>
        </div>
      `).join("");
    }}

    function renderConfigSections() {{
      const target = document.getElementById("config-sections");
      target.innerHTML = payload.config_sections.map(section => `
        <section class="config-section">
          <h3 class="config-title">${{section.title}}</h3>
          <div class="kv-list">
            ${{section.items.map(item => `
              <div class="kv-row">
                <div class="kv-label">${{prettyKey(item.label)}}</div>
                <div class="kv-value">${{fmt(item.value)}}</div>
              </div>
            `).join("")}}
          </div>
        </section>
      `).join("");
    }}

    // 近期成交表帮助我们快速确认最近有哪些真实 fill。
    function renderTrades() {{
      const target = document.getElementById("recent-trades");
      if (!payload.recent_trades.length) {{
        target.innerHTML = emptyRow(7, "No fills were generated in this run.");
        return;
      }}
      target.innerHTML = payload.recent_trades.map(trade => `
        <tr>
          <td>${{trade.timestamp}}</td>
          <td class="${{trade.side === "BUY" ? "buy" : "sell"}}">${{trade.side}}</td>
          <td>${{fmt(trade.price)}}</td>
          <td>${{fmt(trade.quantity)}}</td>
          <td>${{fmt(trade.commission)}}</td>
          <td>${{fmt(trade.pnl)}}</td>
          <td>${{trade.reason}}</td>
        </tr>
      `).join("");
    }}

    // 近期订单表会保留更多执行细节，例如已成交数量和剩余数量。
    function renderOrders() {{
      const target = document.getElementById("recent-orders");
      if (!payload.recent_orders.length) {{
        target.innerHTML = emptyRow(9, "No order events were generated in this run.");
        return;
      }}
      target.innerHTML = payload.recent_orders.map(order => `
        <tr>
          <td>${{order.timestamp}}</td>
          <td class="${{order.side === "BUY" ? "buy" : "sell"}}">${{order.side}}</td>
          <td>${{order.status}}</td>
          <td>${{fmt(order.quantity)}}</td>
          <td>${{fmt(order.filled_quantity ?? 0)}}</td>
          <td>${{fmt(order.remaining_quantity ?? 0)}}</td>
          <td>${{fmt(order.requested_price)}}</td>
          <td>${{fmt(order.fill_price)}}</td>
          <td>${{order.reason}}</td>
        </tr>
      `).join("");
    }}

    // 审计日志表主要回答“系统为什么会这样决定”。
    function renderAuditLog() {{
      const target = document.getElementById("audit-log");
      if (!payload.audit_timeline.length) {{
        target.innerHTML = emptyRow(4, "No audit events were recorded.");
        return;
      }}
      target.innerHTML = payload.audit_timeline.map(event => `
        <tr>
          <td>${{event.timestamp}}</td>
          <td>${{event.event}}</td>
          <td>${{event.signal}}</td>
          <td>${{event.reason}}</td>
        </tr>
      `).join("");
    }}

    // 把时间序列数据转成 SVG 折线图坐标。
    function polylinePoints(items, accessor, width, height, invert = false) {{
      if (!items.length) return "";
      const values = items.map(accessor);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      return items.map((item, index) => {{
        const x = (index / Math.max(items.length - 1, 1)) * width;
        const raw = accessor(item);
        const normalized = (raw - min) / range;
        const y = invert ? normalized * height : height - normalized * height;
        return `${{x.toFixed(2)}},${{y.toFixed(2)}}`;
      }}).join(" ");
    }}

    // 用统一方式渲染净值和回撤两种曲线。
    function renderChart(id, items, accessor, stroke, fill) {{
      const svg = document.getElementById(id);
      if (!items.length) {{
        svg.innerHTML = "";
        return;
      }}
      const width = 800;
      const height = 260;
      const points = polylinePoints(items, accessor, width, height, false);
      const firstX = 0;
      const lastX = width;
      const area = `${{points}} ${{lastX}},${{height}} ${{firstX}},${{height}}`;
      svg.innerHTML = `
        <defs>
          <linearGradient id="${{id}}-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${{fill}}" stop-opacity="0.4"></stop>
            <stop offset="100%" stop-color="${{fill}}" stop-opacity="0.02"></stop>
          </linearGradient>
        </defs>
        <polygon points="${{area}}" fill="url(#${{id}}-gradient)"></polygon>
        <polyline points="${{points}}" fill="none" stroke="${{stroke}}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
      `;
    }}

    renderContextStrip();
    renderCards();
    renderKeyValueList("run-context", payload.run_context);
    renderConfigSections();
    renderStats("account-summary", payload.account_summary);
    renderStats("performance-summary", payload.performance_summary);
    renderStats("chart-summary", payload.chart_summary);
    renderStats("order-summary", payload.order_summary);
    renderStats("audit-summary", payload.audit_summary);
    renderTrades();
    renderOrders();
    renderAuditLog();
    renderChart("equity-chart", payload.charts.equity_curve, item => item.equity, "#4fb3ff", "#4fb3ff");
    renderChart("drawdown-chart", payload.charts.drawdown_curve, item => item.drawdown_pct, "#ffb65c", "#ffb65c");
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)


def render_history_html(payload: dict[str, object], output_path: str) -> str:
    """渲染历史运行 dashboard 页面。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data_json = json.dumps(payload, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QuantTrade History</title>
  <style>
    :root {{
      --bg: #0a0f1a;
      --panel: #121a29;
      --panel-alt: #172235;
      --text: #edf3ff;
      --muted: #93a9c7;
      --accent: #62c0ff;
      --accent-2: #95f2b2;
      --warn: #ffbf69;
      --line: rgba(255,255,255,0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
      background:
        radial-gradient(circle at top right, rgba(98, 192, 255, 0.12), transparent 24%),
        linear-gradient(180deg, #050b14 0%, var(--bg) 100%);
      color: var(--text);
    }}
    .shell {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}
    .hero {{
      margin-bottom: 24px;
    }}
    .eyebrow {{
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 12px;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(30px, 5vw, 54px);
      line-height: 0.95;
    }}
    .subcopy {{
      color: var(--muted);
      max-width: 760px;
      line-height: 1.6;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 24px 50px rgba(0,0,0,0.22);
    }}
    .card {{
      padding: 18px;
    }}
    .card-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
    }}
    .card-value {{
      font-size: 30px;
      font-weight: 700;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 16px;
    }}
    .stack {{
      display: grid;
      gap: 16px;
    }}
    .panel {{
      padding: 18px;
    }}
    .panel-title {{
      margin: 0 0 4px;
      font-size: 18px;
    }}
    .panel-note {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 14px;
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    .toolbar label {{
      color: var(--muted);
      font-size: 13px;
    }}
    .toolbar select {{
      background: var(--panel-alt);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px 10px;
    }}
    .toolbar-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-left: auto;
    }}
    .link-button {{
      background: transparent;
      color: var(--accent);
      border: 0;
      padding: 0;
      cursor: pointer;
      font: inherit;
      text-align: left;
    }}
    .ghost-button {{
      background: transparent;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
    }}
    .deep-link {{
      color: var(--accent);
      text-decoration: none;
      font-size: 13px;
    }}
    .muted {{
      color: var(--muted);
      font-size: 13px;
    }}
    .context-line {{
      margin-bottom: 12px;
    }}
    .row-active {{
      background: rgba(98, 192, 255, 0.10);
    }}
    .row-anomaly {{
      box-shadow: inset 3px 0 0 rgba(255, 191, 105, 0.9);
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 11px 10px;
      border-bottom: 1px solid var(--line);
      white-space: nowrap;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .buy {{ color: var(--accent-2); }}
    .sell {{ color: var(--warn); }}
    @media (max-width: 980px) {{
      .layout {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">QuantTrade History</div>
      <h1>Run History Dashboard</h1>
      <div class="subcopy">
        A static history view generated from persisted backtest runs, order events, and audit events.
        This page is intended for reviewing how the system has behaved across multiple runs without starting an app server.
      </div>
    </section>

    <section id="summary-cards" class="card-grid"></section>

    <section class="layout">
      <div class="stack">
        <section class="panel">
          <h2 class="panel-title">Recent Runs</h2>
          <div class="panel-note">Most recent persisted backtest runs</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Symbol</th>
                  <th>Started</th>
                  <th>Lifecycles</th>
                  <th>Return %</th>
                  <th>Sharpe</th>
                  <th>Trades</th>
                </tr>
              </thead>
              <tbody id="runs-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Execution Requests</h2>
          <div class="panel-note">Grouped retry chains keyed by request ID</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Run ID</th>
                  <th>Health</th>
                  <th>Anomaly Score</th>
                  <th>Final</th>
                  <th>Attempts</th>
                  <th>Retried</th>
                  <th>Protected</th>
                  <th>Cooldown Until</th>
                  <th>Failure Mix</th>
                  <th>Decision Path</th>
                  <th>Path</th>
                </tr>
              </thead>
              <tbody id="request-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Request Anomalies</h2>
          <div class="panel-note">Prioritized request chains that deserve investigation first</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Health</th>
                  <th>Anomaly Score</th>
                  <th>Final</th>
                  <th>Retry Scheduled</th>
                  <th>Top Failure</th>
                </tr>
              </thead>
              <tbody id="request-anomaly-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Recent Executions</h2>
          <div class="panel-note">Latest controller-level execution attempts, including retries and protection starts</div>
          <div class="toolbar">
            <label for="execution-status-filter">Execution</label>
            <select id="execution-status-filter">
              <option value="all">All attempts</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="blocked">Blocked</option>
              <option value="abandoned">Abandoned</option>
              <option value="running">Running</option>
              <option value="protection">Protection starts</option>
            </select>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Execution ID</th>
                  <th>Request ID</th>
                  <th>Run ID</th>
                  <th>Status</th>
                  <th>Attempt</th>
                  <th>Recovered</th>
                  <th>Failures Before</th>
                  <th>Protection</th>
                  <th>Cooldown Until</th>
                  <th>Retry</th>
                  <th>Failure Class</th>
                </tr>
              </thead>
              <tbody id="execution-table"></tbody>
            </table>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <h2 class="panel-title">Execution Request Detail</h2>
          <div class="panel-note">Inspect one request-level retry chain before drilling into a specific attempt</div>
          <div id="request-detail-meta" class="muted"></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Execution ID</th>
                  <th>Status</th>
                  <th>Attempt</th>
                  <th>Run ID</th>
                  <th>Protection</th>
                  <th>Cooldown Until</th>
                  <th>Retry</th>
                  <th>Failure Class</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="request-detail-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Order Lifecycles</h2>
          <div class="panel-note">Grouped order status paths keyed by order ID</div>
          <div class="toolbar">
            <label for="run-filter">Run</label>
            <select id="run-filter"></select>
            <label for="lifecycle-filter">Filter</label>
            <select id="lifecycle-filter">
              <option value="all">All</option>
              <option value="filled">Filled</option>
              <option value="cancelled">Cancelled</option>
              <option value="open">Open</option>
              <option value="repriced">Repriced</option>
            </select>
            <label for="side-filter">Side</label>
            <select id="side-filter">
              <option value="all">All sides</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
            </select>
            <label for="broker-filter">Broker</label>
            <select id="broker-filter">
              <option value="all">All broker states</option>
              <option value="pending_new">pending_new</option>
              <option value="working">working</option>
              <option value="replaced">replaced</option>
              <option value="partially_filled">partially_filled</option>
              <option value="filled">filled</option>
              <option value="cancelled">cancelled</option>
              <option value="rejected">rejected</option>
              <option value="local_skipped">local_skipped</option>
            </select>
            <label for="focus-filter">Focus</label>
            <select id="focus-filter">
              <option value="all">All orders</option>
              <option value="anomalies">Anomalies</option>
            </select>
            <div class="toolbar-actions">
              <button id="clear-context" class="ghost-button" type="button">Clear Context</button>
              <button id="copy-link" class="ghost-button" type="button">Copy Link</button>
              <a id="deep-link" class="deep-link" href="#">Deep Link</a>
            </div>
          </div>
          <div id="selected-context" class="muted context-line"></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Run ID</th>
                  <th>Side</th>
                  <th>Final</th>
                  <th>Broker</th>
                  <th>Req Qty</th>
                  <th>Filled</th>
                  <th>Path</th>
                </tr>
              </thead>
              <tbody id="lifecycle-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Lifecycle Detail</h2>
          <div class="panel-note">Click an order lifecycle to inspect the underlying event stream</div>
          <div id="lifecycle-detail-meta" class="muted"></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Broker</th>
                  <th>Detail</th>
                  <th>Req Qty</th>
                  <th>Filled</th>
                  <th>Remaining</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="lifecycle-detail-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Execution Detail</h2>
          <div class="panel-note">Click an execution attempt to inspect retry count, protection mode and linked run context</div>
          <div id="execution-detail-meta" class="muted"></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Execution ID</th>
                  <th>Request ID</th>
                  <th>Symbol</th>
                  <th>Status</th>
                  <th>Attempt</th>
                  <th>Recovered</th>
                  <th>Failures Before</th>
                  <th>Protection</th>
                  <th>Cooldown Until</th>
                  <th>Retry</th>
                  <th>Failure Class</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="execution-detail-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Recent Orders</h2>
          <div class="panel-note">Latest persisted order events</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Status</th>
                  <th>Broker</th>
                  <th>Detail</th>
                  <th>Req Qty</th>
                  <th>Filled</th>
                  <th>Remaining</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="orders-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <h2 class="panel-title">Recent Audit Events</h2>
          <div class="panel-note">Latest strategy and risk events</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>Signal</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody id="audit-table"></tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  </main>
  <script>
    const payload = {data_json};

    // 历史页的设计目标不是花哨，而是让复盘和排错尽量少跳转。
    function fmt(value) {{
      return typeof value === "number" ? value.toLocaleString(undefined, {{ maximumFractionDigits: 4 }}) : value;
    }}
    function formatFailureMix(request) {{
      const failures = request.failure_classes || [];
      if (!failures.length) return "";
      return failures.map(item => `${{item.failure_class}}(${{item.count}})`).join(", ");
    }}
    function lifecycleCountForRun(runId) {{
      return payload.order_lifecycles.filter(order => order.run_id === runId).length;
    }}
    function isAnomaly(order) {{
      if (!order) return false;
      if (order.final_status !== "filled") return true;
      return order.status_path.includes("replaced");
    }}
    function availableRunIds() {{
      return payload.runs_table.map(run => run.run_id);
    }}
    function hydrateRunFilter() {{
      // run 下拉框来自真实运行记录，而不是写死在页面里。
      const select = document.getElementById("run-filter");
      const options = ['<option value="all">All runs</option>'].concat(
        payload.runs_table.map(run => `<option value="${{run.run_id}}">${{run.run_id}}</option>`)
      );
      select.innerHTML = options.join("");
    }}
    function findLifecycle(orderId) {{
      return payload.order_lifecycles.find(order => order.order_id === orderId);
    }}
    function readHashState() {{
      // 所有筛选状态都从 URL hash 中恢复，这样页面可以被分享和复现。
      const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      const runId = params.get("run") || "all";
      const lifecycleFilter = params.get("filter") || "all";
      const side = params.get("side") || "all";
      const broker = params.get("broker") || "all";
      const focus = params.get("focus") || "all";
      const executionStatus = params.get("execution_status") || "all";
      const requestId = params.get("request") || "";
      const executionId = params.get("execution") || "";
      const orderId = params.get("order") || "";
      return {{
        runId: availableRunIds().includes(runId) ? runId : "all",
        lifecycleFilter: ["all", "filled", "cancelled", "open", "repriced"].includes(lifecycleFilter) ? lifecycleFilter : "all",
        side: ["all", "BUY", "SELL"].includes(side) ? side : "all",
        broker: ["all", "pending_new", "working", "replaced", "partially_filled", "filled", "cancelled", "rejected", "local_skipped"].includes(broker) ? broker : "all",
        focus: ["all", "anomalies"].includes(focus) ? focus : "all",
        executionStatus: ["all", "completed", "failed", "blocked", "abandoned", "running", "protection"].includes(executionStatus) ? executionStatus : "all",
        requestId,
        executionId,
        orderId,
      }};
    }}
    const state = readHashState();
    function writeHashState() {{
      // 每次筛选变化后都同步回地址栏，保证“当前所见就是当前链接”。
      const params = new URLSearchParams();
      if (state.runId !== "all") params.set("run", state.runId);
      if (state.lifecycleFilter !== "all") params.set("filter", state.lifecycleFilter);
      if (state.side !== "all") params.set("side", state.side);
      if (state.broker !== "all") params.set("broker", state.broker);
      if (state.focus !== "all") params.set("focus", state.focus);
      if (state.executionStatus !== "all") params.set("execution_status", state.executionStatus);
      if (state.requestId) params.set("request", state.requestId);
      if (state.executionId) params.set("execution", state.executionId);
      if (state.orderId) params.set("order", state.orderId);
      const hash = params.toString() ? `#${{params.toString()}}` : "";
      const target = `${{window.location.pathname}}${{window.location.search}}${{hash}}`;
      if (window.location.hash !== hash) {{
        window.history.replaceState(null, "", target);
      }}
      document.getElementById("deep-link").href = window.location.href;
    }}
    function syncControlsToState() {{
      document.getElementById("run-filter").value = state.runId;
      document.getElementById("lifecycle-filter").value = state.lifecycleFilter;
      document.getElementById("side-filter").value = state.side;
      document.getElementById("broker-filter").value = state.broker;
      document.getElementById("focus-filter").value = state.focus;
      document.getElementById("execution-status-filter").value = state.executionStatus;
    }}
    function filteredLifecycleCount() {{
      return filteredLifecycles().filter(order => state.focus === "all" || isAnomaly(order)).length;
    }}
    function renderContext() {{
      // 这一行是给人看的“当前上下文摘要”，方便确认自己到底筛到了哪里。
      const bits = [];
      bits.push(state.runId === "all" ? "Run: all" : `Run: ${{state.runId}}`);
      bits.push(`Status: ${{state.lifecycleFilter}}`);
      bits.push(`Side: ${{state.side === "all" ? "all" : state.side}}`);
      bits.push(`Broker: ${{state.broker}}`);
      bits.push(`Focus: ${{state.focus}}`);
      bits.push(`Execution Filter: ${{state.executionStatus}}`);
      bits.push(state.requestId ? `Request: ${{state.requestId}}` : "Request: none selected");
      bits.push(`Matches: ${{filteredLifecycleCount()}}`);
      bits.push(state.executionId ? `Execution: ${{state.executionId}}` : "Execution: none selected");
      bits.push(state.orderId ? `Order: ${{state.orderId}}` : "Order: none selected");
      document.getElementById("selected-context").textContent = bits.join(" | ");
    }}
    function renderCards() {{
      // 顶部卡片先给总览，再决定是否深入看表格明细。
      const summary = payload.history_summary;
      const cards = [
        {{ label: "Total Runs", value: summary.total_runs }},
        {{ label: "Request Chains", value: summary.total_execution_requests }},
        {{ label: "Retried Requests", value: summary.retried_execution_requests }},
        {{ label: "Anomalous Requests", value: summary.anomalous_execution_requests }},
        {{ label: "Critical Requests", value: summary.critical_execution_requests }},
        {{ label: "Cooldown Active", value: summary.cooldown_protected_requests }},
        {{ label: "Execution Attempts", value: summary.total_executions }},
        {{ label: "Retry Scheduled", value: summary.retry_scheduled_executions }},
        {{ label: "Execution Failed", value: summary.failed_executions }},
        {{ label: "Execution Blocked", value: summary.blocked_executions }},
        {{ label: "Protection Starts", value: summary.protection_mode_executions }},
        {{ label: "Recovered Starts", value: summary.recovered_execution_starts }},
        {{ label: "Top Failure Class", value: summary.top_request_failure_class || "-" }},
        {{ label: "Latest Symbol", value: summary.latest_symbol }},
        {{ label: "Latest Return %", value: summary.latest_return_pct }},
        {{ label: "Latest Sharpe", value: summary.latest_sharpe_ratio }},
        {{ label: "Order Lifecycles", value: summary.total_lifecycles }},
        {{ label: "Lifecycle Filled", value: summary.filled_lifecycles }},
        {{ label: "Lifecycle Cancelled", value: summary.cancelled_lifecycles }},
        {{ label: "Lifecycle Repriced", value: summary.repriced_lifecycles }},
      ];
      document.getElementById("summary-cards").innerHTML = cards.map(card => `
        <article class="card">
          <div class="card-label">${{card.label}}</div>
          <div class="card-value">${{fmt(card.value)}}</div>
        </article>
      `).join("");
    }}
    function renderRuns() {{
      // Recent Runs 表让我们先确定“要看哪一次运行”。
      document.getElementById("runs-table").innerHTML = payload.runs_table.map(run => `
        <tr class="${{state.runId === run.run_id ? "row-active" : ""}}">
          <td><button class="link-button" data-run-id="${{run.run_id}}">${{run.run_id}}</button></td>
          <td>${{run.symbol}}</td>
          <td>${{run.started_at}}</td>
          <td>${{fmt(lifecycleCountForRun(run.run_id))}}</td>
          <td>${{fmt(run.total_return_pct)}}</td>
          <td>${{fmt(run.sharpe_ratio)}}</td>
          <td>${{fmt(run.total_trades)}}</td>
        </tr>
      `).join("");
      document.querySelectorAll("[data-run-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.runId = node.getAttribute("data-run-id") || "all";
          renderAll();
        }});
      }});
    }}
    function findExecution(executionId) {{
      return payload.recent_executions.find(execution => execution.execution_id === executionId);
    }}
    function findRequest(requestId) {{
      return payload.execution_requests.find(request => request.request_id === requestId);
    }}
    function isExecutionAnomaly(execution) {{
      if (!execution) return false;
      return execution.status !== "completed" || execution.protection_mode || Number(execution.recovered_execution_count || 0) > 0;
    }}
    function renderRequestChains() {{
      // request 表负责回答“这几次重试是不是同一轮外部触发”。
      const rows = payload.execution_requests.filter(request => state.runId === "all" || request.run_id === state.runId);
      if (!rows.some(request => request.request_id === state.requestId)) {{
        state.requestId = rows[0]?.request_id ?? "";
      }}
      document.getElementById("request-table").innerHTML = rows.map(request => `
        <tr class="${{state.requestId === request.request_id ? "row-active" : ""}}">
          <td><button class="link-button" data-request-id="${{request.request_id}}">${{request.request_id}}</button></td>
          <td>${{request.run_id ? `<button class="link-button" data-request-run-id="${{request.run_id}}">${{request.run_id}}</button>` : ""}}</td>
          <td>${{request.health_label}}</td>
          <td>${{fmt(request.anomaly_score || 0)}}</td>
          <td>${{request.final_status}}</td>
          <td>${{fmt(request.attempt_count)}}</td>
          <td>${{request.retried ? "yes" : "no"}}</td>
          <td>${{request.protection_mode_seen ? "yes" : "no"}}</td>
          <td>${{request.protection_cooldown_until || ""}}</td>
          <td>${{formatFailureMix(request)}}</td>
          <td>${{request.decision_path || ""}}</td>
          <td>${{request.attempt_path}}</td>
        </tr>
      `).join("");
      document.querySelectorAll("#request-table [data-request-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.requestId = node.getAttribute("data-request-id") || "";
          renderAll();
        }});
      }});
      document.querySelectorAll("#request-table [data-request-run-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.runId = node.getAttribute("data-request-run-id") || "all";
          renderAll();
        }});
      }});
      renderRequestAnomalies(rows);
      renderRequestDetail();
    }}
    function renderRequestAnomalies(requestRows) {{
      // 这个面板把“最值得先看”的 request 先排到前面，减少人工在表里翻找的时间。
      const rows = (requestRows || [])
        .filter(request => Number(request.anomaly_score || 0) > 0)
        .sort((left, right) => Number(right.anomaly_score || 0) - Number(left.anomaly_score || 0));
      document.getElementById("request-anomaly-table").innerHTML = rows.length ? rows.map(request => `
        <tr class="${{state.requestId === request.request_id ? "row-active" : ""}}">
          <td><button class="link-button" data-request-anomaly-id="${{request.request_id}}">${{request.request_id}}</button></td>
          <td>${{request.health_label}}</td>
          <td>${{fmt(request.anomaly_score || 0)}}</td>
          <td>${{request.final_status}}</td>
          <td>${{fmt(request.retry_scheduled_count || 0)}}</td>
          <td>${{request.dominant_failure_class || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="6" class="muted">No anomalous request chains in the current view.</td></tr>';
      document.querySelectorAll("[data-request-anomaly-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.requestId = node.getAttribute("data-request-anomaly-id") || "";
          renderAll();
        }});
      }});
    }}
    function renderRequestDetail() {{
      // request detail 先看整条重试链，再决定点进哪一次具体 execution。
      const request = findRequest(state.requestId);
      const attempts = payload.execution_request_details[state.requestId] || [];
      if (!attempts.some(attempt => attempt.execution_id === state.executionId)) {{
        state.executionId = attempts[attempts.length - 1]?.execution_id ?? state.executionId;
      }}
      document.getElementById("request-detail-meta").textContent = request
        ? `Request ${{request.request_id}} | Health: ${{request.health_label}} | Anomaly Score: ${{request.anomaly_score || 0}} | Final: ${{request.final_status}} | Attempts: ${{request.attempt_count}} | Retried: ${{request.retried ? "yes" : "no"}} | Protected: ${{request.protection_mode_seen ? "yes" : "no"}} | Cooldown Until: ${{request.protection_cooldown_until || ""}} | Failure Mix: ${{formatFailureMix(request)}}`
        : "No request selected.";
      document.getElementById("request-detail-table").innerHTML = attempts.map(attempt => `
        <tr class="${{state.executionId === attempt.execution_id ? "row-active" : ""}}">
          <td>${{attempt.request_id}}</td>
          <td><button class="link-button" data-request-execution-id="${{attempt.execution_id}}">${{attempt.execution_id}}</button></td>
          <td>${{attempt.status}}</td>
          <td>${{fmt(attempt.attempt_number)}}</td>
          <td>${{attempt.run_id || ""}}</td>
          <td>${{attempt.protection_mode ? "on" : "off"}}</td>
          <td>${{attempt.protection_cooldown_until || ""}}</td>
          <td>${{attempt.retry_decision || ""}}</td>
          <td>${{attempt.failure_class || ""}}</td>
          <td>${{attempt.error_message || attempt.protection_reason || ""}}</td>
        </tr>
      `).join("");
      document.querySelectorAll("#request-detail-table [data-request-execution-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.executionId = node.getAttribute("data-request-execution-id") || "";
          renderAll();
        }});
      }});
    }}
    function renderExecutions() {{
      // 执行表回答的是“这次回测任务本身是否健康”，它和订单表不是同一层。
      const rows = payload.recent_executions.filter(execution => {{
        if (state.runId !== "all" && execution.run_id !== state.runId) return false;
        if (state.requestId && execution.request_id !== state.requestId) return false;
        if (state.executionStatus === "protection") return Boolean(execution.protection_mode);
        if (state.executionStatus !== "all" && execution.status !== state.executionStatus) return false;
        return true;
      }});
      if (!rows.some(execution => execution.execution_id === state.executionId)) {{
        state.executionId = rows[0]?.execution_id ?? "";
      }}
      document.getElementById("execution-table").innerHTML = rows.map(execution => `
        <tr class="${{[state.executionId === execution.execution_id ? "row-active" : "", isExecutionAnomaly(execution) ? "row-anomaly" : ""].filter(Boolean).join(" ")}}">
          <td><button class="link-button" data-execution-id="${{execution.execution_id}}">${{execution.execution_id}}</button></td>
          <td>${{execution.request_id || ""}}</td>
          <td>${{execution.run_id ? `<button class="link-button" data-execution-run-id="${{execution.run_id}}">${{execution.run_id}}</button>` : ""}}</td>
          <td>${{execution.status}}</td>
          <td>${{fmt(execution.attempt_number)}}</td>
          <td>${{fmt(execution.recovered_execution_count)}}</td>
          <td>${{fmt(execution.consecutive_failures_before_start)}}</td>
          <td>${{execution.protection_mode ? "on" : "off"}}</td>
          <td>${{execution.protection_cooldown_until || ""}}</td>
          <td>${{execution.retry_decision || ""}}</td>
          <td>${{execution.failure_class || ""}}</td>
        </tr>
      `).join("");
      document.querySelectorAll("#execution-table [data-execution-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.executionId = node.getAttribute("data-execution-id") || "";
          renderAll();
        }});
      }});
      document.querySelectorAll("#execution-table [data-execution-run-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.runId = node.getAttribute("data-execution-run-id") || "all";
          renderAll();
        }});
      }});
      renderExecutionDetail();
    }}
    function renderExecutionDetail() {{
      // 详情面板把一次执行尝试的“控制器级状态”摊开，便于判断是否要继续追订单层。
      const execution = findExecution(state.executionId);
      document.getElementById("execution-detail-meta").textContent = execution
        ? `Execution ${{execution.execution_id}} | Request: ${{execution.request_id || ""}} | Status: ${{execution.status}} | Attempt: ${{execution.attempt_number}} | Retry: ${{execution.retry_decision || ""}} | Failure Class: ${{execution.failure_class || ""}} | Recovered Starts: ${{execution.recovered_execution_count}} | Failures Before Start: ${{execution.consecutive_failures_before_start}} | Protection: ${{execution.protection_mode ? "on" : "off"}} | Cooldown Until: ${{execution.protection_cooldown_until || ""}}`
        : "No execution selected.";
      document.getElementById("execution-detail-table").innerHTML = execution ? `
        <tr>
          <td>${{execution.execution_id}}</td>
          <td>${{execution.request_id || ""}}</td>
          <td>${{execution.symbol}} / ${{execution.timeframe}}</td>
          <td>${{execution.status}}</td>
          <td>${{fmt(execution.attempt_number)}}</td>
          <td>${{fmt(execution.recovered_execution_count)}}</td>
          <td>${{fmt(execution.consecutive_failures_before_start)}}</td>
          <td>${{execution.protection_mode ? "on" : "off"}}</td>
          <td>${{execution.protection_cooldown_until || ""}}</td>
          <td>${{execution.retry_decision || ""}}</td>
          <td>${{execution.failure_class || ""}}</td>
          <td>${{execution.error_message || execution.protection_reason || ""}}</td>
        </tr>
      ` : "";
    }}
    function renderOrders() {{
      // 这里展示的是原始订单事件，适合看最近实际发生的执行动作。
      const rows = payload.recent_orders.filter(order => {{
        if (state.runId !== "all" && order.run_id !== state.runId) return false;
        if (state.side !== "all" && order.side !== state.side) return false;
        if (state.broker !== "all" && order.broker_status !== state.broker) return false;
        return true;
      }});
      document.getElementById("orders-table").innerHTML = rows.map(order => `
        <tr class="${{state.orderId === order.order_id ? "row-active" : ""}}">
          <td><button class="link-button" data-order-id="${{order.order_id}}">${{order.order_id}}</button></td>
          <td>${{order.timestamp}}</td>
          <td class="${{order.side === "BUY" ? "buy" : "sell"}}">${{order.side}}</td>
          <td>${{order.status}}</td>
          <td>${{order.broker_status || ""}}</td>
          <td>${{order.status_detail || ""}}</td>
          <td>${{fmt(order.quantity)}}</td>
          <td>${{fmt(order.filled_quantity ?? 0)}}</td>
          <td>${{fmt(order.remaining_quantity ?? 0)}}</td>
          <td>${{order.reason}}</td>
        </tr>
      `).join("");
      document.querySelectorAll("#orders-table [data-order-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          const orderId = node.getAttribute("data-order-id") || "";
          const lifecycle = findLifecycle(orderId);
          if (lifecycle) {{
            state.orderId = orderId;
            state.runId = lifecycle.run_id || state.runId;
            renderAll();
          }}
        }});
      }});
    }}
    function filteredLifecycles() {{
      // 先按 run / side 缩小范围，再按生命周期状态继续过滤。
      const scoped = payload.order_lifecycles.filter(order => {{
        if (state.runId !== "all" && order.run_id !== state.runId) return false;
        if (state.side !== "all" && order.side !== state.side) return false;
        if (state.broker !== "all" && order.latest_broker_status !== state.broker) return false;
        return true;
      }});
      if (state.lifecycleFilter === "all") return scoped;
      if (state.lifecycleFilter === "repriced") {{
        return scoped.filter(order => order.status_path.includes("replaced"));
      }}
      return scoped.filter(order => order.final_status === state.lifecycleFilter);
    }}
    function renderLifecycles() {{
      // 生命周期表更强调“一笔订单完整经历了什么”，而不是孤立事件。
      const rows = filteredLifecycles().filter(order => state.focus === "all" || isAnomaly(order));
      if (!rows.some(order => order.order_id === state.orderId)) {{
        state.orderId = rows[0]?.order_id ?? "";
      }}
      document.getElementById("lifecycle-table").innerHTML = rows.map(order => `
        <tr class="${{[state.orderId === order.order_id ? "row-active" : "", isAnomaly(order) ? "row-anomaly" : ""].filter(Boolean).join(" ")}}">
          <td><button class="link-button" data-order-id="${{order.order_id}}">${{order.order_id}}</button></td>
          <td><button class="link-button" data-run-id="${{order.run_id}}">${{order.run_id}}</button></td>
          <td class="${{order.side === "BUY" ? "buy" : "sell"}}">${{order.side}}</td>
          <td>${{order.final_status}}</td>
          <td>${{order.latest_broker_status || ""}}</td>
          <td>${{fmt(order.requested_quantity)}}</td>
          <td>${{fmt(order.filled_quantity)}}</td>
          <td>${{order.status_path}}</td>
        </tr>
      `).join("");
      document.querySelectorAll("#lifecycle-table [data-order-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.orderId = node.getAttribute("data-order-id") || "";
          renderAll();
        }});
      }});
      document.querySelectorAll("#lifecycle-table [data-run-id]").forEach(node => {{
        node.addEventListener("click", () => {{
          state.runId = node.getAttribute("data-run-id") || "all";
          renderAll();
        }});
      }});
      renderLifecycleDetail();
    }}
    function renderLifecycleDetail() {{
      // 明细表展示的是被选中订单的原始事件流，用来做最终排错。
      const events = payload.order_lifecycle_details[state.orderId] || [];
      const lifecycle = findLifecycle(state.orderId);
      document.getElementById("lifecycle-detail-meta").textContent = lifecycle
        ? `Order ${{lifecycle.order_id}} | Run: ${{lifecycle.run_id}} | Final: ${{lifecycle.final_status}} | Broker: ${{lifecycle.latest_broker_status || ""}} | Path: ${{lifecycle.status_path}}`
        : "No order selected.";
      document.getElementById("lifecycle-detail-table").innerHTML = events.map(event => `
        <tr>
          <td>${{event.order_id}}</td>
          <td>${{event.timestamp}}</td>
          <td>${{event.status}}</td>
          <td>${{event.broker_status || ""}}</td>
          <td>${{event.status_detail || ""}}</td>
          <td>${{fmt(event.quantity)}}</td>
          <td>${{fmt(event.filled_quantity ?? 0)}}</td>
          <td>${{fmt(event.remaining_quantity ?? 0)}}</td>
          <td>${{event.reason}}</td>
        </tr>
      `).join("");
    }}
    function renderAudit() {{
      // 审计日志和订单表联动 run 过滤，但不会跟 side/focus 强绑定，
      // 因为审计日志描述的是整个系统行为，而不是单一订单切片。
      const rows = payload.recent_audit_events.filter(event => state.runId === "all" || event.run_id === state.runId);
      document.getElementById("audit-table").innerHTML = rows.map(event => `
        <tr>
          <td>${{event.timestamp}}</td>
          <td>${{event.event}}</td>
          <td>${{event.signal}}</td>
          <td>${{event.reason}}</td>
        </tr>
      `).join("");
    }}
    async function copyCurrentLink() {{
      // 优先用浏览器剪贴板 API；如果环境不支持，就退化成 prompt。
      const button = document.getElementById("copy-link");
      const originalLabel = button.textContent;
      try {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          await navigator.clipboard.writeText(window.location.href);
        }} else {{
          window.prompt("Copy link:", window.location.href);
        }}
        button.textContent = "Copied";
      }} catch (error) {{
        window.prompt("Copy link:", window.location.href);
        button.textContent = "Link Ready";
      }}
      window.setTimeout(() => {{
        button.textContent = originalLabel;
      }}, 1400);
    }}
    function renderAll() {{
      // 所有页面更新都走同一个总入口，避免多个函数各自改一半状态。
      syncControlsToState();
      renderContext();
      renderRuns();
      renderRequestChains();
      renderExecutions();
      renderLifecycles();
      renderOrders();
      renderAudit();
      writeHashState();
    }}
    hydrateRunFilter();
    renderCards();
    renderAll();
    document.getElementById("run-filter").addEventListener("change", event => {{
      state.runId = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("lifecycle-filter").addEventListener("change", event => {{
      state.lifecycleFilter = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("side-filter").addEventListener("change", event => {{
      state.side = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("broker-filter").addEventListener("change", event => {{
      state.broker = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("focus-filter").addEventListener("change", event => {{
      state.focus = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("execution-status-filter").addEventListener("change", event => {{
      state.executionStatus = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("clear-context").addEventListener("click", () => {{
      state.runId = "all";
      state.lifecycleFilter = "all";
      state.side = "all";
      state.broker = "all";
      state.focus = "all";
      state.executionStatus = "all";
      state.requestId = "";
      state.executionId = "";
      state.orderId = "";
      renderAll();
    }});
    document.getElementById("copy-link").addEventListener("click", copyCurrentLink);
    window.addEventListener("hashchange", () => {{
      const next = readHashState();
      state.runId = next.runId;
      state.lifecycleFilter = next.lifecycleFilter;
      state.side = next.side;
      state.broker = next.broker;
      state.focus = next.focus;
      state.executionStatus = next.executionStatus;
      state.requestId = next.requestId;
      state.executionId = next.executionId;
      state.orderId = next.orderId;
      renderAll();
    }});
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)
