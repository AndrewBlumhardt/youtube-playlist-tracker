# YouTube Playlist Tracker

A lightweight Streamlit project for retrieving public statistics for videos in a YouTube playlist.

## Current Scope (Phase 1)

- Accept a YouTube Data API key.
- Accept a single playlist URL or playlist ID.
- Retrieve playlist videos.
- Retrieve per-video public stats (views, likes, comments where available).
- Display results in a Streamlit table and allow CSV export.

## Why This Works for Non-Owned Videos

The YouTube Data API can return public metadata and public statistics for videos that are publicly visible, even when those videos are not owned by your channel. This makes playlist-based monitoring feasible for curation use cases (for example TEDx-style collections).

Owner-only capabilities (editing metadata, private analytics, moderation actions, etc.) require OAuth scopes and channel ownership permissions, and are intentionally out of scope for Phase 1.

## Project Structure

- `app.py`: Streamlit UI for API key input, playlist input, retrieval, table display, and CSV download.
- `requirements.txt`: Python dependencies.
- `youtube_tracker/youtube_api.py`: API client utilities for playlist parsing and stats retrieval.
- `youtube_tracker/README.md`: Folder-level notes for the API helper package.
- `.streamlit/README.md`: Folder-level guidance for local secrets configuration.

## Local Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Add your API key to `.streamlit/secrets.toml`:

```toml
YOUTUBE_API_KEY = "your_api_key_here"
```

4. Start the app:

```bash
streamlit run app.py
```

## Planned Next Phases

- Discover playlists tied to the authenticated account.
- Save selected playlists and user settings.
- Store daily/hourly snapshots to persistent storage.
- Add trend visualizations for historical changes.
- Add optional owner-capability workflows for channel-owned videos.
