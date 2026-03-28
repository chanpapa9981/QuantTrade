"""配置加载器测试。"""

import unittest
from pathlib import Path

from quanttrade.config.loader import load_settings


class ConfigLoaderTestCase(unittest.TestCase):
    def test_load_settings_reads_yaml(self) -> None:
        """确认最小 YAML 配置能被正确读入，并自动补上默认值。"""
        tmp_path = Path("var/test-artifacts")
        tmp_path.mkdir(parents=True, exist_ok=True)
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            "\n".join(
                [
                    "app:",
                    "  app_name: TestApp",
                    "strategy:",
                    "  symbol: MSFT",
                ]
            ),
            encoding="utf-8",
        )

        settings = load_settings(config_file)

        self.assertEqual(settings.app.app_name, "TestApp")
        self.assertEqual(settings.strategy.symbol, "MSFT")
        self.assertEqual(settings.risk.max_open_positions, 5)
        self.assertEqual(settings.broker.provider, "local_file")
        self.assertFalse(settings.broker.enabled)
        self.assertEqual(settings.broker.equity_drift_threshold, 0.0)
        self.assertEqual(settings.broker.cash_drift_threshold, 0.0)


if __name__ == "__main__":
    unittest.main()
