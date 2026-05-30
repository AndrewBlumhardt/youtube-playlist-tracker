from __future__ import annotations

import json
import random
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
        return {
            "saved_playlist_ids": [],
            "saved_channels": [],
            "last_channel_input": "",
            "last_playlist_input": "",
            "save_snapshot_default": False,
            "last_history_playlist_id": "",
            "last_discovered_playlists": [],
            "show_discovery_history": False,
        }

    try:
        content = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "saved_playlist_ids": [],
            "saved_channels": [],
            "last_channel_input": "",
            "last_playlist_input": "",
            "save_snapshot_default": False,
            "last_history_playlist_id": "",
            "last_discovered_playlists": [],
            "show_discovery_history": False,
        }

    playlist_ids = content.get("saved_playlist_ids", [])
    if not isinstance(playlist_ids, list):
        playlist_ids = []
    saved_channels = content.get("saved_channels", [])
    if not isinstance(saved_channels, list):
        saved_channels = []
    return {
        "saved_playlist_ids": [str(item) for item in playlist_ids],
        "saved_channels": [str(item) for item in saved_channels if str(item).strip()],
        "last_channel_input": str(content.get("last_channel_input", "") or ""),
        "last_playlist_input": str(content.get("last_playlist_input", "") or ""),
        "save_snapshot_default": bool(content.get("save_snapshot_default", False)),
        "last_history_playlist_id": str(content.get("last_history_playlist_id", "") or ""),
        "last_discovered_playlists": content.get("last_discovered_playlists", []) if isinstance(content.get("last_discovered_playlists", []), list) else [],
        "show_discovery_history": bool(content.get("show_discovery_history", False)),
    }


def save_user_config(saved_playlist_ids: List[str]) -> None:
    _ensure_data_dir()
    payload = load_user_config()
    payload["saved_playlist_ids"] = sorted(set(saved_playlist_ids))
    CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_user_preferences(
    *,
    saved_playlist_ids: List[str] | None = None,
    last_channel_input: str | None = None,
    last_playlist_input: str | None = None,
    save_snapshot_default: bool | None = None,
    last_history_playlist_id: str | None = None,
    last_discovered_playlists: List[Dict] | None = None,
    show_discovery_history: bool | None = None,
    saved_channels: List[str] | None = None,
) -> None:
    _ensure_data_dir()
    payload = load_user_config()

    if saved_playlist_ids is not None:
        payload["saved_playlist_ids"] = sorted(set(saved_playlist_ids))
    if last_channel_input is not None:
        payload["last_channel_input"] = last_channel_input.strip()
    if last_playlist_input is not None:
        payload["last_playlist_input"] = last_playlist_input.strip()
    if save_snapshot_default is not None:
        payload["save_snapshot_default"] = bool(save_snapshot_default)
    if last_history_playlist_id is not None:
        payload["last_history_playlist_id"] = last_history_playlist_id.strip()
    if last_discovered_playlists is not None:
        payload["last_discovered_playlists"] = last_discovered_playlists
    if show_discovery_history is not None:
        payload["show_discovery_history"] = bool(show_discovery_history)
    if saved_channels is not None:
        cleaned = sorted({str(item).strip() for item in saved_channels if str(item).strip()})
        payload["saved_channels"] = cleaned

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
                "data_source": "actual",
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

    df = pd.DataFrame(records)
    if "data_source" not in df.columns:
        df["data_source"] = "actual"
    else:
        df["data_source"] = df["data_source"].fillna("actual")
    return df


def _write_snapshot_history(df: pd.DataFrame) -> None:
    _ensure_data_dir()
    if df.empty:
        SNAPSHOT_FILE.write_text("", encoding="utf-8")
        return

    with SNAPSHOT_FILE.open("w", encoding="utf-8") as handle:
        for _, row in df.iterrows():
            record = {}
            for key, value in row.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, pd.Timestamp):
                    record[key] = value.isoformat()
                else:
                    record[key] = value
            handle.write(json.dumps(record) + "\n")


def _estimated_series(current_value: int, periods: int, rng: random.Random) -> List[int]:
    if periods <= 0:
        return []
    if current_value <= 0:
        return [0] * periods

    # Build monotonic pre-actual values that lead up to the latest observed metric.
    weights = [rng.random() + 0.2 for _ in range(periods + 1)]
    total_weight = sum(weights)
    running = 0.0
    values: List[int] = []
    for index in range(periods):
        running += weights[index]
        value = int((running / total_weight) * current_value)
        if values and value < values[-1]:
            value = values[-1]
        if value >= current_value:
            value = max(0, current_value - 1)
        values.append(value)
    return values


def _safe_int(value: object) -> int:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return 0
    return int(parsed)


def estimate_playlist_history(playlist_id: str, months_back: int = 12) -> Dict[str, int]:
    """Backfill estimated monthly history for a playlist, labeled as estimated."""
    history_df = load_snapshot_history()
    if history_df.empty:
        return {"estimated_rows": 0, "videos": 0, "months": months_back}

    history_df["snapshot_time"] = pd.to_datetime(history_df["snapshot_time"], errors="coerce", utc=True)
    history_df = history_df.dropna(subset=["snapshot_time"]).copy()

    playlist_df = history_df[history_df["playlist_id"] == playlist_id].copy()
    actual_df = playlist_df[playlist_df["data_source"] == "actual"].copy()
    if actual_df.empty:
        return {"estimated_rows": 0, "videos": 0, "months": months_back}

    latest_snapshot_time = actual_df["snapshot_time"].max()
    latest_rows = actual_df[actual_df["snapshot_time"] == latest_snapshot_time].copy()
    latest_rows = latest_rows.drop_duplicates(subset=["video_id"], keep="first")

    estimate_dates = [latest_snapshot_time - pd.DateOffset(months=offset) for offset in range(months_back, 0, -1)]
    estimated_records = []

    for _, row in latest_rows.iterrows():
        video_id = str(row.get("video_id", ""))
        seed_base = abs(hash(f"{playlist_id}:{video_id}")) % (2**32)
        view_rng = random.Random(seed_base)
        like_rng = random.Random(seed_base + 101)
        comment_rng = random.Random(seed_base + 202)

        view_series = _estimated_series(_safe_int(row.get("view_count", 0)), months_back, view_rng)
        like_series = _estimated_series(_safe_int(row.get("like_count", 0)), months_back, like_rng)
        comment_series = _estimated_series(_safe_int(row.get("comment_count", 0)), months_back, comment_rng)

        for index, estimate_time in enumerate(estimate_dates):
            estimated_records.append(
                {
                    "snapshot_time": estimate_time.isoformat(),
                    "data_source": "estimated",
                    "playlist_id": row.get("playlist_id", playlist_id),
                    "playlist_title": row.get("playlist_title", ""),
                    "video_id": row.get("video_id", ""),
                    "title": row.get("title", ""),
                    "channel_title": row.get("channel_title", ""),
                    "published_at": row.get("published_at", ""),
                    "view_count": view_series[index],
                    "like_count": like_series[index],
                    "comment_count": comment_series[index],
                }
            )

    non_estimated_or_other = history_df[
        (history_df["playlist_id"] != playlist_id) | (history_df["data_source"] != "estimated")
    ].copy()
    non_estimated_or_other["snapshot_time"] = pd.to_datetime(
        non_estimated_or_other["snapshot_time"], errors="coerce", utc=True
    )
    estimated_df = pd.DataFrame(estimated_records)
    if not estimated_df.empty:
        estimated_df["snapshot_time"] = pd.to_datetime(
            estimated_df["snapshot_time"], errors="coerce", utc=True
        )
    refreshed_df = pd.concat([non_estimated_or_other, estimated_df], ignore_index=True)
    refreshed_df = refreshed_df.sort_values("snapshot_time", ascending=True)
    _write_snapshot_history(refreshed_df)

    return {
        "estimated_rows": len(estimated_records),
        "videos": len(latest_rows),
        "months": months_back,
    }
