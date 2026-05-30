import streamlit as st

from youtube_tracker.youtube_api import (
    YouTubeApiError,
    extract_playlist_id,
    fetch_playlist_videos_with_stats,
)


st.set_page_config(page_title="YouTube Playlist Tracker", page_icon="YT", layout="wide")

st.title("YouTube Playlist Tracker")
st.caption("Phase 1: Fetch and display public video statistics for one playlist.")

st.subheader("API Configuration")
api_key = st.text_input(
    "YouTube Data API key",
    type="password",
    value=st.secrets.get("YOUTUBE_API_KEY", ""),
    help="For local testing, enter the key here or set YOUTUBE_API_KEY in .streamlit/secrets.toml.",
)

playlist_input = st.text_input(
    "Playlist URL or Playlist ID",
    placeholder="https://www.youtube.com/playlist?list=PL... or PL...",
)

fetch_clicked = st.button("Fetch Playlist Statistics", type="primary")

if fetch_clicked:
    if not api_key.strip():
        st.error("Please provide a YouTube Data API key.")
        st.stop()

    playlist_id = extract_playlist_id(playlist_input)
    if not playlist_id:
        st.error("Please provide a valid YouTube playlist URL or playlist ID.")
        st.stop()

    with st.spinner("Loading playlist videos and statistics..."):
        try:
            df = fetch_playlist_videos_with_stats(api_key=api_key.strip(), playlist_id=playlist_id)
        except YouTubeApiError as exc:
            st.error(f"YouTube API error: {exc}")
            st.stop()

    st.success(f"Loaded {len(df)} videos from playlist {playlist_id}.")
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name=f"playlist_{playlist_id}_stats.csv",
        mime="text/csv",
    )

st.divider()
st.markdown(
    """
### Next Phases
- Playlist discovery for the authenticated user's channel
- Save selected playlists and configuration
- Persist snapshots for time-based trend reporting
- Dashboard charts for views/likes/comments over time
"""
)
