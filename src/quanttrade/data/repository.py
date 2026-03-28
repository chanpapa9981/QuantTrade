"""数据仓储层。

仓储层的职责不是“做业务判断”，而是“把数据正确地存进去、取出来、整理好”。
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from quanttrade.core.types import MarketBar
from quanttrade.data.storage import connect_database


class BarRepository:
    """负责行情 bars 的读写。"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def insert_bars(self, symbol: str, timeframe: str, bars: list[MarketBar]) -> int:
        """批量写入行情 bar。"""
        connection = connect_database(self.db_path)
        try:
            payload = [
                (
                    symbol,
                    timeframe,
                    bar.timestamp.isoformat(),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                )
                for bar in bars
            ]
            connection.executemany(
                """
                INSERT OR REPLACE INTO bars(
                    symbol, timeframe, timestamp, open, high, low, close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            return len(payload)
        finally:
            connection.close()

    def fetch_bars(self, symbol: str, timeframe: str = "1d") -> list[MarketBar]:
        """按标的和周期读取历史 bar。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "bars" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT timestamp, open, high, low, close, volume
                FROM bars
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp
                """,
                (symbol, timeframe),
            ).fetchall()
        finally:
            connection.close()

        return [
            MarketBar(
                timestamp=datetime.fromisoformat(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in rows
        ]


class BacktestRunRepository:
    """负责回测运行、订单、审计日志、快照等持久化读写。"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _recent_statuses(self, connection: object, symbol: str, timeframe: str, limit: int = 20) -> list[str]:
        """读取同标的同周期最近的执行状态，用于判断是否出现连续失败。"""
        rows = connection.execute(
            """
            SELECT status
            FROM backtest_executions
            WHERE symbol = ? AND timeframe = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (symbol, timeframe, limit),
        ).fetchall()
        return [str(row[0]) for row in rows]

    def _consecutive_failure_count(self, connection: object, symbol: str, timeframe: str) -> int:
        """统计最近连续失败/中断的次数，直到遇到一次 completed 为止。"""
        count = 0
        for status in self._recent_statuses(connection, symbol, timeframe):
            if status == "completed":
                break
            if status in {"failed", "abandoned"}:
                count += 1
        return count

    def _latest_abnormal_execution_reference(
        self,
        connection: object,
        symbol: str,
        timeframe: str,
    ) -> dict[str, str] | None:
        """读取最近一次异常 execution，用来推导保护模式冷却窗口。"""
        row = connection.execute(
            """
            SELECT execution_id, status, COALESCE(finished_at, started_at, '') AS reference_at
            FROM backtest_executions
            WHERE symbol = ? AND timeframe = ? AND status != ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (symbol, timeframe, "completed"),
        ).fetchone()
        if row is None:
            return None
        return {
            "execution_id": str(row[0]),
            "status": str(row[1]),
            "reference_at": str(row[2] or ""),
        }

    def _protection_mode_state(
        self,
        connection: object,
        symbol: str,
        timeframe: str,
        protection_mode_failure_threshold: int,
        protection_mode_cooldown_seconds: int,
    ) -> dict[str, object]:
        """根据连续失败和冷却窗口，判断下一次 execution 启动是否仍应被保护模式拦截。"""
        consecutive_failures = self._consecutive_failure_count(connection, symbol, timeframe)
        threshold = max(int(protection_mode_failure_threshold), 1)
        cooldown_seconds = max(int(protection_mode_cooldown_seconds), 0)
        if consecutive_failures < threshold:
            return {
                "consecutive_failures": consecutive_failures,
                "protection_mode": 0,
                "protection_reason": "",
                "protection_cooldown_until": "",
            }

        if cooldown_seconds <= 0:
            return {
                "consecutive_failures": consecutive_failures,
                "protection_mode": 1,
                "protection_reason": f"entered protection mode after {threshold} consecutive failed executions",
                "protection_cooldown_until": "",
            }

        latest_abnormal = self._latest_abnormal_execution_reference(connection, symbol, timeframe)
        if latest_abnormal is None or not latest_abnormal.get("reference_at"):
            return {
                "consecutive_failures": consecutive_failures,
                "protection_mode": 1,
                "protection_reason": (
                    f"entered protection mode after {threshold} consecutive failed executions; "
                    "cooldown reference time was unavailable"
                ),
                "protection_cooldown_until": "",
            }

        reference_at = datetime.fromisoformat(str(latest_abnormal["reference_at"]))
        cooldown_until = reference_at + timedelta(seconds=cooldown_seconds)
        cooldown_until_iso = cooldown_until.isoformat()
        now = datetime.now(UTC)
        if cooldown_until > now:
            return {
                "consecutive_failures": consecutive_failures,
                "protection_mode": 1,
                "protection_reason": (
                    f"entered protection mode after {threshold} consecutive failed executions; "
                    f"cooldown active until {cooldown_until_iso}"
                ),
                "protection_cooldown_until": cooldown_until_iso,
            }

        return {
            "consecutive_failures": consecutive_failures,
            "protection_mode": 0,
            "protection_reason": (
                f"protection cooldown expired at {cooldown_until_iso}; "
                f"allowing resume after {consecutive_failures} consecutive failed executions"
            ),
            "protection_cooldown_until": cooldown_until_iso,
        }

    @staticmethod
    def _execution_select_clause(connection: object) -> str:
        """根据数据库当前实际列，构造兼容新旧版本的 execution 查询字段。

        这里不能简单写死 `SELECT retryable, retry_decision ...`，
        因为旧库可能还没迁移到这些字段。最稳妥的做法是：
        - 如果列存在，就读真实值；
        - 如果列不存在，就返回带别名的默认值。
        """
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info('backtest_executions')").fetchall()
        }
        select_map = {
            "execution_id": "execution_id",
            "request_id": "request_id" if "request_id" in columns else "'' AS request_id",
            "symbol": "symbol",
            "timeframe": "timeframe",
            "initial_equity": "initial_equity",
            "attempt_number": "attempt_number" if "attempt_number" in columns else "1 AS attempt_number",
            "recovered_execution_count": (
                "recovered_execution_count" if "recovered_execution_count" in columns else "0 AS recovered_execution_count"
            ),
            "consecutive_failures_before_start": (
                "consecutive_failures_before_start"
                if "consecutive_failures_before_start" in columns
                else "0 AS consecutive_failures_before_start"
            ),
            "protection_mode": "protection_mode" if "protection_mode" in columns else "0 AS protection_mode",
            "protection_reason": "protection_reason" if "protection_reason" in columns else "'' AS protection_reason",
            "protection_cooldown_until": (
                "protection_cooldown_until"
                if "protection_cooldown_until" in columns
                else "'' AS protection_cooldown_until"
            ),
            "retryable": "retryable" if "retryable" in columns else "0 AS retryable",
            "retry_decision": "retry_decision" if "retry_decision" in columns else "'' AS retry_decision",
            "failure_class": "failure_class" if "failure_class" in columns else "'' AS failure_class",
            "status": "status",
            "requested_at": "requested_at",
            "started_at": "started_at",
            "finished_at": "finished_at",
            "run_id": "run_id",
            "error_message": "error_message",
        }
        ordered_keys = [
            "execution_id",
            "request_id",
            "symbol",
            "timeframe",
            "initial_equity",
            "attempt_number",
            "recovered_execution_count",
            "consecutive_failures_before_start",
            "protection_mode",
            "protection_reason",
            "protection_cooldown_until",
            "retryable",
            "retry_decision",
            "failure_class",
            "status",
            "requested_at",
            "started_at",
            "finished_at",
            "run_id",
            "error_message",
        ]
        return ", ".join(select_map[key] for key in ordered_keys)

    @staticmethod
    def _execution_row_to_dict(row: object) -> dict[str, object]:
        """把统一顺序的 execution 查询结果转换成字典。"""
        return {
            "execution_id": row[0],
            "request_id": row[1],
            "symbol": row[2],
            "timeframe": row[3],
            "initial_equity": row[4],
            "attempt_number": row[5],
            "recovered_execution_count": row[6],
            "consecutive_failures_before_start": row[7],
            "protection_mode": bool(row[8]),
            "protection_reason": row[9],
            "protection_cooldown_until": row[10],
            "retryable": bool(row[11]),
            "retry_decision": row[12],
            "failure_class": row[13],
            "status": row[14],
            "requested_at": row[15],
            "started_at": row[16],
            "finished_at": row[17],
            "run_id": row[18],
            "error_message": row[19],
        }

    @staticmethod
    def _failure_class_summary(attempts: list[dict[str, object]]) -> list[dict[str, object]]:
        """统计一条 request 链里最常见的失败类别。

        这里单独输出列表，而不是只给一个字符串，是为了让 CLI 和页面都能同时看到：
        - 有没有多种失败混在同一条链里；
        - 哪一类失败出现得最多；
        - 后续如果要按类别排序或聚合，也能直接复用这份结构。
        """
        counter = Counter(
            str(item.get("failure_class", "")).strip()
            for item in attempts
            if str(item.get("failure_class", "")).strip()
        )
        return [
            {"failure_class": failure_class, "count": count}
            for failure_class, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    @staticmethod
    def _request_anomaly_score(attempts: list[dict[str, object]], latest: dict[str, object]) -> int:
        """给 request 链算一个简单异常分数，便于先看最值得排查的请求。

        分数不是风险模型，只是排错优先级：
        - 最终失败 / 被拦截，比普通重试更严重；
        - 明确不可重试的错误，比可重试瞬时错误更值得优先处理；
        - 保护模式、恢复启动、重复重试都会把分数继续抬高。
        """
        retry_scheduled_count = len([item for item in attempts if item.get("retry_decision") == "retry_scheduled"])
        final_failure_count = len([item for item in attempts if item.get("retry_decision") == "final_failure"])
        non_retryable_failure_count = len(
            [
                item
                for item in attempts
                if item.get("status") == "failed" and not bool(item.get("retryable"))
            ]
        )
        recovered_starts = sum(int(item.get("recovered_execution_count", 0)) for item in attempts)
        score = retry_scheduled_count
        score += final_failure_count * 3
        score += non_retryable_failure_count * 2
        score += recovered_starts
        if latest.get("status") == "blocked":
            score += 4
        elif latest.get("status") in {"failed", "abandoned"}:
            score += 2
        if any(bool(item.get("protection_mode")) for item in attempts):
            score += 2
        if len(attempts) > 1:
            score += 1
        return score

    def _summarize_execution_request(self, request_id: str, attempts: list[dict[str, object]]) -> dict[str, object]:
        """把同一个 request 下的多次 execution attempt 压缩成一条摘要。"""
        ordered = sorted(attempts, key=lambda item: str(item.get("started_at", "")))
        latest = ordered[-1]
        failure_classes = self._failure_class_summary(ordered)
        retry_scheduled_count = len([item for item in ordered if item.get("retry_decision") == "retry_scheduled"])
        final_failure_count = len([item for item in ordered if item.get("retry_decision") == "final_failure"])
        non_retryable_failure_count = len(
            [
                item
                for item in ordered
                if item.get("status") == "failed" and not bool(item.get("retryable"))
            ]
        )
        anomaly_score = self._request_anomaly_score(ordered, latest)
        health_label = "healthy"
        if latest.get("status") in {"failed", "blocked"} or final_failure_count or non_retryable_failure_count:
            health_label = "critical"
        elif latest.get("status") == "abandoned" or retry_scheduled_count or any(
            bool(item.get("protection_mode")) for item in ordered
        ):
            health_label = "watch"
        return {
            "request_id": request_id,
            "symbol": latest["symbol"],
            "timeframe": latest["timeframe"],
            "attempt_count": len(ordered),
            "attempt_path": " -> ".join(str(item.get("status", "")) for item in ordered),
            "decision_path": " -> ".join(
                str(item.get("retry_decision", "")) for item in ordered if item.get("retry_decision")
            ),
            "final_status": latest["status"],
            "latest_execution_id": latest["execution_id"],
            "run_id": latest["run_id"],
            "retried": len(ordered) > 1,
            "blocked": latest["status"] == "blocked",
            "protection_mode_seen": any(bool(item.get("protection_mode")) for item in ordered),
            "cooldown_active": bool(
                latest.get("protection_mode") and str(latest.get("protection_cooldown_until", "")).strip()
            ),
            "protection_cooldown_until": str(latest.get("protection_cooldown_until", "") or ""),
            "requested_at": ordered[0]["requested_at"],
            "last_updated_at": latest["finished_at"] or latest["started_at"],
            "retry_scheduled_count": retry_scheduled_count,
            "final_failure_count": final_failure_count,
            "non_retryable_failure_count": non_retryable_failure_count,
            "failure_classes": failure_classes,
            "dominant_failure_class": failure_classes[0]["failure_class"] if failure_classes else "",
            "anomaly_score": anomaly_score,
            "health_label": health_label,
        }

    def create_execution(
        self,
        request_id: str,
        symbol: str,
        timeframe: str,
        initial_equity: float,
        recovered_execution_count: int = 0,
        protection_mode_failure_threshold: int = 2,
        protection_mode_cooldown_seconds: int = 0,
    ) -> str:
        """创建一条新的回测执行记录。

        `protection_mode_failure_threshold` 用来控制：
        同标的同周期在连续失败多少次后，下一次启动要被视作进入保护模式。
        """
        connection = connect_database(self.db_path)
        execution_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()
        try:
            attempt_row = connection.execute(
                """
                SELECT COALESCE(MAX(attempt_number), 0)
                FROM backtest_executions
                WHERE symbol = ? AND timeframe = ?
                """,
                (symbol, timeframe),
            ).fetchone()
            attempt_number = int(attempt_row[0]) + 1 if attempt_row else 1
            protection_state = self._protection_mode_state(
                connection,
                symbol,
                timeframe,
                protection_mode_failure_threshold=protection_mode_failure_threshold,
                protection_mode_cooldown_seconds=protection_mode_cooldown_seconds,
            )
            connection.execute(
                """
                INSERT INTO backtest_executions (
                    execution_id, request_id, symbol, timeframe, initial_equity, attempt_number,
                    recovered_execution_count, consecutive_failures_before_start,
                    protection_mode, protection_reason, protection_cooldown_until, status,
                    requested_at, started_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    request_id,
                    symbol,
                    timeframe,
                    initial_equity,
                    attempt_number,
                    recovered_execution_count,
                    protection_state["consecutive_failures"],
                    protection_state["protection_mode"],
                    protection_state["protection_reason"],
                    protection_state["protection_cooldown_until"],
                    "running",
                    started_at,
                    started_at,
                    "",
                ),
            )
            return execution_id
        finally:
            connection.close()

    def mark_execution_completed(self, execution_id: str, run_id: str) -> None:
        """把执行记录标记为完成，并挂上生成的 run_id。"""
        connection = connect_database(self.db_path)
        finished_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                UPDATE backtest_executions
                SET status = ?, finished_at = ?, run_id = ?, error_message = '',
                    retryable = 0, retry_decision = ?, failure_class = ''
                WHERE execution_id = ?
                """,
                ("completed", finished_at, run_id, "completed", execution_id),
            )
        finally:
            connection.close()

    def mark_execution_failed(
        self,
        execution_id: str,
        error_message: str,
        status: str = "failed",
        retryable: bool = False,
        retry_decision: str = "final_failure",
        failure_class: str = "",
    ) -> None:
        """把执行记录标记为失败或其它异常结束状态。"""
        connection = connect_database(self.db_path)
        finished_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                UPDATE backtest_executions
                SET status = ?, finished_at = ?, error_message = ?,
                    retryable = ?, retry_decision = ?, failure_class = ?
                WHERE execution_id = ?
                """,
                (
                    status,
                    finished_at,
                    error_message[:500],
                    1 if retryable else 0,
                    retry_decision,
                    failure_class[:120],
                    execution_id,
                ),
            )
        finally:
            connection.close()

    def mark_execution_blocked(self, execution_id: str, reason: str) -> None:
        """把执行记录标记为被保护模式拦截。

        单独保留这个语义化方法，是为了避免调用方到处手写 `status="blocked"`，
        让“失败”和“主动拦截”这两种不同结束原因更清楚。
        """
        self.mark_execution_failed(
            execution_id=execution_id,
            error_message=reason,
            status="blocked",
            retryable=False,
            retry_decision="blocked_protection_mode",
            failure_class="ProtectionMode",
        )

    def save_notification_event(
        self,
        *,
        severity: str,
        category: str,
        title: str,
        message: str,
        provider: str,
        delivery_status: str,
        delivery_target: str = "",
        delivery_attempts: int = 0,
        delivered_at: str = "",
        last_error: str = "",
        next_delivery_attempt_at: str = "",
        notification_key: str = "",
        silenced_until: str = "",
        suppressed_duplicate_count: int = 0,
        last_suppressed_at: str = "",
        acknowledged_at: str = "",
        acknowledged_note: str = "",
        symbol: str = "",
        timeframe: str = "",
        run_id: str = "",
        execution_id: str = "",
        request_id: str = "",
    ) -> str:
        """保存一条通知事件。

        这层记录的不是“系统内部日志”，而是“理论上应该通知外部世界的重要事件”。
        所以它天然适合后续做通知补发、失败重投和告警历史查询。
        """
        connection = connect_database(self.db_path)
        event_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        scheduled_next_attempt = next_delivery_attempt_at[:40]
        if not scheduled_next_attempt and delivery_status == "queued":
            # 新事件进入队列后，默认就应该立刻可投递，所以这里把“下一次可尝试时间”设成创建时刻。
            scheduled_next_attempt = created_at
        try:
            connection.execute(
                """
                INSERT INTO notification_events (
                    event_id, timestamp, severity, category, title, message,
                    provider, delivery_status, delivery_target, delivery_attempts, delivered_at, last_error, next_delivery_attempt_at,
                    notification_key, silenced_until, suppressed_duplicate_count, last_suppressed_at,
                    acknowledged_at, acknowledged_note,
                    symbol, timeframe, run_id, execution_id, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    created_at,
                    severity[:20],
                    category[:40],
                    title[:160],
                    message[:500],
                    provider[:40],
                    delivery_status[:40],
                    delivery_target[:300],
                    max(int(delivery_attempts), 0),
                    delivered_at[:40],
                    last_error[:500],
                    scheduled_next_attempt,
                    notification_key[:300],
                    silenced_until[:40],
                    max(int(suppressed_duplicate_count), 0),
                    last_suppressed_at[:40],
                    acknowledged_at[:40],
                    acknowledged_note[:500],
                    symbol[:40],
                    timeframe[:20],
                    run_id[:80],
                    execution_id[:80],
                    request_id[:80],
                ),
            )
            return event_id
        finally:
            connection.close()

    def fetch_recent_notification_events(self, limit: int = 20) -> list[dict[str, object]]:
        """查询最近产生的通知事件。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "notification_events" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT event_id, timestamp, severity, category, title, message, provider, delivery_status,
                       delivery_target, delivery_attempts, delivered_at, last_error, next_delivery_attempt_at,
                       notification_key, silenced_until, suppressed_duplicate_count, last_suppressed_at,
                       acknowledged_at, acknowledged_note,
                       symbol, timeframe, run_id, execution_id, request_id
                FROM notification_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "event_id": row[0],
                "timestamp": row[1],
                "severity": row[2],
                "category": row[3],
                "title": row[4],
                "message": row[5],
                "provider": row[6],
                "delivery_status": row[7],
                "delivery_target": row[8],
                "delivery_attempts": row[9],
                "delivered_at": row[10],
                "last_error": row[11],
                "next_delivery_attempt_at": row[12],
                "notification_key": row[13],
                "silenced_until": row[14],
                "suppressed_duplicate_count": row[15],
                "last_suppressed_at": row[16],
                "acknowledged_at": row[17],
                "acknowledged_note": row[18],
                "symbol": row[19],
                "timeframe": row[20],
                "run_id": row[21],
                "execution_id": row[22],
                "request_id": row[23],
            }
            for row in rows
        ]

    def fetch_active_notification_for_key(self, notification_key: str, current_time: str) -> dict[str, object] | None:
        """查找仍处于静默窗口内的同类通知。

        这里的目标不是做全局唯一约束，而是做“短时间内的降噪”：
        如果同一类告警刚刚发出过，就不再重复生成新事件，而是把计数压到已有事件上。
        """
        if not notification_key.strip():
            return None
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "notification_events" for table in tables):
                return None
            row = connection.execute(
                """
                SELECT event_id, timestamp, severity, category, title, message, provider, delivery_status,
                       delivery_target, delivery_attempts, delivered_at, last_error, next_delivery_attempt_at,
                       notification_key, silenced_until, suppressed_duplicate_count, last_suppressed_at,
                       acknowledged_at, acknowledged_note,
                       symbol, timeframe, run_id, execution_id, request_id
                FROM notification_events
                WHERE notification_key = ?
                  AND silenced_until >= ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (notification_key[:300], current_time[:40]),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return {
            "event_id": row[0],
            "timestamp": row[1],
            "severity": row[2],
            "category": row[3],
            "title": row[4],
            "message": row[5],
            "provider": row[6],
            "delivery_status": row[7],
            "delivery_target": row[8],
            "delivery_attempts": row[9],
            "delivered_at": row[10],
            "last_error": row[11],
            "next_delivery_attempt_at": row[12],
            "notification_key": row[13],
            "silenced_until": row[14],
            "suppressed_duplicate_count": row[15],
            "last_suppressed_at": row[16],
            "acknowledged_at": row[17],
            "acknowledged_note": row[18],
            "symbol": row[19],
            "timeframe": row[20],
            "run_id": row[21],
            "execution_id": row[22],
            "request_id": row[23],
        }

    def mark_notification_duplicate_suppressed(
        self,
        *,
        event_id: str,
        silenced_until: str,
        last_suppressed_at: str,
    ) -> None:
        """把重复告警压缩到已有通知事件上。

        这样 history 里仍然能看到“这类告警被压了多少次”，
        但不会因为每次重复都新插一行而把页面和 outbox 刷爆。
        """
        connection = connect_database(self.db_path)
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET silenced_until = ?,
                    last_suppressed_at = ?,
                    suppressed_duplicate_count = suppressed_duplicate_count + 1
                WHERE event_id = ?
                """,
                (
                    silenced_until[:40],
                    last_suppressed_at[:40],
                    event_id[:80],
                ),
            )
        finally:
            connection.close()

    def fetch_notifications_pending_delivery(self, limit: int = 20, max_delivery_attempts: int = 3) -> list[dict[str, object]]:
        """查询仍需要通知 worker 继续处理的事件。

        这里保留 `queued` 和 `delivery_failed_retryable` 两种状态：
        - `queued` 代表业务流程刚把事件放进待投递队列；
        - `delivery_failed_retryable` 代表 adapter 尝试过一次，但还没到最终放弃的门槛。
        """
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "notification_events" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT event_id, timestamp, severity, category, title, message, provider, delivery_status,
                       delivery_target, delivery_attempts, delivered_at, last_error, next_delivery_attempt_at,
                       notification_key, silenced_until, suppressed_duplicate_count, last_suppressed_at,
                       acknowledged_at, acknowledged_note,
                       symbol, timeframe, run_id, execution_id, request_id
                FROM notification_events
                WHERE delivery_status IN ('queued', 'delivery_failed_retryable')
                  AND delivery_attempts < ?
                  AND (next_delivery_attempt_at = '' OR next_delivery_attempt_at <= ?)
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (max(int(max_delivery_attempts), 1), datetime.now(UTC).isoformat(), limit),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "event_id": row[0],
                "timestamp": row[1],
                "severity": row[2],
                "category": row[3],
                "title": row[4],
                "message": row[5],
                "provider": row[6],
                "delivery_status": row[7],
                "delivery_target": row[8],
                "delivery_attempts": row[9],
                "delivered_at": row[10],
                "last_error": row[11],
                "next_delivery_attempt_at": row[12],
                "notification_key": row[13],
                "silenced_until": row[14],
                "suppressed_duplicate_count": row[15],
                "last_suppressed_at": row[16],
                "acknowledged_at": row[17],
                "acknowledged_note": row[18],
                "symbol": row[19],
                "timeframe": row[20],
                "run_id": row[21],
                "execution_id": row[22],
                "request_id": row[23],
            }
            for row in rows
        ]

    def acknowledge_notification_event(self, event_id: str, note: str = "") -> None:
        """把某条通知标记为已处理/已查看。"""
        connection = connect_database(self.db_path)
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET acknowledged_at = ?,
                    acknowledged_note = ?
                WHERE event_id = ?
                """,
                (
                    datetime.now(UTC).isoformat(),
                    note[:500],
                    event_id[:80],
                ),
            )
        finally:
            connection.close()

    def mark_notification_delivery_result(
        self,
        *,
        event_id: str,
        delivery_status: str,
        delivery_target: str = "",
        delivered_at: str = "",
        last_error: str = "",
        next_delivery_attempt_at: str = "",
        increment_attempts: bool = True,
    ) -> None:
        """记录通知 worker 的处理结果。

        这样设计后，业务流程只负责“把通知生出来”，而 worker 负责“把通知往前推进到下一状态”。
        两者职责分开，后续接真实 provider 时也更容易替换。
        """
        connection = connect_database(self.db_path)
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET delivery_status = ?,
                    delivery_target = ?,
                    delivered_at = ?,
                    last_error = ?,
                    next_delivery_attempt_at = ?,
                    delivery_attempts = delivery_attempts + ?
                WHERE event_id = ?
                """,
                (
                    delivery_status[:40],
                    delivery_target[:300],
                    delivered_at[:40],
                    last_error[:500],
                    next_delivery_attempt_at[:40],
                    1 if increment_attempts else 0,
                    event_id[:80],
                ),
            )
        finally:
            connection.close()

    def recover_stale_executions(self, symbol: str, timeframe: str) -> int:
        """把异常中断后残留的 running 记录修正为 abandoned。"""
        connection = connect_database(self.db_path)
        finished_at = datetime.now(UTC).isoformat()
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_executions" for table in tables):
                return 0
            rows = connection.execute(
                """
                SELECT execution_id
                FROM backtest_executions
                WHERE symbol = ? AND timeframe = ? AND status = ?
                """,
                (symbol, timeframe, "running"),
            ).fetchall()
            if not rows:
                return 0
            connection.execute(
                """
                UPDATE backtest_executions
                SET status = ?, finished_at = ?, error_message = ?
                WHERE symbol = ? AND timeframe = ? AND status = ?
                """,
                (
                    "abandoned",
                    finished_at,
                    "recovered after interrupted run",
                    symbol,
                    timeframe,
                    "running",
                ),
            )
            return len(rows)
        finally:
            connection.close()

    def save_run(self, symbol: str, timeframe: str, payload: dict[str, object]) -> str:
        """把一次完整回测的结果写入数据库。"""
        connection = connect_database(self.db_path)
        run_id = str(uuid4())
        metrics = payload["metrics"]
        orders = payload["orders"]
        audit_log = payload["audit_log"]
        started_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                INSERT INTO backtest_runs (
                    run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                    total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio,
                    total_trades, winning_trades, losing_trades, avg_trade_pnl, profit_factor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    symbol,
                    timeframe,
                    started_at,
                    payload["bars_processed"],
                    metrics["ending_equity"],
                    metrics["total_return_pct"],
                    metrics["max_drawdown_pct"],
                    metrics["sharpe_ratio"],
                    metrics["sortino_ratio"],
                    metrics["total_trades"],
                    metrics["winning_trades"],
                    metrics["losing_trades"],
                    metrics["avg_trade_pnl"],
                    metrics["profit_factor"],
                ),
            )
            if orders:
                # 订单事件保留的是过程细节，方便后续做生命周期分析。
                connection.executemany(
                    """
                    INSERT INTO order_events (
                        run_id, order_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                        broker_status, status_detail, requested_price, fill_price, commission, gross_value, net_value, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            order.get("order_id", ""),
                            order["timestamp"],
                            order["side"],
                            order["status"],
                            order["quantity"],
                            order.get("filled_quantity", 0),
                            order.get("remaining_quantity", 0),
                            order.get("broker_status", ""),
                            order.get("status_detail", ""),
                            order["requested_price"],
                            order["fill_price"],
                            order["commission"],
                            order.get("gross_value", 0.0),
                            order["net_value"],
                            order["reason"],
                        )
                        for order in orders
                    ],
                )
            if audit_log:
                # 审计日志保留“系统为什么这样做”的解释信息。
                connection.executemany(
                    """
                    INSERT INTO audit_events (
                        run_id, timestamp, event, signal, reason, risk_allowed
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            event["timestamp"],
                            event["event"],
                            event["signal"],
                            event["reason"],
                            event["risk_allowed"],
                        )
                        for event in audit_log
                    ],
                )
            # 账户快照记录最终现金、权益和盈亏，方便历史页回放运行结果。
            account = payload["account"]
            connection.execute(
                """
                INSERT INTO account_snapshots (
                    run_id, recorded_at, cash, equity, realized_pnl, unrealized_pnl, open_positions
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    started_at,
                    account["cash"],
                    account["equity"],
                    account["realized_pnl"],
                    account["unrealized_pnl"],
                    account["open_positions"],
                ),
            )
            return run_id
        finally:
            connection.close()

    def fetch_recent_runs(self, limit: int = 10) -> list[dict[str, object]]:
        """查询最近几次回测运行。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_runs" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                       total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio, total_trades
                FROM backtest_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()

        return [
            {
                "run_id": row[0],
                "symbol": row[1],
                "timeframe": row[2],
                "started_at": row[3],
                "bars_processed": row[4],
                "ending_equity": row[5],
                "total_return_pct": row[6],
                "max_drawdown_pct": row[7],
                "sharpe_ratio": row[8],
                "sortino_ratio": row[9],
                "total_trades": row[10],
            }
            for row in rows
        ]

    def fetch_recent_executions(self, limit: int = 10) -> list[dict[str, object]]:
        """查询最近几次执行尝试，包括失败与中断。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_executions" for table in tables):
                return []
            select_clause = self._execution_select_clause(connection)
            rows = connection.execute(
                f"""
                SELECT {select_clause}
                FROM backtest_executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [self._execution_row_to_dict(row) for row in rows]

    def fetch_execution_detail(self, execution_id: str) -> dict[str, object] | None:
        """查询某一次执行尝试的完整详情。

        这个接口主要服务两类场景：
        1. CLI 直接查看某次执行为什么失败、是不是保护模式启动；
        2. 后续历史页如果需要更深的 execution drill-down，也可以直接复用。
        """
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            table_names = {table[0] for table in tables}
            if "backtest_executions" not in table_names:
                return None
            select_clause = self._execution_select_clause(connection)
            execution_row = connection.execute(
                f"""
                SELECT {select_clause}
                FROM backtest_executions
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()
            if execution_row is None:
                return None
            run_row = None
            run_id = execution_row[18]
            if run_id and "backtest_runs" in table_names:
                run_row = connection.execute(
                    """
                    SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                           total_return_pct, sharpe_ratio, total_trades
                    FROM backtest_runs
                    WHERE run_id = ?
                    """,
                    (run_id,),
                ).fetchone()
        finally:
            connection.close()

        return {
            "execution": self._execution_row_to_dict(execution_row),
            "run": {
                "run_id": run_row[0],
                "symbol": run_row[1],
                "timeframe": run_row[2],
                "started_at": run_row[3],
                "bars_processed": run_row[4],
                "ending_equity": run_row[5],
                "total_return_pct": run_row[6],
                "sharpe_ratio": run_row[7],
                "total_trades": run_row[8],
            }
            if run_row
            else {"run_id": run_id} if run_id else None,
        }

    def fetch_execution_request_detail(self, request_id: str) -> dict[str, object] | None:
        """查询某一次外部回测请求对应的完整 execution attempt 链。

        这里的重点不是单个 execution，而是同一个 `request_id` 下：
        - 一共尝试了几次；
        - 每次尝试的状态如何；
        - 最终有没有落成 run。
        """
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            table_names = {table[0] for table in tables}
            if "backtest_executions" not in table_names:
                return None
            select_clause = self._execution_select_clause(connection)
            rows = connection.execute(
                f"""
                SELECT {select_clause}
                FROM backtest_executions
                WHERE request_id = ?
                ORDER BY started_at
                """,
                (request_id,),
            ).fetchall()
            if not rows:
                return None
        finally:
            connection.close()

        attempts = [self._execution_row_to_dict(row) for row in rows]
        return {
            "request": self._summarize_execution_request(request_id, attempts),
            "attempts": attempts,
        }

    def fetch_recent_execution_requests(self, limit: int = 10) -> list[dict[str, object]]:
        """查询最近几条 request 级执行链摘要。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_executions" for table in tables):
                return []
            select_clause = self._execution_select_clause(connection)
            rows = connection.execute(
                f"""
                SELECT {select_clause}
                FROM backtest_executions
                WHERE request_id != ''
                ORDER BY started_at DESC
                """
            ).fetchall()
        finally:
            connection.close()

        grouped: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            execution = self._execution_row_to_dict(row)
            request_id = str(execution["request_id"])
            grouped.setdefault(request_id, []).append(execution)

        summaries = [self._summarize_execution_request(request_id, attempts) for request_id, attempts in grouped.items()]
        summaries.sort(key=lambda item: str(item.get("last_updated_at", "")), reverse=True)
        return summaries[:limit]

    def fetch_protection_status(self, symbol: str, timeframe: str) -> dict[str, object]:
        """查询某个标的/周期当前的保护模式状态，而不需要触发新的回测。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_executions" for table in tables):
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "has_history": False,
                    "active": False,
                    "consecutive_failures": 0,
                    "latest_execution_id": "",
                    "latest_execution_status": "",
                    "latest_execution_at": "",
                    "latest_abnormal_execution_id": "",
                    "latest_abnormal_status": "",
                    "latest_abnormal_at": "",
                    "protection_reason": "",
                    "protection_cooldown_until": "",
                }
            latest_row = connection.execute(
                """
                SELECT execution_id, status, COALESCE(finished_at, started_at, '') AS reference_at,
                       protection_mode, protection_reason, protection_cooldown_until
                FROM backtest_executions
                WHERE symbol = ? AND timeframe = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (symbol, timeframe),
            ).fetchone()
            latest_abnormal = self._latest_abnormal_execution_reference(connection, symbol, timeframe)
            consecutive_failures = self._consecutive_failure_count(connection, symbol, timeframe)
        finally:
            connection.close()

        if latest_row is None:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "has_history": False,
                "active": False,
                "consecutive_failures": consecutive_failures,
                "latest_execution_id": "",
                "latest_execution_status": "",
                "latest_execution_at": "",
                "latest_abnormal_execution_id": "",
                "latest_abnormal_status": "",
                "latest_abnormal_at": "",
                "protection_reason": "",
                "protection_cooldown_until": "",
            }

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "has_history": True,
            "active": bool(latest_row[3]),
            "consecutive_failures": consecutive_failures,
            "latest_execution_id": str(latest_row[0] or ""),
            "latest_execution_status": str(latest_row[1] or ""),
            "latest_execution_at": str(latest_row[2] or ""),
            "latest_abnormal_execution_id": str(latest_abnormal["execution_id"]) if latest_abnormal else "",
            "latest_abnormal_status": str(latest_abnormal["status"]) if latest_abnormal else "",
            "latest_abnormal_at": str(latest_abnormal["reference_at"]) if latest_abnormal else "",
            "protection_reason": str(latest_row[4] or ""),
            "protection_cooldown_until": str(latest_row[5] or ""),
        }

    def fetch_run_detail(self, run_id: str) -> dict[str, object] | None:
        """查询某次回测的完整详情。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_runs" for table in tables):
                return None
            run_row = connection.execute(
                """
                SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                       total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio,
                       total_trades, winning_trades, losing_trades, avg_trade_pnl, profit_factor
                FROM backtest_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if run_row is None:
                return None

            order_rows = connection.execute(
                """
                SELECT order_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                       broker_status, status_detail, requested_price, fill_price, commission, gross_value, net_value, reason
                FROM order_events
                WHERE run_id = ?
                ORDER BY timestamp
                """,
                (run_id,),
            ).fetchall()
            audit_rows = connection.execute(
                """
                SELECT timestamp, event, signal, reason, risk_allowed
                FROM audit_events
                WHERE run_id = ?
                ORDER BY timestamp
                """,
                (run_id,),
            ).fetchall()
            snapshot_row = connection.execute(
                """
                SELECT recorded_at, cash, equity, realized_pnl, unrealized_pnl, open_positions
                FROM account_snapshots
                WHERE run_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        finally:
            connection.close()

        # 先把原始订单事件标准化成字典，再往上构建生命周期摘要。
        orders = [
            {
                "order_id": row[0],
                "timestamp": row[1],
                "side": row[2],
                "status": row[3],
                "quantity": row[4],
                "filled_quantity": row[5],
                "remaining_quantity": row[6],
                "broker_status": row[7],
                "status_detail": row[8],
                "requested_price": row[9],
                "fill_price": row[10],
                "commission": row[11],
                "gross_value": row[12],
                "net_value": row[13],
                "reason": row[14],
            }
            for row in order_rows
        ]

        return {
            "run": {
                "run_id": run_row[0],
                "symbol": run_row[1],
                "timeframe": run_row[2],
                "started_at": run_row[3],
                "bars_processed": run_row[4],
                "ending_equity": run_row[5],
                "total_return_pct": run_row[6],
                "max_drawdown_pct": run_row[7],
                "sharpe_ratio": run_row[8],
                "sortino_ratio": run_row[9],
                "total_trades": run_row[10],
                "winning_trades": run_row[11],
                "losing_trades": run_row[12],
                "avg_trade_pnl": run_row[13],
                "profit_factor": run_row[14],
            },
            "orders": orders,
            "order_lifecycles": self._build_order_lifecycles(orders),
            "audit_log": [
                {
                    "timestamp": row[0],
                    "event": row[1],
                    "signal": row[2],
                    "reason": row[3],
                    "risk_allowed": row[4],
                }
                for row in audit_rows
            ],
            "account_snapshot": {
                "recorded_at": snapshot_row[0],
                "cash": snapshot_row[1],
                "equity": snapshot_row[2],
                "realized_pnl": snapshot_row[3],
                "unrealized_pnl": snapshot_row[4],
                "open_positions": snapshot_row[5],
            }
            if snapshot_row
            else {
                "recorded_at": run_row[3],
                "cash": run_row[5],
                "equity": run_row[5],
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "open_positions": 0,
            },
        }

    def fetch_order_detail(self, order_id: str) -> dict[str, object] | None:
        """查询某一笔订单的完整事件流和所属运行信息。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            table_names = {table[0] for table in tables}
            if "order_events" not in table_names:
                return None
            order_rows = connection.execute(
                """
                SELECT run_id, order_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                       broker_status, status_detail, requested_price, fill_price, commission, gross_value, net_value, reason
                FROM order_events
                WHERE order_id = ?
                ORDER BY timestamp
                """,
                (order_id,),
            ).fetchall()
            if not order_rows:
                return None
            run_id = order_rows[0][0]
            run_row = None
            if "backtest_runs" in table_names:
                run_row = connection.execute(
                    """
                    SELECT run_id, symbol, timeframe, started_at
                    FROM backtest_runs
                    WHERE run_id = ?
                    """,
                    (run_id,),
                ).fetchone()
        finally:
            connection.close()

        events = [
            {
                "run_id": row[0],
                "order_id": row[1],
                "timestamp": row[2],
                "side": row[3],
                "status": row[4],
                "quantity": row[5],
                "filled_quantity": row[6],
                "remaining_quantity": row[7],
                "broker_status": row[8],
                "status_detail": row[9],
                "requested_price": row[10],
                "fill_price": row[11],
                "commission": row[12],
                "gross_value": row[13],
                "net_value": row[14],
                "reason": row[15],
            }
            for row in order_rows
        ]
        lifecycles = self._build_order_lifecycles(events)
        lifecycle = lifecycles[0] if lifecycles else {}
        return {
            "order": lifecycle,
            "events": events,
            "run": {
                "run_id": run_row[0],
                "symbol": run_row[1],
                "timeframe": run_row[2],
                "started_at": run_row[3],
            }
            if run_row
            else {"run_id": run_id},
        }

    def fetch_recent_order_events(self, limit: int = 20) -> list[dict[str, object]]:
        """查询最近的订单事件。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "order_events" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT run_id, order_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                       broker_status, status_detail, fill_price, commission, reason
                FROM order_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "run_id": row[0],
                "order_id": row[1],
                "timestamp": row[2],
                "side": row[3],
                "status": row[4],
                "quantity": row[5],
                "filled_quantity": row[6],
                "remaining_quantity": row[7],
                "broker_status": row[8],
                "status_detail": row[9],
                "fill_price": row[10],
                "commission": row[11],
                "reason": row[12],
            }
            for row in rows
        ]

    def fetch_recent_audit_events(self, limit: int = 20) -> list[dict[str, object]]:
        """查询最近的审计事件。"""
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "audit_events" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT run_id, timestamp, event, signal, reason, risk_allowed
                FROM audit_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "run_id": row[0],
                "timestamp": row[1],
                "event": row[2],
                "signal": row[3],
                "reason": row[4],
                "risk_allowed": row[5],
            }
            for row in rows
        ]

    def fetch_history_bundle(self, runs_limit: int = 20, events_limit: int = 20) -> dict[str, list[dict[str, object]]]:
        """一次性取回历史页面需要的 runs / executions / orders / audit / notifications 五组数据。

        之所以把 execution 单独带出来，是因为“运行有没有成功”与“订单后来发生了什么”
        属于两个不同层级的问题。历史页需要同时看到这两层，排错才完整。
        """
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            table_names = {table[0] for table in tables}
            runs: list[dict[str, object]] = []
            executions: list[dict[str, object]] = []
            orders: list[dict[str, object]] = []
            audit_events: list[dict[str, object]] = []
            notification_events: list[dict[str, object]] = []

            if "backtest_runs" in table_names:
                run_rows = connection.execute(
                    """
                    SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                           total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio, total_trades
                    FROM backtest_runs
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (runs_limit,),
                ).fetchall()
                runs = [
                    {
                        "run_id": row[0],
                        "symbol": row[1],
                        "timeframe": row[2],
                        "started_at": row[3],
                        "bars_processed": row[4],
                        "ending_equity": row[5],
                        "total_return_pct": row[6],
                        "max_drawdown_pct": row[7],
                        "sharpe_ratio": row[8],
                        "sortino_ratio": row[9],
                        "total_trades": row[10],
                    }
                    for row in run_rows
                ]

            if "backtest_executions" in table_names:
                select_clause = self._execution_select_clause(connection)
                execution_rows = connection.execute(
                    f"""
                    SELECT {select_clause}
                    FROM backtest_executions
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (events_limit,),
                ).fetchall()
                executions = [self._execution_row_to_dict(row) for row in execution_rows]

            if "order_events" in table_names:
                order_rows = connection.execute(
                """
                    SELECT run_id, order_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                           broker_status, status_detail, fill_price, commission, reason
                    FROM order_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (events_limit,),
                ).fetchall()
                orders = [
                    {
                        "run_id": row[0],
                        "order_id": row[1],
                        "timestamp": row[2],
                        "side": row[3],
                        "status": row[4],
                        "quantity": row[5],
                        "filled_quantity": row[6],
                        "remaining_quantity": row[7],
                        "broker_status": row[8],
                        "status_detail": row[9],
                        "fill_price": row[10],
                        "commission": row[11],
                        "reason": row[12],
                    }
                    for row in order_rows
                ]

            if "audit_events" in table_names:
                audit_rows = connection.execute(
                    """
                    SELECT run_id, timestamp, event, signal, reason, risk_allowed
                    FROM audit_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (events_limit,),
                ).fetchall()
                audit_events = [
                    {
                        "run_id": row[0],
                        "timestamp": row[1],
                        "event": row[2],
                        "signal": row[3],
                        "reason": row[4],
                        "risk_allowed": row[5],
                    }
                    for row in audit_rows
                ]
            if "notification_events" in table_names:
                notification_rows = connection.execute(
                    """
                    SELECT event_id, timestamp, severity, category, title, message, provider, delivery_status,
                           delivery_target, delivery_attempts, delivered_at, last_error, next_delivery_attempt_at,
                           notification_key, silenced_until, suppressed_duplicate_count, last_suppressed_at,
                           acknowledged_at, acknowledged_note,
                           symbol, timeframe, run_id, execution_id, request_id
                    FROM notification_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (events_limit,),
                ).fetchall()
                notification_events = [
                    {
                        "event_id": row[0],
                        "timestamp": row[1],
                        "severity": row[2],
                        "category": row[3],
                        "title": row[4],
                        "message": row[5],
                        "provider": row[6],
                        "delivery_status": row[7],
                        "delivery_target": row[8],
                        "delivery_attempts": row[9],
                        "delivered_at": row[10],
                        "last_error": row[11],
                        "next_delivery_attempt_at": row[12],
                        "notification_key": row[13],
                        "silenced_until": row[14],
                        "suppressed_duplicate_count": row[15],
                        "last_suppressed_at": row[16],
                        "acknowledged_at": row[17],
                        "acknowledged_note": row[18],
                        "symbol": row[19],
                        "timeframe": row[20],
                        "run_id": row[21],
                        "execution_id": row[22],
                        "request_id": row[23],
                    }
                    for row in notification_rows
                ]
        finally:
            connection.close()

        return {
            "runs": runs,
            "executions": executions,
            "orders": orders,
            "audit_events": audit_events,
            "notification_events": notification_events,
        }

    @staticmethod
    def _build_order_lifecycles(order_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        """把散落的订单事件按 `order_id` 归并成生命周期摘要。"""
        grouped: dict[str, list[dict[str, object]]] = {}
        for row in order_rows:
            order_id = str(row.get("order_id", ""))
            grouped.setdefault(order_id, []).append(row)

        lifecycles: list[dict[str, object]] = []
        for order_id, events in grouped.items():
            # status_path 用来回答最关键的问题：
            # “这张单从创建到结束，完整经历了哪些状态？”
            statuses = [str(event.get("status", "")) for event in events]
            first_event = events[0]
            last_event = events[-1]
            lifecycles.append(
                {
                    "order_id": order_id,
                    "side": first_event.get("side", ""),
                    "submitted_at": first_event.get("timestamp", ""),
                    "last_updated_at": last_event.get("timestamp", ""),
                    "event_count": len(events),
                    "status_path": statuses,
                    "broker_status_path": [str(event.get("broker_status", "")) for event in events],
                    "final_status": last_event.get("status", ""),
                    "latest_broker_status": last_event.get("broker_status", ""),
                    "latest_status_detail": last_event.get("status_detail", ""),
                    "requested_quantity": first_event.get("quantity", 0),
                    "filled_quantity": max(int(event.get("filled_quantity", 0)) for event in events),
                    "remaining_quantity": last_event.get("remaining_quantity", 0),
                    "latest_requested_price": last_event.get("requested_price", 0.0),
                    "latest_fill_price": last_event.get("fill_price", 0.0),
                    "final_reason": last_event.get("reason", ""),
                }
            )
        lifecycles.sort(key=lambda item: str(item.get("submitted_at", "")))
        return lifecycles
