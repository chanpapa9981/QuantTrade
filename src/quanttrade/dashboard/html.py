from __future__ import annotations

import json
from pathlib import Path


def render_dashboard_html(payload: dict[str, object], output_path: str) -> str:
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
      --line: #27486f;
      --text: #e8f0ff;
      --muted: #8ea5c6;
      --accent: #4fb3ff;
      --accent-2: #8ce99a;
      --warn: #ffb65c;
      --danger: #ff6b6b;
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
      gap: 14px;
      margin-bottom: 28px;
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
      max-width: 720px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
    }}

    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }}

    .card, .panel {{
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)), var(--panel);
      border: 1px solid rgba(255,255,255,0.06);
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
      grid-template-columns: 1.5fr 1fr;
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

    .stat {{
      padding: 14px;
      border-radius: 16px;
      background: var(--panel-alt);
      border: 1px solid rgba(255,255,255,0.05);
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
      border: 1px solid rgba(255,255,255,0.04);
      padding: 12px;
    }}

    svg {{
      width: 100%;
      height: 100%;
      display: block;
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
      border-bottom: 1px solid rgba(255,255,255,0.06);
      text-align: left;
      white-space: nowrap;
    }}

    th {{
      color: var(--muted);
      font-weight: 600;
    }}

    .buy {{ color: var(--accent-2); }}
    .sell {{ color: var(--warn); }}

    @media (max-width: 980px) {{
      .layout {{
        grid-template-columns: 1fr;
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
        A static research dashboard generated from the current QuantTrade backtest pipeline.
        It is designed to make the strategy state, account state, equity progression, drawdown behavior,
        and recent fills readable without spinning up a server.
      </div>
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
                  <th>Qty</th>
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

    function fmt(value) {{
      return typeof value === "number" ? value.toLocaleString(undefined, {{ maximumFractionDigits: 4 }}) : value;
    }}

    function renderCards() {{
      const target = document.getElementById("summary-cards");
      target.innerHTML = payload.summary_cards.map(card => `
        <article class="card">
          <div class="card-label">${{card.label}}</div>
          <div class="card-value">${{fmt(card.value)}}</div>
        </article>
      `).join("");
    }}

    function renderStats(id, stats) {{
      const target = document.getElementById(id);
      target.innerHTML = Object.entries(stats).map(([key, value]) => `
        <div class="stat">
          <dt>${{key.replace(/_/g, " ")}}</dt>
          <dd>${{fmt(value)}}</dd>
        </div>
      `).join("");
    }}

    function renderTrades() {{
      const target = document.getElementById("recent-trades");
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

    function renderOrders() {{
      const target = document.getElementById("recent-orders");
      target.innerHTML = payload.recent_orders.map(order => `
        <tr>
          <td>${{order.timestamp}}</td>
          <td class="${{order.side === "BUY" ? "buy" : "sell"}}">${{order.side}}</td>
          <td>${{order.status}}</td>
          <td>${{fmt(order.quantity)}}</td>
          <td>${{fmt(order.requested_price)}}</td>
          <td>${{fmt(order.fill_price)}}</td>
          <td>${{order.reason}}</td>
        </tr>
      `).join("");
    }}

    function renderAuditLog() {{
      const target = document.getElementById("audit-log");
      target.innerHTML = payload.audit_timeline.map(event => `
        <tr>
          <td>${{event.timestamp}}</td>
          <td>${{event.event}}</td>
          <td>${{event.signal}}</td>
          <td>${{event.reason}}</td>
        </tr>
      `).join("");
    }}

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

    function renderChart(id, items, accessor, stroke, fill) {{
      const svg = document.getElementById(id);
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

    renderCards();
    renderStats("account-summary", payload.account_summary);
    renderStats("performance-summary", payload.performance_summary);
    renderStats("order-summary", payload.order_summary);
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
                  <th>Return %</th>
                  <th>Sharpe</th>
                  <th>Trades</th>
                </tr>
              </thead>
              <tbody id="runs-table"></tbody>
            </table>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <h2 class="panel-title">Recent Orders</h2>
          <div class="panel-note">Latest persisted order events</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Status</th>
                  <th>Qty</th>
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
    function fmt(value) {{
      return typeof value === "number" ? value.toLocaleString(undefined, {{ maximumFractionDigits: 4 }}) : value;
    }}
    function renderCards() {{
      const summary = payload.history_summary;
      const cards = [
        {{ label: "Total Runs", value: summary.total_runs }},
        {{ label: "Latest Symbol", value: summary.latest_symbol }},
        {{ label: "Latest Return %", value: summary.latest_return_pct }},
        {{ label: "Latest Sharpe", value: summary.latest_sharpe_ratio }},
      ];
      document.getElementById("summary-cards").innerHTML = cards.map(card => `
        <article class="card">
          <div class="card-label">${{card.label}}</div>
          <div class="card-value">${{fmt(card.value)}}</div>
        </article>
      `).join("");
    }}
    function renderRuns() {{
      document.getElementById("runs-table").innerHTML = payload.runs_table.map(run => `
        <tr>
          <td>${{run.run_id}}</td>
          <td>${{run.symbol}}</td>
          <td>${{run.started_at}}</td>
          <td>${{fmt(run.total_return_pct)}}</td>
          <td>${{fmt(run.sharpe_ratio)}}</td>
          <td>${{fmt(run.total_trades)}}</td>
        </tr>
      `).join("");
    }}
    function renderOrders() {{
      document.getElementById("orders-table").innerHTML = payload.recent_orders.map(order => `
        <tr>
          <td>${{order.timestamp}}</td>
          <td class="${{order.side === "BUY" ? "buy" : "sell"}}">${{order.side}}</td>
          <td>${{order.status}}</td>
          <td>${{fmt(order.quantity)}}</td>
          <td>${{order.reason}}</td>
        </tr>
      `).join("");
    }}
    function renderAudit() {{
      document.getElementById("audit-table").innerHTML = payload.recent_audit_events.map(event => `
        <tr>
          <td>${{event.timestamp}}</td>
          <td>${{event.event}}</td>
          <td>${{event.signal}}</td>
          <td>${{event.reason}}</td>
        </tr>
      `).join("");
    }}
    renderCards();
    renderRuns();
    renderOrders();
    renderAudit();
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)
