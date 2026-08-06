import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


DEFAULT_DB_PATH = Path("data/market-pulse.sqlite3")


def database_path() -> Path:
    return Path(os.getenv("MARKET_DB_PATH", DEFAULT_DB_PATH))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS snapshot_captured_at_idx
                ON market_snapshots(captured_at DESC);
            CREATE TABLE IF NOT EXISTS minute_bars (
                captured_at TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                change_pct REAL NOT NULL,
                amount REAL NOT NULL,
                turnover REAL NOT NULL,
                industry TEXT NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (captured_at, code)
            );
            CREATE INDEX IF NOT EXISTS minute_bars_code_time_idx
                ON minute_bars(code, captured_at DESC);
            CREATE TABLE IF NOT EXISTS daily_bars (
                code TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                amount REAL NOT NULL,
                change_pct REAL NOT NULL,
                turnover REAL NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (code, trading_date)
            );
            CREATE INDEX IF NOT EXISTS daily_bars_code_date_idx
                ON daily_bars(code, trading_date DESC);
            CREATE TABLE IF NOT EXISTS signal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                triggered_at TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                rule_version TEXT NOT NULL DEFAULT 'legacy',
                score INTEGER NOT NULL,
                evidence TEXT NOT NULL,
                risk TEXT NOT NULL,
                source TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS signal_events_code_time_idx
                ON signal_events(code, triggered_at DESC);
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS analysis_runs_kind_time_idx
                ON analysis_runs(kind, generated_at DESC);
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(signal_events)")}
        if "rule_version" not in columns:
            connection.execute("ALTER TABLE signal_events ADD COLUMN rule_version TEXT NOT NULL DEFAULT 'legacy'")


def save_snapshot(snapshot: dict, bars: list[dict] | None = None) -> None:
    initialize()
    with connect() as connection:
        connection.execute(
            "INSERT INTO market_snapshots (captured_at, source, payload) VALUES (?, ?, ?)",
            (snapshot["as_of"], snapshot["source"], json.dumps(snapshot, ensure_ascii=False)),
        )
        if bars:
            connection.executemany(
                """
                INSERT OR REPLACE INTO minute_bars
                (captured_at, code, name, price, change_pct, amount, turnover, industry, source)
                VALUES (:captured_at, :code, :name, :price, :change_pct, :amount, :turnover, :industry, :source)
                """,
                bars,
            )


def latest_snapshot(max_age_seconds: int | None = None) -> dict | None:
    initialize()
    with connect() as connection:
        row = connection.execute(
            "SELECT captured_at, payload FROM market_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    captured_at = datetime.fromisoformat(row["captured_at"])
    if max_age_seconds is not None:
        now = datetime.now(timezone.utc)
        normalized_captured_at = captured_at.astimezone(timezone.utc)
        if normalized_captured_at < now - timedelta(seconds=max_age_seconds):
            return None
    return json.loads(row["payload"])


def recent_bars(code: str, limit: int = 240) -> list[dict]:
    initialize()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT captured_at, code, name, price, change_pct, amount, turnover, industry, source
            FROM minute_bars WHERE code = ? ORDER BY captured_at DESC LIMIT ?
            """,
            (code, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def snapshot_bars(captured_at: str) -> list[dict]:
    initialize()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT captured_at, code, name, price, change_pct, amount, turnover, industry, source
            FROM minute_bars WHERE captured_at = ? ORDER BY code
            """,
            (captured_at,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_daily_bars(bars: list[dict]) -> None:
    if not bars:
        return
    initialize()
    with connect() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO daily_bars
            (code, trading_date, open, high, low, close, volume, amount, change_pct, turnover, source)
            VALUES (:code, :trading_date, :open, :high, :low, :close, :volume, :amount, :change_pct, :turnover, :source)
            """,
            bars,
        )


def recent_daily_bars(code: str, limit: int = 250) -> list[dict]:
    initialize()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT code, trading_date, open, high, low, close, volume, amount, change_pct, turnover, source
            FROM daily_bars WHERE code = ? ORDER BY trading_date DESC LIMIT ?
            """,
            (code, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def daily_histories_for_codes(codes: list[str], limit: int = 60) -> dict[str, list[dict]]:
    """Load only locally available daily history for the requested symbols."""
    if not codes:
        return {}
    initialize()
    unique_codes = list(dict.fromkeys(codes))
    histories: dict[str, list[dict]] = {}
    # SQLite limits bound parameters, so query codes in conservative chunks.
    with connect() as connection:
        for start in range(0, len(unique_codes), 800):
            chunk = unique_codes[start:start + 800]
            placeholders = ", ".join("?" for _ in chunk)
            rows = connection.execute(
                f"""
                SELECT code, trading_date, open, high, low, close, volume, amount, change_pct, turnover, source
                FROM daily_bars WHERE code IN ({placeholders})
                ORDER BY code, trading_date DESC
                """,
                chunk,
            ).fetchall()
            grouped: dict[str, list[dict]] = {}
            for row in rows:
                grouped.setdefault(row["code"], []).append(dict(row))
            for code, newest_first in grouped.items():
                histories[code] = list(reversed(newest_first[:limit]))
    return histories


def recent_signal_events(limit: int = 100) -> list[dict]:
    initialize()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT triggered_at, code, name, rule_name, rule_version, score, evidence, risk, source
            FROM signal_events ORDER BY triggered_at DESC, score DESC, id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_analysis(kind: str, payload: dict, generated_at: str | None = None) -> None:
    """Persist the latest bounded model output for the desktop UI."""
    initialize()
    captured_at = generated_at or datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute(
            "INSERT INTO analysis_runs (kind, generated_at, payload) VALUES (?, ?, ?)",
            (kind, captured_at, json.dumps(payload, ensure_ascii=False)),
        )
        connection.execute(
            """
            DELETE FROM analysis_runs
            WHERE kind = ? AND id NOT IN (
                SELECT id FROM analysis_runs WHERE kind = ? ORDER BY generated_at DESC LIMIT 8
            )
            """,
            (kind, kind),
        )


def latest_analysis(kind: str) -> dict | None:
    initialize()
    with connect() as connection:
        row = connection.execute(
            "SELECT generated_at, payload FROM analysis_runs WHERE kind = ? ORDER BY generated_at DESC, id DESC LIMIT 1",
            (kind,),
        ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload"])
    payload["generated_at"] = row["generated_at"]
    return payload


def record_rule_events(signals: list[dict], cooldown_minutes: int = 30) -> int:
    """Persist versioned rule outputs with code/rule cooldown deduplication."""
    initialize()
    inserted = 0
    with connect() as connection:
        for signal in signals:
            triggered_at = datetime.fromisoformat(signal["triggered_at"])
            existing = connection.execute(
                """
                SELECT triggered_at FROM signal_events
                WHERE code = ? AND rule_name = ? AND rule_version = ?
                ORDER BY id DESC LIMIT 1
                """,
                (signal["code"], signal["rule_name"], signal["rule_version"]),
            ).fetchone()
            if existing is not None:
                previous = datetime.fromisoformat(existing["triggered_at"])
                if triggered_at - previous <= timedelta(minutes=cooldown_minutes):
                    continue
            connection.execute(
                """
                INSERT INTO signal_events
                (triggered_at, code, name, rule_name, rule_version, score, evidence, risk, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal["triggered_at"], signal["code"], signal["name"], signal["rule_name"],
                    signal["rule_version"], signal["score"], signal["evidence"], signal["risk"], signal["source"],
                ),
            )
            inserted += 1
    return inserted


def record_signal_events(snapshot: dict, cooldown_minutes: int = 30) -> int:
    """Store actionable signals once per code/rule within the cooldown window."""
    initialize()
    triggered_at = datetime.fromisoformat(snapshot["as_of"])
    inserted = 0
    with connect() as connection:
        for mover in snapshot["movers"]:
            existing = connection.execute(
                """
                SELECT triggered_at FROM signal_events
                WHERE code = ? AND rule_name = ?
                ORDER BY id DESC LIMIT 1
                """,
                (mover["code"], mover["signal"]),
            ).fetchone()
            if existing is not None:
                previous = datetime.fromisoformat(existing["triggered_at"])
                if triggered_at - previous <= timedelta(minutes=cooldown_minutes):
                    continue
            connection.execute(
                """
                INSERT INTO signal_events
                (triggered_at, code, name, rule_name, score, evidence, risk, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot["as_of"], mover["code"], mover["name"], mover["signal"],
                    mover["score"], mover["note"], mover["risk"], snapshot["source"],
                ),
            )
            inserted += 1
    return inserted
