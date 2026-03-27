"""审计日志配置。"""

from __future__ import annotations

import logging


def configure_logging() -> None:
    """初始化项目统一日志格式。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
