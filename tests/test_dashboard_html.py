"""静态 dashboard HTML 导出测试。"""

import csv
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quanttrade.app import QuantTradeApp


class DashboardHtmlTestCase(unittest.TestCase):
    def test_export_dashboard_html_writes_expected_sections(self) -> None:
        """确认导出的 HTML 页面包含主要面板和表格区域。"""
        base_dir = Path("var/test-artifacts/dashboard-html")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "dashboard-html-test.duckdb"
        config_path = base_dir / "settings.yaml"
        output_path = base_dir / "dashboard.html"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 3, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.05
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.6, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_200_000 + offset * 1000,
                    }
                )

        config_path.write_text(
            "\n".join(
                [
                    "strategy:",
                    "  symbol: AAPL",
                    "  entry_donchian_n: 5",
                    "  exit_donchian_m: 3",
                    "  atr_smooth_period: 5",
                    "  risk_coefficient_k: 2.0",
                    "  adx_trend_filter: 5.0",
                    "data:",
                    f"  duckdb_path: {db_path}",
                    "  backend: duckdb",
                ]
            ),
            encoding="utf-8",
        )

        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        result = app.export_dashboard_html(symbol="AAPL", timeframe="1d", initial_equity=100_000.0, output_path=str(output_path))

        self.assertEqual(result["output_path"], str(output_path))
        self.assertTrue(output_path.exists())
        html = output_path.read_text(encoding="utf-8")
        self.assertIn("Backtest Dashboard", html)
        self.assertIn("Equity Curve", html)
        self.assertIn("Recent Trades", html)
        self.assertIn("Recent Orders", html)
        self.assertIn("Audit Timeline", html)


if __name__ == "__main__":
    unittest.main()
