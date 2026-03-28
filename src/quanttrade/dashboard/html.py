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
      --bg: #eef3f7;
      --bg-alt: #e3ebf1;
      --panel: rgba(255, 255, 255, 0.88);
      --panel-strong: rgba(255, 255, 255, 0.96);
      --panel-alt: #f4f8fb;
      --text: #11243a;
      --muted: #60758c;
      --accent: #1a6fd8;
      --accent-soft: rgba(26, 111, 216, 0.10);
      --accent-2: #177a52;
      --warn: #b66a16;
      --danger: #b73a3a;
      --critical: #8b1e2d;
      --line: rgba(17, 36, 58, 0.10);
      --line-strong: rgba(17, 36, 58, 0.16);
      --shadow: 0 24px 60px rgba(19, 42, 67, 0.10);
      --shadow-soft: 0 14px 32px rgba(19, 42, 67, 0.06);
      --mono: "IBM Plex Mono", "SFMono-Regular", monospace;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(26, 111, 216, 0.10), transparent 26%),
        radial-gradient(circle at right 10%, rgba(23, 122, 82, 0.08), transparent 24%),
        linear-gradient(180deg, #f8fbfd 0%, var(--bg) 58%, var(--bg-alt) 100%);
      color: var(--text);
    }}
    .shell {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 28px 24px 72px;
    }}
    .hero {{
      margin-bottom: 26px;
    }}
    .hero-shell {{
      display: grid;
      grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.9fr);
      gap: 20px;
      padding: 28px;
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.96), rgba(244,248,251,0.96)),
        var(--panel-strong);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .hero-copy {{
      min-width: 0;
    }}
    .eyebrow {{
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 12px;
      margin-bottom: 12px;
      font-weight: 700;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(34px, 5vw, 58px);
      line-height: 0.92;
      letter-spacing: -0.04em;
    }}
    .subcopy {{
      color: var(--muted);
      max-width: 820px;
      line-height: 1.68;
      font-size: 15px;
    }}
    .hero-status {{
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .hero-card {{
      padding: 18px 18px 16px;
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(26,111,216,0.08), rgba(26,111,216,0.03));
      border: 1px solid rgba(26,111,216,0.12);
      box-shadow: var(--shadow-soft);
    }}
    .hero-card-title {{
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 10px;
    }}
    .hero-card-value {{
      font-size: 30px;
      font-weight: 750;
      letter-spacing: -0.04em;
      margin-bottom: 8px;
    }}
    .hero-card-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .jump-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .jump-link {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--line);
      color: var(--text);
      text-decoration: none;
      font-size: 13px;
      box-shadow: var(--shadow-soft);
    }}
    .app-frame {{
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .sidebar {{
      position: sticky;
      top: 18px;
      display: grid;
      gap: 14px;
      padding: 18px;
      border-radius: 28px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.95), rgba(244,248,251,0.95)),
        var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .sidebar-brand {{
      padding: 14px 14px 16px;
      border-radius: 20px;
      background: linear-gradient(135deg, rgba(26,111,216,0.12), rgba(23,122,82,0.08));
      border: 1px solid rgba(26,111,216,0.12);
    }}
    .sidebar-brand-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .sidebar-brand-title {{
      font-size: 24px;
      font-weight: 760;
      letter-spacing: -0.03em;
      margin-bottom: 8px;
    }}
    .sidebar-brand-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .sidebar-section-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      font-weight: 700;
      padding: 0 4px;
    }}
    .sidebar-nav {{
      display: grid;
      gap: 8px;
    }}
    .sidebar-button {{
      display: flex;
      align-items: flex-start;
      gap: 10px;
      width: 100%;
      text-align: left;
      padding: 12px 14px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      cursor: pointer;
      box-shadow: var(--shadow-soft);
    }}
    .sidebar-button.is-active {{
      border-color: rgba(26,111,216,0.22);
      background: linear-gradient(180deg, rgba(26,111,216,0.10), rgba(255,255,255,0.96));
    }}
    .sidebar-button-kicker {{
      min-width: 28px;
      height: 28px;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 800;
      color: var(--accent);
      background: rgba(26,111,216,0.10);
      border: 1px solid rgba(26,111,216,0.12);
      font-family: var(--mono);
    }}
    .sidebar-button-copy {{
      min-width: 0;
    }}
    .sidebar-button-title {{
      font-size: 14px;
      font-weight: 720;
      margin-bottom: 4px;
    }}
    .sidebar-button-note {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    .sidebar-tip {{
      padding: 14px;
      border-radius: 18px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
    }}
    .sidebar-tip-title {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .sidebar-tip-copy {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .workspace-shell {{
      min-width: 0;
    }}
    .workspace-bar {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 20px;
      margin-bottom: 16px;
      padding: 18px 20px;
      border-radius: 24px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.96), rgba(244,248,251,0.96)),
        var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow-soft);
    }}
    .workspace-label {{
      color: var(--accent);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .workspace-title {{
      margin: 0 0 6px;
      font-size: 26px;
      line-height: 1;
      letter-spacing: -0.03em;
    }}
    .workspace-note {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
      max-width: 760px;
    }}
    .workspace-pills {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
    }}
    .workspace-pill {{
      padding: 10px 12px;
      border-radius: 999px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .workspace-pill strong {{
      color: var(--text);
      margin-right: 6px;
    }}
    .workspace-panel[data-hidden="true"] {{
      display: none !important;
    }}
    .summary-stack {{
      display: grid;
      gap: 18px;
      margin-bottom: 24px;
    }}
    .summary-hero {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 14px;
    }}
    .summary-groups {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .card, .panel, .summary-group {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow-soft);
    }}
    .card {{
      padding: 18px 18px 16px;
      position: relative;
      overflow: hidden;
      min-height: 132px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.92), rgba(244,248,251,0.92)),
        var(--panel);
    }}
    .card-label {{
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .card-value {{
      font-size: 34px;
      font-weight: 760;
      letter-spacing: -0.05em;
      margin-bottom: 8px;
    }}
    .card-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .tone-ok {{
      border-color: rgba(23, 122, 82, 0.18);
      background: linear-gradient(180deg, rgba(23,122,82,0.08), rgba(255,255,255,0.92));
    }}
    .tone-warn {{
      border-color: rgba(182, 106, 22, 0.18);
      background: linear-gradient(180deg, rgba(255,191,105,0.12), rgba(255,255,255,0.92));
    }}
    .tone-critical {{
      border-color: rgba(139, 30, 45, 0.18);
      background: linear-gradient(180deg, rgba(183,58,58,0.10), rgba(255,255,255,0.92));
    }}
    .summary-group {{
      padding: 18px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.94), rgba(244,248,251,0.94)),
        var(--panel);
    }}
    .summary-group-head {{
      margin-bottom: 14px;
    }}
    .summary-group-title {{
      margin: 0 0 4px;
      font-size: 16px;
      font-weight: 730;
      letter-spacing: -0.02em;
    }}
    .summary-group-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .summary-group-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .summary-mini {{
      padding: 12px 14px;
      border-radius: 16px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
    }}
    .summary-mini-label {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
      font-weight: 700;
    }}
    .summary-mini-value {{
      font-size: 20px;
      font-weight: 720;
      letter-spacing: -0.03em;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.28fr) minmax(360px, 0.92fr);
      gap: 18px;
    }}
    .stack {{
      display: grid;
      gap: 18px;
    }}
    .panel {{
      padding: 20px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.95), rgba(244,248,251,0.95)),
        var(--panel);
      overflow: hidden;
    }}
    .panel-title {{
      margin: 0 0 4px;
      font-size: 19px;
      font-weight: 730;
      letter-spacing: -0.02em;
    }}
    .panel-note {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 16px;
      line-height: 1.55;
    }}
    .toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 16px;
      padding: 12px;
      border-radius: 18px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
    }}
    .toolbar label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .toolbar select,
    .toolbar input,
    .ghost-button {{
      background: var(--panel-alt);
      color: var(--text);
      border: 1px solid var(--line-strong);
      border-radius: 12px;
      padding: 10px 12px;
      min-height: 42px;
    }}
    .toolbar-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
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
      font-weight: 650;
    }}
    .ghost-button {{
      border-radius: 999px;
      cursor: pointer;
      background: #fff;
      box-shadow: var(--shadow-soft);
    }}
    .deep-link {{
      color: var(--accent);
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
    }}
    .muted {{
      color: var(--muted);
      font-size: 13px;
    }}
    .context-line {{
      margin-bottom: 14px;
      padding: 12px 14px;
      border-radius: 16px;
      background: var(--panel-alt);
      border: 1px dashed var(--line-strong);
    }}
    .row-active {{
      background: rgba(26, 111, 216, 0.08);
    }}
    .row-anomaly {{
      box-shadow: inset 4px 0 0 rgba(182, 106, 22, 0.92);
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.65);
    }}
    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 12px;
      border-bottom: 1px solid var(--line);
      white-space: nowrap;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 11px;
      position: sticky;
      top: 0;
      z-index: 1;
      background: #f7fafc;
    }}
    tbody tr:nth-child(2n) {{
      background: rgba(244, 248, 251, 0.62);
    }}
    tbody tr:hover {{
      background: rgba(26, 111, 216, 0.06);
    }}
    td:first-child, th:first-child {{
      padding-left: 14px;
    }}
    td:last-child, th:last-child {{
      padding-right: 14px;
    }}
    td:first-child {{
      font-family: var(--mono);
      font-size: 12px;
    }}
    .buy {{ color: var(--accent-2); }}
    .sell {{ color: var(--warn); }}
    @media (max-width: 980px) {{
      .app-frame {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        position: static;
      }}
      .workspace-bar {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .workspace-pills {{
        justify-content: flex-start;
      }}
      .hero-shell {{
        grid-template-columns: 1fr;
      }}
      .summary-hero {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .summary-groups {{
        grid-template-columns: 1fr;
      }}
      .summary-group-grid {{
        grid-template-columns: 1fr 1fr;
      }}
      .layout {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 700px) {{
      .shell {{
        padding: 18px 14px 42px;
      }}
      .sidebar,
      .workspace-bar,
      .hero-shell,
      .panel,
      .summary-group {{
        padding: 16px;
      }}
      .summary-hero {{
        grid-template-columns: 1fr;
      }}
      .summary-group-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-shell">
        <div class="hero-copy">
          <div class="eyebrow">QuantTrade History</div>
          <h1>Run History Dashboard</h1>
          <div class="subcopy">
            A static operations workspace generated from persisted runs, requests, runner cycles, broker syncs,
            and notifications. It is designed to feel like a lightweight control room instead of a raw export table.
          </div>
        </div>
        <div class="hero-status">
          <div class="hero-card">
            <div class="hero-card-title">Workspace Mode</div>
            <div class="hero-card-value">Static Ops Console</div>
            <div class="hero-card-note">Use the grouped scorecards below to scan runtime health first, then drop into detailed panels only where something looks off.</div>
          </div>
          <div class="hero-card">
            <div class="hero-card-title">Review Pattern</div>
            <div class="hero-card-note">Start from runtime health, then check runner heartbeat, broker drift, and finally request or order detail. This keeps the page readable even as the dataset grows.</div>
          </div>
        </div>
      </div>
      <nav class="jump-nav">
        <a class="jump-link" href="#runs-panel">Runs</a>
        <a class="jump-link" href="#runtime-panel">Runtime</a>
        <a class="jump-link" href="#runner-panel">Runners</a>
        <a class="jump-link" href="#broker-panel">Broker</a>
        <a class="jump-link" href="#alerts-panel">Alerts</a>
      </nav>
    </section>

    <section class="app-frame">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-brand-label">QuantTrade Workspace</div>
          <div class="sidebar-brand-title">Project Console</div>
          <div class="sidebar-brand-note">A simplified QuantConnect-style shell with a stable left navigation, an active workspace bar, and focused operational surfaces instead of one endless report.</div>
        </div>
        <div class="sidebar-section-label">Workspaces</div>
        <nav class="sidebar-nav" id="workspace-nav">
          <button class="sidebar-button" type="button" data-workspace-target="overview">
            <span class="sidebar-button-kicker">01</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Overview</span><span class="sidebar-button-note">Scan health, queue pressure, and immediate system posture.</span></span>
          </button>
          <button class="sidebar-button" type="button" data-workspace-target="research">
            <span class="sidebar-button-kicker">02</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Research</span><span class="sidebar-button-note">Frame the next experiment using recent results and current system context.</span></span>
          </button>
          <button class="sidebar-button" type="button" data-workspace-target="backtest">
            <span class="sidebar-button-kicker">03</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Backtest</span><span class="sidebar-button-note">Review runs, request chains, executions, orders, and audit traces.</span></span>
          </button>
          <button class="sidebar-button" type="button" data-workspace-target="live">
            <span class="sidebar-button-kicker">04</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Live</span><span class="sidebar-button-note">Track runner heartbeat, maintenance cadence, and controller operations.</span></span>
          </button>
          <button class="sidebar-button" type="button" data-workspace-target="broker">
            <span class="sidebar-button-kicker">05</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Broker</span><span class="sidebar-button-note">Inspect sync freshness, external drift, and broker-side state quality.</span></span>
          </button>
          <button class="sidebar-button" type="button" data-workspace-target="alerts">
            <span class="sidebar-button-kicker">06</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Alerts</span><span class="sidebar-button-note">Work through inbox, owners, SLA pressure, and delivery outcomes.</span></span>
          </button>
          <button class="sidebar-button" type="button" data-workspace-target="settings">
            <span class="sidebar-button-kicker">07</span>
            <span class="sidebar-button-copy"><span class="sidebar-button-title">Settings</span><span class="sidebar-button-note">See how this static console maps to the full product workflow.</span></span>
          </button>
        </nav>
        <div class="sidebar-tip">
          <div class="sidebar-tip-title">Operator Flow</div>
          <div class="sidebar-tip-copy">Start from Overview. If risk signals are quiet, move into Backtest or Research. If something is red, go straight to Live, Broker, or Alerts to investigate by function instead of by raw table order.</div>
        </div>
      </aside>

      <div class="workspace-shell">
        <header class="workspace-bar">
          <div>
            <div class="workspace-label">Active Workspace</div>
            <h2 id="workspace-title" class="workspace-title">Overview</h2>
            <div id="workspace-note" class="workspace-note"></div>
          </div>
          <div id="workspace-pills" class="workspace-pills"></div>
        </header>

        <section id="summary-cards" class="summary-stack workspace-panel" data-workspaces="overview"></section>

        <section class="layout">
      <div class="stack">
        <section id="runs-panel" class="panel workspace-panel" data-workspaces="overview backtest">
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

        <section id="runtime-panel" class="panel workspace-panel" data-workspaces="backtest">
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

        <section id="runner-panel" class="panel workspace-panel" data-workspaces="overview backtest">
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

        <section id="broker-panel" class="panel workspace-panel" data-workspaces="backtest">
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

        <section id="alerts-panel" class="panel workspace-panel" data-workspaces="live overview">
          <h2 class="panel-title">Recent Live Cycles</h2>
          <div class="panel-note">Foreground polling cycles that decide whether the controller should run or skip</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Cycle ID</th>
                  <th>Runner</th>
                  <th>Status</th>
                  <th>Latest Bar</th>
                  <th>Bars</th>
                  <th>Request ID</th>
                  <th>Execution ID</th>
                  <th>Run ID</th>
                  <th>Skip Reason</th>
                  <th>Protection</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody id="live-cycle-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="live overview">
          <h2 class="panel-title">Live Runners</h2>
          <div class="panel-note">Aggregated runner health grouped by runner and market</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Runner</th>
                  <th>Market</th>
                  <th>Latest</th>
                  <th>Cycles</th>
                  <th>Completed</th>
                  <th>Skipped</th>
                  <th>Blocked</th>
                  <th>Failed</th>
                  <th>Idle Streak</th>
                  <th>Cycle Age</th>
                  <th>Stall Threshold</th>
                  <th>Stalled</th>
                  <th>Protection Hits</th>
                  <th>Last Success</th>
                  <th>Latest Bar</th>
                </tr>
              </thead>
              <tbody id="live-runner-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="broker live">
          <h2 class="panel-title">Recent Broker Syncs</h2>
          <div class="panel-note">Read-only broker snapshots normalized into the local controller history</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Sync ID</th>
                  <th>Provider</th>
                  <th>Synced At</th>
                  <th>Status</th>
                  <th>Account</th>
                  <th>Broker Equity</th>
                  <th>Cash</th>
                  <th>Positions</th>
                  <th>Orders</th>
                  <th>Runner</th>
                  <th>Cycle</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody id="broker-sync-table"></tbody>
            </table>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="panel workspace-panel" data-workspaces="overview backtest">
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

        <section class="panel workspace-panel" data-workspaces="backtest">
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
            <label for="notification-status-filter">Notify</label>
            <select id="notification-status-filter">
              <option value="all">All alerts</option>
              <option value="queued">queued</option>
              <option value="dispatched">dispatched</option>
              <option value="delivery_failed_retryable">delivery_failed_retryable</option>
              <option value="delivery_failed_final">delivery_failed_final</option>
              <option value="filtered">filtered</option>
              <option value="suppressed">suppressed</option>
            </select>
            <label for="notification-owner-filter">Owner</label>
            <select id="notification-owner-filter">
              <option value="all">All owners</option>
              <option value="assigned">Assigned</option>
              <option value="unassigned">Unassigned</option>
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

        <section class="panel workspace-panel" data-workspaces="backtest">
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

        <section class="panel workspace-panel" data-workspaces="backtest">
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

        <section class="panel workspace-panel" data-workspaces="backtest">
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

        <section class="panel workspace-panel" data-workspaces="alerts overview">
          <h2 class="panel-title">Notification Summary</h2>
          <div class="panel-note">Grouped alert categories for faster triage</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Events</th>
                  <th>Suppressed</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody id="notification-summary-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="live">
          <h2 class="panel-title">Recent Maintenance Cycles</h2>
          <div class="panel-note">Controller maintenance runs that reconcile, monitor, escalate and deliver operational work</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Cycle ID</th>
                  <th>Runner</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Reconcile</th>
                  <th>Broker Sync</th>
                  <th>Recovered Exec</th>
                  <th>Issues</th>
                  <th>Emitted</th>
                  <th>Escalated</th>
                  <th>Delivered</th>
                  <th>Pending</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody id="maintenance-cycle-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="live">
          <h2 class="panel-title">Maintenance Runners</h2>
          <div class="panel-note">Aggregated health view for maintenance polling loops and their latest cycle heartbeat</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Runner</th>
                  <th>Latest</th>
                  <th>Cycles</th>
                  <th>Failed</th>
                  <th>Cycle Age</th>
                  <th>Stall Threshold</th>
                  <th>Stalled</th>
                  <th>Last Success</th>
                  <th>Delivered Total</th>
                  <th>Latest Pending</th>
                </tr>
              </thead>
              <tbody id="maintenance-runner-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="broker overview">
          <h2 class="panel-title">Broker Health</h2>
          <div class="panel-note">Freshness and latest status of the most recent broker snapshot</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Latest Sync</th>
                  <th>Snapshot Age</th>
                  <th>Age Threshold</th>
                  <th>Stale</th>
                  <th>Failed Syncs</th>
                  <th>Runner</th>
                  <th>Cycle</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody id="broker-health-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="broker overview">
          <h2 class="panel-title">Broker Reconcile</h2>
          <div class="panel-note">Lightweight drift preview between the latest local run snapshot and the latest broker snapshot</div>
          <div id="broker-reconcile-meta" class="muted"></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Local</th>
                  <th>Broker</th>
                  <th>Delta</th>
                  <th>Threshold</th>
                  <th>Breached</th>
                </tr>
              </thead>
              <tbody id="broker-reconcile-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="alerts">
          <h2 class="panel-title">Notification Owners</h2>
          <div class="panel-note">Who currently owns the alert queue and how much is still open</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Owner</th>
                  <th>Events</th>
                  <th>Active</th>
                  <th>Resolved</th>
                  <th>Reopened</th>
                  <th>Unacked</th>
                  <th>Escalated</th>
                  <th>Open High</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody id="notification-owner-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="alerts">
          <h2 class="panel-title">Notification SLA</h2>
          <div class="panel-note">Assigned alerts that have stayed unacknowledged beyond the configured SLA window</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Owner</th>
                  <th>Event ID</th>
                  <th>Severity</th>
                  <th>Category</th>
                  <th>Assigned At</th>
                  <th>Age Sec</th>
                  <th>SLA Sec</th>
                  <th>SLA Source</th>
                  <th>Breach Sec</th>
                </tr>
              </thead>
              <tbody id="notification-sla-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="alerts overview">
          <h2 class="panel-title">Notification Inbox</h2>
          <div class="panel-note">Active alerts that still need operator attention</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Owner</th>
                  <th>Event ID</th>
                  <th>Severity</th>
                  <th>Category</th>
                  <th>Title</th>
                  <th>Active Since</th>
                  <th>Age Sec</th>
                  <th>Ack State</th>
                  <th>Escalated</th>
                  <th>Reopened</th>
                  <th>Reopen Count</th>
                  <th>Next Try</th>
                </tr>
              </thead>
              <tbody id="notification-inbox-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="overview live">
          <h2 class="panel-title">Controller Health</h2>
          <div class="panel-note">High-priority controller issues and pending self-heal candidates</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Code</th>
                  <th>Count</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody id="controller-health-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="alerts">
          <h2 class="panel-title">Recent Notifications</h2>
          <div class="panel-note">Latest controller alerts and local delivery outcomes</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Category</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Suppressed</th>
                  <th>Next Try</th>
                  <th>Silenced Until</th>
                  <th>Owner</th>
                  <th>Assigned At</th>
                  <th>Resolved At</th>
                  <th>Reopened At</th>
                  <th>Reopen Count</th>
                  <th>Acked At</th>
                  <th>Escalated At</th>
                  <th>Provider</th>
                  <th>Assign Note</th>
                  <th>Resolved Note</th>
                  <th>Reopen Note</th>
                  <th>Ack Note</th>
                  <th>Escalation</th>
                  <th>Last Error</th>
                  <th>Execution</th>
                </tr>
              </thead>
              <tbody id="notifications-table"></tbody>
            </table>
          </div>
        </section>

        <section class="panel workspace-panel" data-workspaces="backtest">
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
        <section class="panel workspace-panel" data-workspaces="research settings">
          <h2 class="panel-title">Workspace Guide</h2>
          <div class="panel-note">A bridge panel so the current static export already follows the larger product workflow you asked for.</div>
          <div class="context-line">Research uses the latest run snapshot, anomaly ranking, broker drift, and health summaries to decide what to test next.</div>
          <div class="context-line">Settings is reserved for the future project configuration flow: strategy parameters, runner behavior, broker connections, and alert routing. In this static console it stays visible as a structural placeholder, so the product frame already matches the intended habit loop.</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Workspace</th>
                  <th>Current Static Surface</th>
                  <th>Future Product Intent</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Overview</td>
                  <td>Scorecards, controller health, notification inbox, recent runs</td>
                  <td>Project landing page and operational snapshot</td>
                </tr>
                <tr>
                  <td>Research</td>
                  <td>Guide and summary-driven decision framing</td>
                  <td>Notebook-style exploration, experiment notes, factor checks</td>
                </tr>
                <tr>
                  <td>Backtest</td>
                  <td>Runs, requests, executions, lifecycles, audit</td>
                  <td>Project-centered backtest analysis and parameter review</td>
                </tr>
                <tr>
                  <td>Live</td>
                  <td>Live cycles, live runners, maintenance cycles</td>
                  <td>Runner control surface and operating heartbeat board</td>
                </tr>
                <tr>
                  <td>Broker</td>
                  <td>Broker syncs, health, reconcile drift</td>
                  <td>Account sync, holdings, order sync, and reconciliation</td>
                </tr>
                <tr>
                  <td>Alerts</td>
                  <td>Inbox, owners, SLA, recent notifications</td>
                  <td>Daily operator queue and resolution workflow</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
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
    const WORKSPACE_META = {{
      overview: {{
        title: "Overview",
        note: "Start here. This workspace concentrates the main system posture before you switch into a more specialized flow.",
        pills: [
          {{ label: "Controller Issues", value: payload.history_summary.controller_health_issues }},
          {{ label: "Critical Alerts", value: payload.history_summary.critical_notifications }},
          {{ label: "Broker Drift", value: payload.history_summary.broker_reconcile_mismatches }},
        ],
      }},
      research: {{
        title: "Research",
        note: "A simplified placeholder for the future research environment. It already keeps the larger product layout aligned with QuantConnect-style habits.",
        pills: [
          {{ label: "Latest Symbol", value: payload.history_summary.latest_symbol || "-" }},
          {{ label: "Latest Return %", value: payload.history_summary.latest_return_pct }},
          {{ label: "Latest Sharpe", value: payload.history_summary.latest_sharpe_ratio }},
        ],
      }},
      backtest: {{
        title: "Backtest",
        note: "Use this view to review the full offline chain: runs, requests, executions, orders, and audit evidence.",
        pills: [
          {{ label: "Runs", value: payload.history_summary.total_runs }},
          {{ label: "Requests", value: payload.history_summary.total_execution_requests }},
          {{ label: "Executions", value: payload.history_summary.total_executions }},
        ],
      }},
      live: {{
        title: "Live",
        note: "Runner heartbeat and maintenance cadence. This is the operational surface that most closely resembles a live trading console.",
        pills: [
          {{ label: "Live Runners", value: payload.history_summary.live_runners }},
          {{ label: "Stalled Live", value: payload.history_summary.stalled_live_runners }},
          {{ label: "Stalled Maintenance", value: payload.history_summary.stalled_maintenance_runners }},
        ],
      }},
      broker: {{
        title: "Broker",
        note: "Freshness, sync quality, and local-versus-broker drift are grouped here so external state does not get lost inside backtest tables.",
        pills: [
          {{ label: "Broker Syncs", value: payload.history_summary.total_broker_syncs }},
          {{ label: "Failed Syncs", value: payload.history_summary.failed_broker_syncs }},
          {{ label: "Drift", value: payload.history_summary.broker_reconcile_mismatches }},
        ],
      }},
      alerts: {{
        title: "Alerts",
        note: "Treat this as the operator queue: inbox, ownership, SLA pressure, and delivery outcomes all live together.",
        pills: [
          {{ label: "Active", value: payload.history_summary.active_notifications }},
          {{ label: "Unacked", value: payload.history_summary.unacknowledged_notifications }},
          {{ label: "SLA Breached", value: payload.history_summary.sla_breached_notifications }},
        ],
      }},
      settings: {{
        title: "Settings",
        note: "This static page does not edit configuration yet, but the workflow slot is already in place so the product frame stays consistent.",
        pills: [
          {{ label: "Live Mode", value: payload.history_summary.live_runners ? "configured" : "idle" }},
          {{ label: "Broker Mode", value: payload.history_summary.total_broker_syncs ? "configured" : "off" }},
          {{ label: "Alert Flow", value: payload.history_summary.total_notifications ? "active" : "quiet" }},
        ],
      }},
    }};
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
      const workspace = params.get("workspace") || "overview";
      const runId = params.get("run") || "all";
      const lifecycleFilter = params.get("filter") || "all";
      const side = params.get("side") || "all";
      const broker = params.get("broker") || "all";
      const focus = params.get("focus") || "all";
      const executionStatus = params.get("execution_status") || "all";
      const notificationStatus = params.get("notification_status") || "all";
      const notificationOwner = params.get("notification_owner") || "all";
      const requestId = params.get("request") || "";
      const executionId = params.get("execution") || "";
      const orderId = params.get("order") || "";
      return {{
        workspace: Object.hasOwn(WORKSPACE_META, workspace) ? workspace : "overview",
        runId: availableRunIds().includes(runId) ? runId : "all",
        lifecycleFilter: ["all", "filled", "cancelled", "open", "repriced"].includes(lifecycleFilter) ? lifecycleFilter : "all",
        side: ["all", "BUY", "SELL"].includes(side) ? side : "all",
        broker: ["all", "pending_new", "working", "replaced", "partially_filled", "filled", "cancelled", "rejected", "local_skipped"].includes(broker) ? broker : "all",
        focus: ["all", "anomalies"].includes(focus) ? focus : "all",
        executionStatus: ["all", "completed", "failed", "blocked", "abandoned", "running", "protection"].includes(executionStatus) ? executionStatus : "all",
        notificationStatus: ["all", "queued", "dispatched", "delivery_failed_retryable", "delivery_failed_final", "filtered", "suppressed"].includes(notificationStatus) ? notificationStatus : "all",
        notificationOwner: ["all", "assigned", "unassigned"].includes(notificationOwner) ? notificationOwner : "all",
        requestId,
        executionId,
        orderId,
      }};
    }}
    const state = readHashState();
    function writeHashState() {{
      // 每次筛选变化后都同步回地址栏，保证“当前所见就是当前链接”。
      const params = new URLSearchParams();
      if (state.workspace !== "overview") params.set("workspace", state.workspace);
      if (state.runId !== "all") params.set("run", state.runId);
      if (state.lifecycleFilter !== "all") params.set("filter", state.lifecycleFilter);
      if (state.side !== "all") params.set("side", state.side);
      if (state.broker !== "all") params.set("broker", state.broker);
      if (state.focus !== "all") params.set("focus", state.focus);
      if (state.executionStatus !== "all") params.set("execution_status", state.executionStatus);
      if (state.notificationStatus !== "all") params.set("notification_status", state.notificationStatus);
      if (state.notificationOwner !== "all") params.set("notification_owner", state.notificationOwner);
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
      document.getElementById("notification-status-filter").value = state.notificationStatus;
      document.getElementById("notification-owner-filter").value = state.notificationOwner;
    }}
    function renderWorkspaceChrome() {{
      const meta = WORKSPACE_META[state.workspace] || WORKSPACE_META.overview;
      document.getElementById("workspace-title").textContent = meta.title;
      document.getElementById("workspace-note").textContent = meta.note;
      document.getElementById("workspace-pills").innerHTML = (meta.pills || []).map(pill => `
        <div class="workspace-pill"><strong>${{pill.label}}</strong>${{fmt(pill.value)}}</div>
      `).join("");
      document.querySelectorAll("[data-workspace-target]").forEach(node => {{
        node.classList.toggle("is-active", node.getAttribute("data-workspace-target") === state.workspace);
      }});
      document.querySelectorAll("[data-workspaces]").forEach(node => {{
        const workspaces = String(node.getAttribute("data-workspaces") || "").split(/\\s+/).filter(Boolean);
        node.setAttribute("data-hidden", workspaces.includes(state.workspace) ? "false" : "true");
      }});
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
      bits.push(`Notify: ${{state.notificationStatus}}`);
      bits.push(state.requestId ? `Request: ${{state.requestId}}` : "Request: none selected");
      bits.push(`Matches: ${{filteredLifecycleCount()}}`);
      bits.push(state.executionId ? `Execution: ${{state.executionId}}` : "Execution: none selected");
      bits.push(state.orderId ? `Order: ${{state.orderId}}` : "Order: none selected");
      document.getElementById("selected-context").textContent = bits.join(" | ");
    }}
    function renderCards() {{
      // 这里不再把所有指标无差别平铺，而是先给“主状态”，再给分组指标带。
      const summary = payload.history_summary;
      function toneForValue(value) {{
        const number = Number(value || 0);
        if (number >= 3) return "tone-critical";
        if (number > 0) return "tone-warn";
        return "tone-ok";
      }}
      const primary = [
        {{
          label: "Controller Issues",
          value: summary.controller_health_issues,
          note: "The fastest read on whether this page is calm or needs intervention.",
          tone: toneForValue(summary.controller_health_issues),
        }},
        {{
          label: "Critical Alerts",
          value: summary.critical_notifications,
          note: "Any unhandled high-severity alert should pull attention before run analytics.",
          tone: toneForValue(summary.critical_notifications),
        }},
        {{
          label: "Broker Drift",
          value: summary.broker_reconcile_mismatches,
          note: "Threshold-breached mismatches between local state and broker snapshot.",
          tone: toneForValue(summary.broker_reconcile_mismatches),
        }},
        {{
          label: "Stalled Runners",
          value: summary.stalled_live_runners,
          note: "Live polling loops that may have silently stopped producing cycles.",
          tone: toneForValue(summary.stalled_live_runners),
        }},
        {{
          label: "Stalled Maintenance Runners",
          value: summary.stalled_maintenance_runners,
          note: "Maintenance loops that are no longer refreshing runtime health.",
          tone: toneForValue(summary.stalled_maintenance_runners),
        }},
        {{
          label: "Pending Alerts",
          value: summary.pending_notifications,
          note: "Queued or retrying notifications that still need delivery or attention.",
          tone: toneForValue(summary.pending_notifications),
        }},
      ];
      const groups = [
        {{
          title: "Runtime Control",
          note: "Retry chains, protection state, and execution pressure.",
          metrics: [
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
            {{ label: "Stale Executions", value: summary.stale_execution_candidates }},
            {{ label: "Reconcile Queue", value: summary.runtime_reconcile_candidates }},
            {{ label: "Top Failure Class", value: summary.top_request_failure_class || "-" }},
          ],
        }},
        {{
          title: "Runner Cadence",
          note: "Heartbeat view across live loops and maintenance loops.",
          metrics: [
            {{ label: "Live Cycles", value: summary.total_live_cycles }},
            {{ label: "Live Completed", value: summary.completed_live_cycles }},
            {{ label: "Live Skipped", value: summary.skipped_live_cycles }},
            {{ label: "Live Blocked", value: summary.blocked_live_cycles }},
            {{ label: "Live Failed", value: summary.failed_live_cycles }},
            {{ label: "Live Runners", value: summary.live_runners }},
            {{ label: "Idle Runners", value: summary.idle_live_runners }},
            {{ label: "Stalled Runners", value: summary.stalled_live_runners }},
            {{ label: "Maintenance Cycles", value: summary.total_maintenance_cycles }},
            {{ label: "Failed Maintenance", value: summary.failed_maintenance_cycles }},
            {{ label: "Last Maintenance", value: summary.latest_maintenance_status || "-" }},
            {{ label: "Maintenance Runners", value: summary.maintenance_runners }},
            {{ label: "Stalled Maintenance Runners", value: summary.stalled_maintenance_runners }},
          ],
        }},
        {{
          title: "Broker and Alerts",
          note: "External state freshness plus the current alert queue.",
          metrics: [
            {{ label: "Broker Syncs", value: summary.total_broker_syncs }},
            {{ label: "Broker Sync Failed", value: summary.failed_broker_syncs }},
            {{ label: "Broker Stale", value: summary.stale_broker_syncs }},
            {{ label: "Broker Provider", value: summary.latest_broker_provider || "-" }},
            {{ label: "Broker Equity", value: summary.latest_broker_equity }},
            {{ label: "Broker Cash", value: summary.latest_broker_cash }},
            {{ label: "Broker Positions", value: summary.latest_broker_positions }},
            {{ label: "Broker Orders", value: summary.latest_broker_orders }},
            {{ label: "Notifications", value: summary.total_notifications }},
            {{ label: "Queued Alerts", value: summary.queued_notifications }},
            {{ label: "Dispatched Alerts", value: summary.dispatched_notifications }},
            {{ label: "Failed Alerts", value: summary.failed_notifications }},
            {{ label: "Retrying Alerts", value: summary.scheduled_retry_notifications }},
            {{ label: "Silenced Groups", value: summary.silenced_notification_groups }},
            {{ label: "Suppressed Dups", value: summary.suppressed_duplicates }},
            {{ label: "Acked Alerts", value: summary.acknowledged_notifications }},
            {{ label: "Unacked Alerts", value: summary.unacknowledged_notifications }},
            {{ label: "Active Alerts", value: summary.active_notifications }},
            {{ label: "Resolved Alerts", value: summary.resolved_notifications }},
            {{ label: "Reopened Alerts", value: summary.reopened_notifications }},
            {{ label: "Assigned Alerts", value: summary.assigned_notifications }},
            {{ label: "Unassigned Alerts", value: summary.unassigned_notifications }},
            {{ label: "Escalated Alerts", value: summary.escalated_notifications }},
            {{ label: "Escalated Unowned", value: summary.escalated_unassigned_notifications }},
            {{ label: "SLA Breached", value: summary.sla_breached_notifications }},
          ],
        }},
        {{
          title: "Research Snapshot",
          note: "Latest run and order lifecycle health at a glance.",
          metrics: [
            {{ label: "Latest Symbol", value: summary.latest_symbol || "-" }},
            {{ label: "Latest Return %", value: summary.latest_return_pct }},
            {{ label: "Latest Sharpe", value: summary.latest_sharpe_ratio }},
            {{ label: "Order Lifecycles", value: summary.total_lifecycles }},
            {{ label: "Lifecycle Filled", value: summary.filled_lifecycles }},
            {{ label: "Lifecycle Cancelled", value: summary.cancelled_lifecycles }},
            {{ label: "Lifecycle Repriced", value: summary.repriced_lifecycles }},
          ],
        }},
      ];
      document.getElementById("summary-cards").innerHTML = `
        <section class="summary-hero">
          ${{primary.map(card => `
            <article class="card ${{card.tone}}">
              <div class="card-label">${{card.label}}</div>
              <div class="card-value">${{fmt(card.value)}}</div>
              <div class="card-note">${{card.note}}</div>
            </article>
          `).join("")}}
        </section>
        <section class="summary-groups">
          ${{groups.map(group => `
            <article class="summary-group">
              <div class="summary-group-head">
                <h3 class="summary-group-title">${{group.title}}</h3>
                <div class="summary-group-note">${{group.note}}</div>
              </div>
              <div class="summary-group-grid">
                ${{group.metrics.map(metric => `
                  <div class="summary-mini">
                    <div class="summary-mini-label">${{metric.label}}</div>
                    <div class="summary-mini-value">${{fmt(metric.value)}}</div>
                  </div>
                `).join("")}}
              </div>
            </article>
          `).join("")}}
        </section>
      `;
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
    function renderLiveCycles() {{
      // live cycle 是 execution 之外再上一层的 runner 周期视角。
      const rows = (payload.recent_live_cycles || []).filter(cycle => {{
        if (state.runId !== "all" && cycle.run_id && cycle.run_id !== state.runId) return false;
        if (state.requestId && cycle.request_id && cycle.request_id !== state.requestId) return false;
        if (state.executionId && cycle.execution_id && cycle.execution_id !== state.executionId) return false;
        return true;
      }});
      document.getElementById("live-cycle-table").innerHTML = rows.length ? rows.map(cycle => `
        <tr class="${{cycle.status === "failed" || cycle.status === "blocked" ? "row-anomaly" : ""}}">
          <td>${{cycle.cycle_id}}</td>
          <td>${{cycle.runner_id}}</td>
          <td>${{cycle.status}}</td>
          <td>${{cycle.latest_bar_at || ""}}</td>
          <td>${{fmt(cycle.processed_bar_count)}}</td>
          <td>${{cycle.request_id || ""}}</td>
          <td>${{cycle.execution_id || ""}}</td>
          <td>${{cycle.run_id || ""}}</td>
          <td>${{cycle.skip_reason || ""}}</td>
          <td>${{cycle.protection_mode ? "on" : "off"}}</td>
          <td>${{cycle.cycle_note || cycle.error_message || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="11" class="muted">No live cycles in the current view.</td></tr>';
      const runnerRows = (payload.live_runner_summary || []).filter(row => {{
        if (state.runId !== "all" && !rows.some(cycle => cycle.run_id === state.runId && cycle.runner_id === row.runner_id && cycle.symbol === row.symbol && cycle.timeframe === row.timeframe)) {{
          return false;
        }}
        return true;
      }});
      document.getElementById("live-runner-table").innerHTML = runnerRows.length ? runnerRows.map(row => `
        <tr class="${{row.latest_status === "failed" || row.latest_status === "blocked" || row.stalled ? "row-anomaly" : ""}}">
          <td>${{row.runner_id}}</td>
          <td>${{row.symbol}} / ${{row.timeframe}}</td>
          <td>${{row.latest_status}}</td>
          <td>${{fmt(row.cycle_count)}}</td>
          <td>${{fmt(row.completed_count)}}</td>
          <td>${{fmt(row.skipped_count)}}</td>
          <td>${{fmt(row.blocked_count)}}</td>
          <td>${{fmt(row.failed_count)}}</td>
          <td>${{fmt(row.idle_streak)}}</td>
          <td>${{fmt(row.last_cycle_age_seconds)}}</td>
          <td>${{fmt(row.stall_threshold_seconds)}}</td>
          <td>${{row.stalled ? "yes" : "no"}}</td>
          <td>${{fmt(row.protection_hits)}}</td>
          <td>${{row.last_success_at || ""}}</td>
          <td>${{row.latest_bar_at || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="15" class="muted">No live runner summary rows in the current view.</td></tr>';

      // broker sync 先走只读快照，但也需要和 runner / request / execution 放在同一页排查。
      const brokerRows = (payload.recent_broker_syncs || []).filter(sync => {{
        if (state.executionId && sync.cycle_id) {{
          const matchedCycle = rows.find(cycle => cycle.cycle_id === sync.cycle_id);
          if (matchedCycle && matchedCycle.execution_id && matchedCycle.execution_id !== state.executionId) {{
            return false;
          }}
        }}
        if (state.requestId && sync.cycle_id) {{
          const matchedCycle = rows.find(cycle => cycle.cycle_id === sync.cycle_id);
          if (matchedCycle && matchedCycle.request_id && matchedCycle.request_id !== state.requestId) {{
            return false;
          }}
        }}
        return true;
      }});
      document.getElementById("broker-sync-table").innerHTML = brokerRows.length ? brokerRows.map(sync => `
        <tr class="${{sync.status === "failed" ? "row-anomaly" : ""}}">
          <td>${{sync.sync_id}}</td>
          <td>${{sync.provider}}</td>
          <td>${{sync.synced_at || ""}}</td>
          <td>${{sync.status}}</td>
          <td>${{sync.account_id || ""}}</td>
          <td>${{fmt(sync.equity)}}</td>
          <td>${{fmt(sync.cash)}}</td>
          <td>${{fmt(sync.position_count)}}</td>
          <td>${{fmt(sync.order_count)}}</td>
          <td>${{sync.runner_id || ""}}</td>
          <td>${{sync.cycle_id || ""}}</td>
          <td>${{sync.error_message || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="12" class="muted">No broker sync rows in the current view.</td></tr>';
      const maintenanceRows = payload.recent_maintenance_cycles || [];
      document.getElementById("maintenance-cycle-table").innerHTML = maintenanceRows.length ? maintenanceRows.map(cycle => `
        <tr class="${{cycle.status === "failed" ? "row-anomaly" : ""}}">
          <td>${{cycle.cycle_id}}</td>
          <td>${{cycle.runner_id || ""}}</td>
          <td>${{cycle.status}}</td>
          <td>${{cycle.started_at || ""}}</td>
          <td>${{cycle.reconcile_runtime ? "yes" : "no"}}</td>
          <td>${{cycle.broker_sync_status || "-"}}</td>
          <td>${{fmt(cycle.recovered_stale_executions)}}</td>
          <td>${{fmt(cycle.controller_issue_count)}}</td>
          <td>${{fmt(cycle.emitted_notification_count)}}</td>
          <td>${{fmt(cycle.escalated_notification_count)}}</td>
          <td>${{fmt(cycle.delivered_notification_count)}}</td>
          <td>${{fmt(cycle.remaining_pending_notifications)}}</td>
          <td>${{cycle.cycle_note || cycle.error_message || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="13" class="muted">No maintenance cycles in the current view.</td></tr>';
      const maintenanceRunnerRows = payload.maintenance_runner_summary || [];
      document.getElementById("maintenance-runner-table").innerHTML = maintenanceRunnerRows.length ? maintenanceRunnerRows.map(row => `
        <tr class="${{row.stalled || row.latest_status === "failed" ? "row-anomaly" : ""}}">
          <td>${{row.runner_id}}</td>
          <td>${{row.latest_status}}</td>
          <td>${{fmt(row.cycle_count)}}</td>
          <td>${{fmt(row.failed_count)}}</td>
          <td>${{fmt(row.last_cycle_age_seconds)}}</td>
          <td>${{fmt(row.stall_threshold_seconds)}}</td>
          <td>${{row.stalled ? "yes" : "no"}}</td>
          <td>${{row.last_success_at || ""}}</td>
          <td>${{fmt(row.total_delivered_notifications)}}</td>
          <td>${{fmt(row.latest_pending_notifications)}}</td>
        </tr>
      `).join("") : '<tr><td colspan="10" class="muted">No maintenance runner summary rows in the current view.</td></tr>';
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
    function renderNotifications() {{
      function buildNotificationOwnerSummary(events) {{
        const grouped = new Map();
        events.forEach(event => {{
          const owner = (event.assigned_to || "").trim() || "(unassigned)";
          const row = grouped.get(owner) || {{
            owner,
            event_count: 0,
            active_count: 0,
            resolved_count: 0,
            reopened_count: 0,
            unacknowledged_count: 0,
            escalated_count: 0,
            open_high_priority_count: 0,
            last_seen_at: "",
          }};
          row.event_count += 1;
          const resolved = !!event.resolved_at;
          if (resolved) {{
            row.resolved_count += 1;
          }} else {{
            row.active_count += 1;
          }}
          if ((event.reopen_count || 0) > 0) row.reopened_count += 1;
          if (!resolved && !event.acknowledged_at) row.unacknowledged_count += 1;
          if (!resolved && event.escalated_at) row.escalated_count += 1;
          if (!resolved && !event.acknowledged_at && ["error", "critical"].includes(event.severity || "")) {{
            row.open_high_priority_count += 1;
          }}
          if ((event.timestamp || "") > row.last_seen_at) {{
            row.last_seen_at = event.timestamp || "";
          }}
          grouped.set(owner, row);
        }});
        return Array.from(grouped.values()).sort((left, right) => {{
          if ((right.unacknowledged_count || 0) !== (left.unacknowledged_count || 0)) {{
            return (right.unacknowledged_count || 0) - (left.unacknowledged_count || 0);
          }}
          if ((right.escalated_count || 0) !== (left.escalated_count || 0)) {{
            return (right.escalated_count || 0) - (left.escalated_count || 0);
          }}
          if ((right.event_count || 0) !== (left.event_count || 0)) {{
            return (right.event_count || 0) - (left.event_count || 0);
          }}
          return String(left.owner || "").localeCompare(String(right.owner || ""));
        }});
      }}

      const summaryRows = payload.notification_summary.filter(row => {{
        const matchingEvents = payload.recent_notifications.filter(event => {{
          if (state.runId !== "all" && event.run_id && event.run_id !== state.runId) return false;
          if (state.requestId && event.request_id && event.request_id !== state.requestId) return false;
          if (state.executionId && event.execution_id && event.execution_id !== state.executionId) return false;
          if (state.notificationStatus !== "all" && event.delivery_status !== state.notificationStatus) return false;
          if (state.notificationOwner === "assigned" && !event.assigned_to) return false;
          if (state.notificationOwner === "unassigned" && event.assigned_to) return false;
          return (
            event.category === row.category &&
            event.severity === row.severity &&
            event.delivery_status === row.delivery_status
          );
        }});
        return matchingEvents.length > 0;
      }});
      document.getElementById("notification-summary-table").innerHTML = summaryRows.length ? summaryRows.map(row => `
        <tr>
          <td>${{row.category}}</td>
          <td>${{row.severity}}</td>
          <td>${{row.delivery_status}}</td>
          <td>${{fmt(row.event_count)}}</td>
          <td>${{fmt(row.suppressed_duplicates)}}</td>
          <td>${{row.last_seen_at || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="6" class="muted">No notification summary rows in the current view.</td></tr>';

      // 通知事件是“系统决定应该提醒人”的那一层，比普通日志更接近运维值班视角。
      const rows = payload.recent_notifications.filter(event => {{
        if (state.runId !== "all" && event.run_id && event.run_id !== state.runId) return false;
        if (state.requestId && event.request_id && event.request_id !== state.requestId) return false;
        if (state.executionId && event.execution_id && event.execution_id !== state.executionId) return false;
        if (state.notificationStatus !== "all" && event.delivery_status !== state.notificationStatus) return false;
        if (state.notificationOwner === "assigned" && !event.assigned_to) return false;
        if (state.notificationOwner === "unassigned" && event.assigned_to) return false;
        return true;
      }});
      const ownerRows = buildNotificationOwnerSummary(rows);
      document.getElementById("notification-owner-table").innerHTML = ownerRows.length ? ownerRows.map(row => `
        <tr>
          <td>${{row.owner}}</td>
          <td>${{fmt(row.event_count)}}</td>
          <td>${{fmt(row.active_count)}}</td>
          <td>${{fmt(row.resolved_count)}}</td>
          <td>${{fmt(row.reopened_count)}}</td>
          <td>${{fmt(row.unacknowledged_count)}}</td>
          <td>${{fmt(row.escalated_count)}}</td>
          <td>${{fmt(row.open_high_priority_count)}}</td>
          <td>${{row.last_seen_at || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="9" class="muted">No notification owner rows in the current view.</td></tr>';
      const inboxRows = (payload.notification_inbox || []).filter(row => {{
        if (state.notificationOwner === "assigned" && (!row.owner || row.owner === "(unassigned)")) return false;
        if (state.notificationOwner === "unassigned" && row.owner && row.owner !== "(unassigned)") return false;
        return true;
      }});
      document.getElementById("notification-inbox-table").innerHTML = inboxRows.length ? inboxRows.map(row => `
        <tr>
          <td>${{row.owner}}</td>
          <td>${{row.event_id}}</td>
          <td>${{row.severity}}</td>
          <td>${{row.category}}</td>
          <td>${{row.title}}</td>
          <td>${{row.active_since || ""}}</td>
          <td>${{fmt(row.age_seconds)}}</td>
          <td>${{row.ack_state}}</td>
          <td>${{row.escalated ? "yes" : "no"}}</td>
          <td>${{row.reopened ? "yes" : "no"}}</td>
          <td>${{fmt(row.reopen_count)}}</td>
          <td>${{row.next_delivery_attempt_at || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="12" class="muted">No active notification inbox rows in the current view.</td></tr>';
      const slaRows = (payload.notification_sla_summary || []).filter(row => {{
        if (state.notificationOwner === "assigned" && (!row.owner || row.owner === "(unassigned)")) return false;
        if (state.notificationOwner === "unassigned" && row.owner && row.owner !== "(unassigned)") return false;
        return true;
      }});
      document.getElementById("notification-sla-table").innerHTML = slaRows.length ? slaRows.map(row => `
        <tr>
          <td>${{row.owner}}</td>
          <td>${{row.event_id}}</td>
          <td>${{row.severity}}</td>
          <td>${{row.category}}</td>
          <td>${{row.assigned_at || ""}}</td>
          <td>${{fmt(row.age_seconds)}}</td>
          <td>${{fmt(row.sla_seconds)}}</td>
          <td>${{row.sla_source || "default"}}</td>
          <td>${{fmt(row.breach_seconds)}}</td>
        </tr>
      `).join("") : '<tr><td colspan="9" class="muted">No SLA-breached notifications in the current view.</td></tr>';
      const brokerHealth = payload.broker_health || {{}};
      document.getElementById("broker-health-table").innerHTML = brokerHealth.latest_sync_id ? `
        <tr class="${{brokerHealth.failed || brokerHealth.stale ? "row-anomaly" : ""}}">
          <td>${{brokerHealth.latest_provider || ""}}</td>
          <td>${{brokerHealth.latest_status || ""}}</td>
          <td>${{brokerHealth.latest_synced_at || ""}}</td>
          <td>${{fmt(brokerHealth.snapshot_age_seconds || 0)}}</td>
          <td>${{fmt(brokerHealth.max_snapshot_age_seconds || 0)}}</td>
          <td>${{brokerHealth.stale ? "yes" : "no"}}</td>
          <td>${{fmt(brokerHealth.failed_sync_count || 0)}}</td>
          <td>${{brokerHealth.latest_runner_id || ""}}</td>
          <td>${{brokerHealth.latest_cycle_id || ""}}</td>
          <td>${{brokerHealth.detail || ""}}</td>
        </tr>
      ` : '<tr><td colspan="10" class="muted">No broker health rows in the current view.</td></tr>';
      const brokerReconcile = payload.broker_reconcile || {{}};
      document.getElementById("broker-reconcile-meta").textContent = brokerReconcile.latest_broker_sync_id
        ? `Status: ${{brokerReconcile.status}} | Mismatches: ${{fmt(brokerReconcile.mismatch_count || 0)}} | Run: ${{brokerReconcile.latest_run_id || ""}} | Sync: ${{brokerReconcile.latest_broker_sync_id || ""}} | Note: ${{(brokerReconcile.notes || []).join("; ")}}`
        : "No broker reconcile preview available.";
      document.getElementById("broker-reconcile-table").innerHTML = (brokerReconcile.rows || []).length ? (brokerReconcile.rows || []).map(row => `
        <tr class="${{row.breached ? "row-anomaly" : ""}}">
          <td>${{row.metric}}</td>
          <td>${{fmt(row.local_value)}}</td>
          <td>${{fmt(row.broker_value)}}</td>
          <td>${{fmt(row.delta)}}</td>
          <td>${{fmt(row.threshold)}}</td>
          <td>${{row.breached ? "yes" : "no"}}</td>
        </tr>
      `).join("") : '<tr><td colspan="6" class="muted">No broker reconcile rows in the current view.</td></tr>';
      const controllerIssues = (payload.controller_health?.issues || []);
      document.getElementById("controller-health-table").innerHTML = controllerIssues.length ? controllerIssues.map(issue => `
        <tr>
          <td>${{issue.severity}}</td>
          <td>${{issue.code}}</td>
          <td>${{fmt(issue.count)}}</td>
          <td>${{issue.detail || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="4" class="muted">No controller health issues in the current view.</td></tr>';
      document.getElementById("notifications-table").innerHTML = rows.length ? rows.map(event => `
        <tr>
          <td>${{event.timestamp}}</td>
          <td>${{event.severity}}</td>
          <td>${{event.category}}</td>
          <td>${{event.title}}</td>
          <td>${{event.delivery_status}}</td>
          <td>${{fmt(event.delivery_attempts ?? 0)}}</td>
          <td>${{fmt(event.suppressed_duplicate_count ?? 0)}}</td>
          <td>${{event.next_delivery_attempt_at || ""}}</td>
          <td>${{event.silenced_until || ""}}</td>
          <td>${{event.assigned_to || ""}}</td>
          <td>${{event.assigned_at || ""}}</td>
          <td>${{event.resolved_at || ""}}</td>
          <td>${{event.reopened_at || ""}}</td>
          <td>${{fmt(event.reopen_count ?? 0)}}</td>
          <td>${{event.acknowledged_at || ""}}</td>
          <td>${{event.escalated_at || ""}}</td>
          <td>${{event.provider}}</td>
          <td>${{event.assignment_note || ""}}</td>
          <td>${{event.resolved_note || ""}}</td>
          <td>${{event.reopened_note || ""}}</td>
          <td>${{event.acknowledged_note || ""}}</td>
          <td>${{event.escalation_level || event.escalation_reason || ""}}</td>
          <td>${{event.last_error || ""}}</td>
          <td>${{event.execution_id || ""}}</td>
        </tr>
      `).join("") : '<tr><td colspan="24" class="muted">No notification events in the current view.</td></tr>';
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
      renderWorkspaceChrome();
      syncControlsToState();
      renderContext();
      renderRuns();
      renderRequestChains();
      renderExecutions();
      renderLiveCycles();
      renderLifecycles();
      renderOrders();
      renderNotifications();
      renderAudit();
      writeHashState();
    }}
    hydrateRunFilter();
    renderCards();
    renderAll();
    document.querySelectorAll("[data-workspace-target]").forEach(node => {{
      node.addEventListener("click", () => {{
        state.workspace = node.getAttribute("data-workspace-target") || "overview";
        renderAll();
      }});
    }});
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
    document.getElementById("notification-status-filter").addEventListener("change", event => {{
      state.notificationStatus = event.target.value || "all";
      renderAll();
    }});
    document.getElementById("notification-owner-filter").addEventListener("change", event => {{
      state.notificationOwner = event.target.value || "all";
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
      state.notificationStatus = "all";
      state.notificationOwner = "all";
      state.executionStatus = "all";
      state.requestId = "";
      state.executionId = "";
      state.orderId = "";
      renderAll();
    }});
    document.getElementById("copy-link").addEventListener("click", copyCurrentLink);
    window.addEventListener("hashchange", () => {{
      const next = readHashState();
      state.workspace = next.workspace;
      state.runId = next.runId;
      state.lifecycleFilter = next.lifecycleFilter;
      state.side = next.side;
      state.broker = next.broker;
      state.focus = next.focus;
      state.notificationStatus = next.notificationStatus;
      state.notificationOwner = next.notificationOwner;
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
