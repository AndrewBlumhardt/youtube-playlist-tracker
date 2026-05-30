from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd


DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "user_config.json"
SNAPSHOT_FILE = DATA_DIR / "snapshots.jsonl"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_user_config() -> Dict:
    _ensure_data_dir()
    if not CONFIG_FILE.exists():
        return {"saved_playlist_ids": []}

    try:
        content = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"saved_playlist_ids": []}

    playlist_ids = content.get("saved_playlist_ids", [])
    if not isinstance(playlist_ids, list):
        playlist_ids = []
    return {"saved_playlist_ids": [str(item) for item in playlist_ids]}


def save_user_config(saved_playlist_ids: List[str]) -> None:
    _ensure_data_dir()
    payload = {"saved_playlist_ids": sorted(set(saved_playlist_ids))}
    CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_snapshot(playlist_id: str, playlist_title: str, df: pd.DataFrame) -> str:
    """Persist a point-in-time snapshot of all rows for one playlist."""
    _ensure_data_dir()
    snapshot_time = datetime.now(timezone.utc).isoformat()

    rows = df.to_dict(orient="records")
    with SNAPSHOT_FILE.open("a", encoding="utf-8") as handle:
        for row in rows:
            record = {
                "snapshot_time": snapshot_time,
                "playlist_id": playlist_id,
                "playlist_title": playlist_title,
                **row,
            }
            handle.write(json.dumps(record) + "\n")

    return snapshot_time


def load_snapshot_history() -> pd.DataFrame:
    _ensure_data_dir()
    if not SNAPSHOT_FILE.exists():
        return pd.DataFrame()

    records = []
    with SNAPSHOT_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError:
                continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)
