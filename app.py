import os

import streamlit as st

from youtube_tracker.storage import (
    append_snapshot,
    load_snapshot_history,
    load_user_config,
    save_user_config,
)
from youtube_tracker.youtube_api import (
    YouTubeApiError,
    discover_channel_playlists,
    extract_playlist_id,
    fetch_playlist_videos_with_stats,
)


st.set_page_config(page_title="YouTube Playlist Tracker", page_icon="YT", layout="wide")

if "discovered_playlists" not in st.session_state:
    st.session_state["discovered_playlists"] = []


def _get_default_api_key() -> str:
    env_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        return st.secrets.get("YOUTUBE_API_KEY", "")
    except Exception:
        return ""

st.title("YouTube Playlist Tracker")
st.caption("Phase 1-3: Single playlist retrieval, playlist discovery, and local snapshot history.")

st.subheader("API Configuration")
api_key = st.text_input(
    "YouTube Data API key",
    type="password",
    value=_get_default_api_key(),
    help="For local testing, enter the key here or set YOUTUBE_API_KEY in .streamlit/secrets.toml.",
)

st.subheader("Playlist Discovery (Phase 2)")
channel_input = st.text_input(
    "Channel URL, handle (@name), or channel ID",
    placeholder="https://www.youtube.com/@channelname or UC...",
)

discover_clicked = st.button("Discover Public Playlists")
if discover_clicked:
    if not api_key.strip():
        st.error("Please provide a YouTube Data API key before discovery.")
        st.stop()

    with st.spinner("Discovering playlists..."):
        try:
            playlists = discover_channel_playlists(api_key=api_key.strip(), channel_input=channel_input)
        except YouTubeApiError as exc:
            st.error(f"YouTube API error: {exc}")
            st.stop()

    st.session_state["discovered_playlists"] = playlists
    st.success(f"Discovered {len(playlists)} playlists.")

user_config = load_user_config()
discovered = st.session_state["discovered_playlists"]
discovered_ids = [item["playlist_id"] for item in discovered]
saved_defaults = [item for item in user_config.get("saved_playlist_ids", []) if item in discovered_ids]

selected_discovered_playlists = st.multiselect(
    "Save one or more discovered playlists",
    options=discovered_ids,
    default=saved_defaults,
    format_func=lambda playlist_id: next(
        (
            f"{item['title']} ({item['video_count']} videos) [{item['playlist_id']}]"
            for item in discovered
            if item["playlist_id"] == playlist_id
        ),
        playlist_id,
    ),
)

save_config_clicked = st.button("Save Playlist Selection")
if save_config_clicked:
    save_user_config(selected_discovered_playlists)
    st.success("Saved playlist selection to local config.")

st.subheader("Playlist Stats Retrieval")
playlist_input = st.text_input(
    "Playlist URL or Playlist ID",
    placeholder="https://www.youtube.com/playlist?list=PL... or PL...",
)

playlist_choices = ["(manual input)"] + selected_discovered_playlists
selected_source = st.selectbox("Choose source playlist", options=playlist_choices)

if selected_source != "(manual input)":
    active_playlist_id = selected_source
else:
    active_playlist_id = extract_playlist_id(playlist_input)

persist_snapshot = st.checkbox("Save snapshot to local history", value=False)

fetch_clicked = st.button("Fetch Playlist Statistics", type="primary")

if fetch_clicked:
    if not api_key.strip():
        st.error("Please provide a YouTube Data API key.")
        st.stop()

    if not active_playlist_id:
        st.error("Please provide a valid YouTube playlist URL or playlist ID.")
        st.stop()

    with st.spinner("Loading playlist videos and statistics..."):
        try:
            df = fetch_playlist_videos_with_stats(api_key=api_key.strip(), playlist_id=active_playlist_id)
        except YouTubeApiError as exc:
            st.error(f"YouTube API error: {exc}")
            st.stop()

    st.success(f"Loaded {len(df)} videos from playlist {active_playlist_id}.")
    st.dataframe(df, use_container_width=True)

    if persist_snapshot and not df.empty:
        playlist_title_lookup = {
            item["playlist_id"]: item["title"] for item in st.session_state["discovered_playlists"]
        }
        snapshot_time = append_snapshot(
            playlist_id=active_playlist_id,
            playlist_title=playlist_title_lookup.get(active_playlist_id, ""),
            df=df,
        )
        st.info(f"Snapshot saved at {snapshot_time}.")

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name=f"playlist_{active_playlist_id}_stats.csv",
        mime="text/csv",
    )

st.subheader("Historical Snapshot Summary (Phase 3)")
history_df = load_snapshot_history()
if history_df.empty:
    st.caption("No local snapshots saved yet.")
else:
    playlist_filter_options = sorted(history_df["playlist_id"].dropna().unique().tolist())
    selected_history_playlist = st.selectbox(
        "Playlist for history",
        options=playlist_filter_options,
    )

    filtered_history = history_df[history_df["playlist_id"] == selected_history_playlist].copy()
    grouped = (
        filtered_history.groupby("snapshot_time", as_index=False)
        .agg(
            video_rows=("video_id", "count"),
            total_views=("view_count", "sum"),
            total_likes=("like_count", "sum"),
            total_comments=("comment_count", "sum"),
        )
        .sort_values("snapshot_time", ascending=False)
    )
    st.dataframe(grouped, use_container_width=True)

st.divider()
st.markdown(
    """
### Next Phases
- Add richer time-series visualizations and charts
- Support multi-playlist aggregate dashboards
- Add optional OAuth workflow for account-specific features
- Add pluggable persistent backend (SQLite or Postgres)
"""
)
