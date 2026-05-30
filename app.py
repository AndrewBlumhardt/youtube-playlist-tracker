import os

import altair as alt
import pandas as pd
import streamlit as st

from youtube_tracker.storage import (
    append_snapshot,
    estimate_playlist_history,
    load_snapshot_history,
    load_user_config,
    save_user_config,
    save_user_preferences,
)
from youtube_tracker import youtube_api as yt_api

YouTubeApiError = yt_api.YouTubeApiError
discover_channel_playlists = yt_api.discover_channel_playlists
extract_playlist_id = yt_api.extract_playlist_id
fetch_playlist_videos_with_stats = yt_api.fetch_playlist_videos_with_stats


def verify_api_key(api_key: str):
    # Backward-compatible fallback if local module is out of date.
    if hasattr(yt_api, "verify_api_key"):
        return yt_api.verify_api_key(api_key)
    return (True, "API key format accepted. Upgrade youtube_api.py for full key verification.")


st.set_page_config(page_title="YouTube Playlist Tracker", page_icon="YT", layout="wide")

README_API_HELP_URL = "https://github.com/AndrewBlumhardt/youtube-playlist-tracker#api-setup-and-lookup-instructions"
GOOGLE_API_HELP_URL = "https://developers.google.com/youtube/registering_an_application"

if "discovered_playlists" not in st.session_state:
    st.session_state["discovered_playlists"] = []
if "selected_playlists" not in st.session_state:
    st.session_state["selected_playlists"] = []
if "latest_combined_df" not in st.session_state:
    st.session_state["latest_combined_df"] = pd.DataFrame()
if "api_verified" not in st.session_state:
    st.session_state["api_verified"] = False


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
section.main > div.block-container {
    padding-top: 1rem;
}
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

st.subheader("API Configuration")
api_key = st.text_input(
    "YouTube Data API key",
    type="password",
    value=_get_default_api_key(),
    help=(
        "For local testing, enter the key here or set YOUTUBE_API_KEY in .streamlit/secrets.toml. "
        "Your browser may offer to save it securely as a password. "
        f"Need help? [Repo instructions]({README_API_HELP_URL}) or "
        f"[Google setup guide]({GOOGLE_API_HELP_URL})."
    ),
)
verify_col, status_col = st.columns([1, 3])
if verify_col.button("Verify API Key"):
    if not api_key.strip():
        st.session_state["api_verified"] = False
        st.error("Enter an API key first.")
    else:
        is_valid, message = verify_api_key(api_key.strip())
        st.session_state["api_verified"] = is_valid
        if is_valid:
            st.success(f"✅ {message}")
        else:
            st.error(f"❌ {message}")

if st.session_state["api_verified"]:
    status_col.success("API key verified for this session.")

st.subheader("Playlist Discovery")
user_config = load_user_config()
channel_input = st.text_input(
    "Channel URL, handle (@name), or channel ID",
    placeholder="https://www.youtube.com/@channelname or UC...",
    value=user_config.get("last_channel_input", ""),
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
    save_user_preferences(last_channel_input=channel_input)
    st.success(f"Discovered {len(playlists)} playlists.")

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

action_col1, action_col2, action_col3 = st.columns(3)
if action_col1.button("Select All Discovered", use_container_width=True):
    st.session_state["selected_playlists"] = discovered_ids
    st.rerun()
if action_col2.button("Clear Selection", use_container_width=True):
    st.session_state["selected_playlists"] = []
    st.rerun()

if action_col3.button("Save Playlist Selection", use_container_width=True):
    save_user_config(selected_discovered_playlists)
    save_user_preferences(saved_playlist_ids=selected_discovered_playlists, last_channel_input=channel_input)
    st.success("Saved playlist selection to local config.")

playlist_input = st.text_input(
    "Optional manual playlist URL or playlist ID",
    placeholder="https://www.youtube.com/playlist?list=PL... or PL...",
    value=user_config.get("last_playlist_input", ""),
)
manual_playlist_id = extract_playlist_id(playlist_input) if playlist_input.strip() else ""

persist_snapshot = st.checkbox("Save snapshot to local history", value=bool(user_config.get("save_snapshot_default", False)))

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

    save_user_preferences(
        saved_playlist_ids=selected_discovered_playlists,
        last_channel_input=channel_input,
        last_playlist_input=playlist_input,
        save_snapshot_default=persist_snapshot,
        last_history_playlist_id=user_config.get("last_history_playlist_id", ""),
    )

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

        totals_df = (
            combined_df.groupby(["playlist_id", "playlist_title"], as_index=False)
            .agg(
                videos=("video_id", "nunique"),
                total_views=("view_count", "sum"),
                total_likes=("like_count", "sum"),
                total_comments=("comment_count", "sum"),
            )
            .sort_values("total_views", ascending=False)
        )
        grand_total = pd.DataFrame(
            [
                {
                    "playlist_id": "ALL",
                    "playlist_title": "Grand Total",
                    "videos": int(combined_df["video_id"].nunique()),
                    "total_views": int(combined_df["view_count"].sum()),
                    "total_likes": int(combined_df["like_count"].sum()),
                    "total_comments": int(combined_df["comment_count"].sum()),
                }
            ]
        )
        st.subheader("Playlist Totals")
        st.dataframe(pd.concat([totals_df, grand_total], ignore_index=True), width="stretch", hide_index=True)

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
        index=playlist_filter_options.index(user_config.get("last_history_playlist_id", playlist_filter_options[0]))
        if user_config.get("last_history_playlist_id", "") in playlist_filter_options
        else 0,
    )
    save_user_preferences(last_history_playlist_id=selected_history_playlist)

    estimate_col1, estimate_col2 = st.columns([2, 1])
    months_back = estimate_col1.slider("Estimate months back", min_value=3, max_value=24, value=12, step=1)
    if estimate_col2.button("Estimate Playlist History", use_container_width=True):
        result = estimate_playlist_history(selected_history_playlist, months_back=months_back)
        st.success(
            f"Estimated {result['estimated_rows']} rows for {result['videos']} videos over {result['months']} months."
        )
        history_df = load_snapshot_history()

    filtered_history = history_df[history_df["playlist_id"] == selected_history_playlist].copy()
    filtered_history["snapshot_time"] = pd.to_datetime(filtered_history["snapshot_time"], errors="coerce", utc=True)
    filtered_history = filtered_history.dropna(subset=["snapshot_time"])

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

    st.subheader("History Timeline / Histogram")
    if filtered_history.empty:
        st.caption("No history data for selected playlist.")
    else:
        per_video_df = filtered_history.copy()
        per_video_df["video_label"] = per_video_df["title"].fillna("").astype(str)
        per_video_df.loc[per_video_df["video_label"].str.strip() == "", "video_label"] = per_video_df["video_id"]

        video_count_limit = st.slider("Max videos to plot", min_value=3, max_value=30, value=12, step=1)
        top_videos = (
            per_video_df.groupby(["video_id", "video_label"], as_index=False)["view_count"].max()
            .sort_values("view_count", ascending=False)
            .head(video_count_limit)
        )
        plot_df = per_video_df[per_video_df["video_id"].isin(top_videos["video_id"])].copy()

        view_mode = st.radio("Visualization", options=["Timeline (per video)", "Histogram (totals)"])
        if view_mode == "Timeline (per video)":
            timeline_chart = (
                alt.Chart(plot_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("snapshot_time:T", title="Snapshot Time"),
                    y=alt.Y("view_count:Q", title="Views"),
                    color=alt.Color("video_label:N", title="Video"),
                    strokeDash=alt.StrokeDash("data_source:N", title="Data Type"),
                    tooltip=[
                        alt.Tooltip("snapshot_time:T", title="Time"),
                        alt.Tooltip("video_label:N", title="Video"),
                        alt.Tooltip("data_source:N", title="Data Type"),
                        alt.Tooltip("view_count:Q", title="Views"),
                        alt.Tooltip("like_count:Q", title="Likes"),
                        alt.Tooltip("comment_count:Q", title="Comments"),
                    ],
                )
                .properties(height=420)
            )
            st.altair_chart(timeline_chart, use_container_width=True)
        else:
            hist_df = (
                plot_df.groupby(["snapshot_time", "data_source"], as_index=False)
                .agg(total_views=("view_count", "sum"))
                .sort_values("snapshot_time", ascending=True)
            )
            histogram_chart = (
                alt.Chart(hist_df)
                .mark_bar()
                .encode(
                    x=alt.X("snapshot_time:T", title="Snapshot Time"),
                    y=alt.Y("total_views:Q", title="Total Views"),
                    color=alt.Color("data_source:N", title="Data Type"),
                    tooltip=[
                        alt.Tooltip("snapshot_time:T", title="Time"),
                        alt.Tooltip("data_source:N", title="Data Type"),
                        alt.Tooltip("total_views:Q", title="Total Views"),
                    ],
                )
                .properties(height=420)
            )
            st.altair_chart(histogram_chart, use_container_width=True)
