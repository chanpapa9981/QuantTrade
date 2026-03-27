import unittest
from pathlib import Path

from quanttrade.config.loader import load_settings


class ConfigLoaderTestCase(unittest.TestCase):
    def test_load_settings_reads_yaml(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
