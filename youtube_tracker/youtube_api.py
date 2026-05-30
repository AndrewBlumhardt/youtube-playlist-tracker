from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests


BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeApiError(RuntimeError):
    """Raised when YouTube Data API calls fail."""


def extract_channel_reference(value: str) -> Tuple[str, str]:
    """Parse channel input into ('channel_id'|'handle'|'query', value)."""
    value = (value or "").strip()
    if not value:
        return ("", "")

    channel_match = re.match(r"^UC[A-Za-z0-9_-]{20,}$", value)
    if channel_match:
        return ("channel_id", value)

    handle_match = re.match(r"^@?[A-Za-z0-9._-]{3,}$", value)
    if handle_match and value.startswith("@"):
        return ("handle", value.lstrip("@"))

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        path = parsed.path.strip("/")
        if path.startswith("channel/"):
            channel_id = path.split("/", 1)[1]
            if channel_id:
                return ("channel_id", channel_id)
        if path.startswith("@"):
            return ("handle", path.lstrip("@"))

    return ("query", value)


def extract_playlist_id(value: str) -> str:
    """Accept either a playlist URL or raw playlist ID and return a playlist ID."""
    value = (value or "").strip()
    if not value:
        return ""

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        query = parse_qs(parsed.query)
        playlist_ids = query.get("list", [])
        return playlist_ids[0] if playlist_ids else ""

    # YouTube playlist IDs usually start with PL, UU, LL, FL, OLAK5uy_.
    if re.match(r"^(PL|UU|LL|FL|RD|OLAK5uy_)[A-Za-z0-9_-]+$", value):
        return value

    return ""


def _get(endpoint: str, params: Dict[str, str]) -> Dict:
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    if response.status_code != 200:
        detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise YouTubeApiError(f"HTTP {response.status_code}: {detail}")
    payload = response.json()
    if "error" in payload:
        raise YouTubeApiError(str(payload["error"]))
    return payload


def _iter_playlist_video_ids(api_key: str, playlist_id: str) -> Iterable[str]:
    next_page_token = ""

    while True:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": "50",
            "key": api_key,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        payload = _get("playlistItems", params)
        for item in payload.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                yield video_id

        next_page_token = payload.get("nextPageToken", "")
        if not next_page_token:
            break


def _chunks(values: List[str], chunk_size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]


def discover_channel_playlists(api_key: str, channel_input: str) -> List[Dict[str, str]]:
    """Discover public playlists from a channel ID, handle, URL, or search query."""
    ref_type, ref_value = extract_channel_reference(channel_input)
    if not ref_value:
        raise YouTubeApiError("Please provide a channel URL, handle, or channel ID.")

    channel_id = ""
    if ref_type == "channel_id":
        channel_id = ref_value
    elif ref_type == "handle":
        payload = _get(
            "channels",
            {
                "part": "id",
                "forHandle": ref_value,
                "maxResults": "1",
                "key": api_key,
            },
        )
        items = payload.get("items", [])
        if items:
            channel_id = items[0].get("id", "")
    elif ref_type == "query":
        search_payload = _get(
            "search",
            {
                "part": "snippet",
                "type": "channel",
                "q": ref_value,
                "maxResults": "1",
                "key": api_key,
            },
        )
        items = search_payload.get("items", [])
        if items:
            channel_id = items[0].get("snippet", {}).get("channelId", "")

    if not channel_id:
        raise YouTubeApiError("Unable to resolve channel. Try a full channel URL or channel ID.")

    next_page_token = ""
    playlists: List[Dict[str, str]] = []
    while True:
        params = {
            "part": "snippet,contentDetails",
            "channelId": channel_id,
            "maxResults": "50",
            "key": api_key,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        payload = _get("playlists", params)
        for item in payload.get("items", []):
            playlists.append(
                {
                    "playlist_id": item.get("id", ""),
                    "title": item.get("snippet", {}).get("title", ""),
                    "video_count": str(item.get("contentDetails", {}).get("itemCount", 0)),
                }
            )

        next_page_token = payload.get("nextPageToken", "")
        if not next_page_token:
            break

    playlists = [item for item in playlists if item.get("playlist_id")]
    playlists.sort(key=lambda item: item.get("title", "").lower())
    return playlists


def verify_api_key(api_key: str) -> Tuple[bool, str]:
    """Validate API key by making a lightweight YouTube Data API request."""
    try:
        _get(
            "videoCategories",
            {
                "part": "snippet",
                "regionCode": "US",
                "maxResults": "1",
                "key": api_key,
            },
        )
        return (True, "API key is valid.")
    except YouTubeApiError as exc:
        return (False, f"API key check failed: {exc}")


def fetch_playlist_videos_with_stats(api_key: str, playlist_id: str) -> pd.DataFrame:
    """Fetch playlist video metadata + statistics and return a dataframe."""
    video_ids = list(_iter_playlist_video_ids(api_key=api_key, playlist_id=playlist_id))
    if not video_ids:
        return pd.DataFrame(
            columns=[
                "video_id",
                "title",
                "channel_title",
                "published_at",
                "view_count",
                "like_count",
                "comment_count",
            ]
        )

    rows: List[Dict] = []
    for chunk in _chunks(video_ids, 50):
        payload = _get(
            "videos",
            {
                "part": "snippet,statistics",
                "id": ",".join(chunk),
                "maxResults": "50",
                "key": api_key,
            },
        )

        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            rows.append(
                {
                    "video_id": item.get("id", ""),
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "view_count": int(stats.get("viewCount", 0) or 0),
                    "like_count": int(stats.get("likeCount", 0) or 0),
                    "comment_count": int(stats.get("commentCount", 0) or 0),
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="view_count", ascending=False).reset_index(drop=True)
    return df
