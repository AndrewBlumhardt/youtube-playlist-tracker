import os

import pandas as pd
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
if "selected_playlists" not in st.session_state:
    st.session_state["selected_playlists"] = []
if "latest_combined_df" not in st.session_state:
    st.session_state["latest_combined_df"] = pd.DataFrame()


def _get_default_api_key() -> str:
    env_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        return st.secrets.get("YOUTUBE_API_KEY", "")
    except Exception:
        return ""

st.markdown(
    """
<style>
div[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 15% 20%, #eef6ff 0%, #f9fbff 40%, #ffffff 100%);
}
.yt-card {
    padding: 0.9rem 1rem;
    border: 1px solid #d8e8ff;
    border-radius: 12px;
    background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
}
.yt-note {
    color: #2a4e75;
    font-size: 0.92rem;
}
</style>
""",
    unsafe_allow_html=True,
)

title_col, link_col = st.columns([6, 2])
title_col.title("YouTube Playlist Tracker")
title_col.caption("Discover playlists, retrieve stats, and preview videos directly in-app.")
link_col.markdown(
    """
<div style="padding-top: 2.2rem; text-align: right;">
<a href="https://github.com/AndrewBlumhardt/youtube-playlist-tracker" target="_blank">GitHub Repository</a>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="yt-card yt-note">
Tip: Discover playlists first, then use multi-select chips to choose what to run. You can still add one manual playlist URL/ID for ad-hoc testing.
</div>
""",
    unsafe_allow_html=True,
)

st.subheader("API Configuration")
api_key = st.text_input(
    "YouTube Data API key",
    type="password",
    value=_get_default_api_key(),
    help="For local testing, enter the key here or set YOUTUBE_API_KEY in .streamlit/secrets.toml.",
)

st.subheader("Playlist Discovery")
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
    st.session_state["selected_playlists"] = [item["playlist_id"] for item in playlists]
    st.success(f"Discovered {len(playlists)} playlists.")

user_config = load_user_config()
discovered = st.session_state["discovered_playlists"]
discovered_ids = [item["playlist_id"] for item in discovered]
saved_defaults = [item for item in user_config.get("saved_playlist_ids", []) if item in discovered_ids]
if discovered_ids and not st.session_state["selected_playlists"]:
    st.session_state["selected_playlists"] = saved_defaults or discovered_ids

playlist_title_lookup = {item["playlist_id"]: item["title"] for item in discovered}

selected_discovered_playlists = st.multiselect(
    "Discovered playlists to include for stats retrieval",
    options=discovered_ids,
    key="selected_playlists",
    format_func=lambda playlist_id: next(
        (
            f"{item['title']} ({item['video_count']} videos)"
            for item in discovered
            if item["playlist_id"] == playlist_id
        ),
        playlist_id,
    ),
)

metric_col1, metric_col2 = st.columns(2)
metric_col1.metric("Discovered Playlists", len(discovered_ids))
metric_col2.metric("Selected For Retrieval", len(selected_discovered_playlists))

col1, col2 = st.columns(2)
if col1.button("Select All Discovered"):
    st.session_state["selected_playlists"] = discovered_ids
    st.rerun()
if col2.button("Clear Selection"):
    st.session_state["selected_playlists"] = []
    st.rerun()

save_config_clicked = st.button("Save Playlist Selection")
if save_config_clicked:
    save_user_config(selected_discovered_playlists)
    st.success("Saved playlist selection to local config.")

st.subheader("Playlist Stats Retrieval")
playlist_input = st.text_input(
    "Optional manual playlist URL or playlist ID",
    placeholder="https://www.youtube.com/playlist?list=PL... or PL...",
)
manual_playlist_id = extract_playlist_id(playlist_input) if playlist_input.strip() else ""

persist_snapshot = st.checkbox("Save snapshot to local history", value=False)

fetch_clicked = st.button("Fetch Playlist Statistics", type="primary")

if fetch_clicked:
    if not api_key.strip():
        st.error("Please provide a YouTube Data API key.")
        st.stop()

    playlist_ids_to_fetch = list(selected_discovered_playlists)
    if manual_playlist_id and manual_playlist_id not in playlist_ids_to_fetch:
        playlist_ids_to_fetch.append(manual_playlist_id)

    if not playlist_ids_to_fetch:
        st.error("Select one or more discovered playlists, or provide a valid manual playlist URL/ID.")
        st.stop()

    if playlist_input.strip() and not manual_playlist_id:
        st.error("Manual playlist input is not a valid playlist URL or playlist ID.")
        st.stop()

    all_frames = []
    with st.spinner("Loading playlist videos and statistics..."):
        for playlist_id in playlist_ids_to_fetch:
            try:
                df = fetch_playlist_videos_with_stats(api_key=api_key.strip(), playlist_id=playlist_id)
            except YouTubeApiError as exc:
                st.error(f"YouTube API error for playlist {playlist_id}: {exc}")
                continue

            playlist_title = playlist_title_lookup.get(playlist_id, "Manual Playlist")

            df_display = df.copy()
            if "video_id" in df_display.columns:
                df_display["video_url"] = "https://www.youtube.com/watch?v=" + df_display["video_id"].astype(str)

            st.success(f"Loaded {len(df)} videos from {playlist_title} ({playlist_id}).")
            with st.expander(f"Results: {playlist_title}", expanded=False):
                st.caption(f"Playlist ID: {playlist_id}")
                st.dataframe(
                    df_display,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "video_url": st.column_config.LinkColumn("Video Link", display_text="Open"),
                    },
                )

                if persist_snapshot and not df.empty:
                    snapshot_time = append_snapshot(
                        playlist_id=playlist_id,
                        playlist_title=playlist_title,
                        df=df,
                    )
                    st.info(f"Snapshot saved for {playlist_title} at {snapshot_time}.")

                download_name = f"playlist_{playlist_id}_stats.csv"
                st.download_button(
                    label=f"Download CSV: {playlist_title}",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name=download_name,
                    mime="text/csv",
                    key=f"download_{playlist_id}",
                )

            if not df.empty:
                df = df.copy()
                df.insert(0, "playlist_id", playlist_id)
                df.insert(1, "playlist_title", playlist_title)
                if "video_id" in df.columns:
                    df.insert(2, "video_url", "https://www.youtube.com/watch?v=" + df["video_id"].astype(str))
                all_frames.append(df)

    if all_frames:
        combined_df = all_frames[0] if len(all_frames) == 1 else pd.concat(all_frames, ignore_index=True)
        st.session_state["latest_combined_df"] = combined_df
        st.subheader("Combined Results")
        st.dataframe(
            combined_df,
            width="stretch",
            hide_index=True,
            column_config={
                "video_url": st.column_config.LinkColumn("Video Link", display_text="Open"),
            },
        )

        st.markdown("### In-App Video Preview")
        playlist_options = sorted(combined_df["playlist_title"].dropna().unique().tolist())
        selected_preview_playlist = st.selectbox("Choose playlist", options=playlist_options)
        preview_candidates = combined_df[combined_df["playlist_title"] == selected_preview_playlist].copy()
        preview_candidates["video_label"] = (
            preview_candidates["title"].astype(str)
            + " | views: "
            + preview_candidates["view_count"].astype(str)
        )

        selected_video_label = st.selectbox(
            "Choose video to preview",
            options=preview_candidates["video_label"].tolist(),
        )
        selected_video_row = preview_candidates[preview_candidates["video_label"] == selected_video_label].iloc[0]
        st.video(selected_video_row["video_url"])

        st.download_button(
            label="Download Combined CSV",
            data=combined_df.to_csv(index=False).encode("utf-8"),
            file_name="playlist_combined_stats.csv",
            mime="text/csv",
        )

latest_df = st.session_state["latest_combined_df"]
if not latest_df.empty:
    st.subheader("Latest Retrieval Snapshot")
    snap_col1, snap_col2, snap_col3 = st.columns(3)
    snap_col1.metric("Videos", int(len(latest_df)))
    snap_col2.metric("Total Views", int(latest_df["view_count"].sum()))
    snap_col3.metric("Total Likes", int(latest_df["like_count"].sum()))

st.subheader("Historical Snapshot Summary")
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
    st.dataframe(grouped, width="stretch")
