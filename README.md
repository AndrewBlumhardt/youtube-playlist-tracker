# YouTube Playlist Tracker

A lightweight Streamlit project for retrieving public statistics for videos in a YouTube playlist.

## Start Here (Low-Tech, Step By Step)

If you are starting from scratch, follow these steps in order.

1. Install Python (3.10+):
	- Download from python.org
	- During install on Windows, check "Add Python to PATH"
2. Install Visual Studio Code.
3. Open VS Code.
4. Open this project folder:
	- File -> Open Folder -> `C:\repos\youtube-playlist-tracker`
5. Install VS Code extensions (if prompted):
	- Python (Microsoft)
	- Jupyter (Microsoft)
6. Open a new terminal in VS Code:
	- Terminal -> New Terminal
7. In the terminal, install project packages:

```bash
pip install -r requirements.txt
```

8. Choose one run path:
	- Notebook run-once validation: open [youtube_playlist_tracker.ipynb](youtube_playlist_tracker.ipynb)
	- Streamlit web app: run `streamlit run app.py` in the VS Code terminal

## Why This Works for Non-Owned Videos

The YouTube Data API can return public metadata and public statistics for videos that are publicly visible, even when those videos are not owned by your channel. This makes playlist-based monitoring feasible for curated collections.

Owner-only capabilities (editing metadata, private analytics, moderation actions, etc.) require OAuth scopes and channel ownership permissions, and are intentionally out of scope for Phase 1.

## Project Structure

- `app.py`: Streamlit UI for API key input, playlist input, retrieval, table display, and CSV download.
- `requirements.txt`: Python dependencies.
- `youtube_tracker/youtube_api.py`: API client utilities for playlist parsing and stats retrieval.
- `youtube_tracker/storage.py`: Local persistence helpers for saved playlist config and snapshots.
- `data/README.md`: Local data storage folder notes for config and snapshot files.
- `youtube_tracker/README.md`: Folder-level notes for the API helper package.
- `.streamlit/README.md`: Folder-level guidance for local secrets configuration.

## Local Run

Use this when you want the Streamlit web app UI.

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

5. Open the local URL shown in terminal (usually `http://localhost:8501`).

## Notebook Run-Once Snapshot And Validation

Use [youtube_playlist_tracker.ipynb](youtube_playlist_tracker.ipynb) when you want a single manual run to validate API access and capture one snapshot.

### Quick Start (Notebook)

1. Open [youtube_playlist_tracker.ipynb](youtube_playlist_tracker.ipynb) in VS Code.
2. Run Cell 2 (installs/imports).
3. In Cell 3, set:
	- `CHANNEL_INPUT` (optional, for playlist discovery)
	- `PLAYLIST_INPUT` (optional if discovery returns playlists)
	- `SAVE_SNAPSHOT = True` only if you want to write history for this run
4. Run Cell 4 to discover playlists (or skip if using `PLAYLIST_INPUT` directly).
5. Run Cell 5 to choose the playlist ID.
6. Run Cell 6 to fetch stats (this is your validation step).
7. Run Cell 7 only if you want to save a snapshot.
8. Run Cell 8 to view history summary for the selected playlist.

Note: the notebook is best for run-once checks and validation.

### API Key (Simple)

You have two easy options:

1. Recommended: set `YOUTUBE_API_KEY` environment variable before launching the notebook.
	- PowerShell: `$env:YOUTUBE_API_KEY="your_api_key_here"`
2. Or: leave env var unset and Cell 3 will prompt for the key with hidden input.

For key creation steps, see the [API Setup And Lookup Instructions](README.md#api-setup-and-lookup-instructions) section.

### Should `streamlit run app.py` be run inside the notebook?

Use the VS Code terminal for Streamlit. It is more reliable and easier to stop/restart.

1. In VS Code: Terminal -> New Terminal
2. Run:

```bash
streamlit run app.py
```

3. Keep notebook for validation/snapshots, and Streamlit for interactive app usage.

## API Setup And Lookup Instructions

This project uses the YouTube Data API v3 with an API key.

1. Create or select a Google Cloud project.
2. Enable YouTube Data API v3:
	- Google Cloud Console -> APIs & Services -> Library
	- Search for YouTube Data API v3 and enable it
3. Create an API key:
	- Google Cloud Console -> APIs & Services -> Credentials -> Create credentials -> API key
4. Restrict the API key (recommended):
	- Application restrictions: set based on your usage model (for example IP address for server usage)
	- API restrictions: limit to YouTube Data API v3
5. Add the key to the app:
	- Paste into the app input, or
	- Store as YOUTUBE_API_KEY in .streamlit/secrets.toml

### Lookup: Playlist ID

- From a playlist URL such as https://www.youtube.com/playlist?list=PLabc123XYZ
- The value after list= is the playlist ID

### Lookup: Channel Input For Discovery

The app accepts any of the following:

- Channel URL: https://www.youtube.com/@yourhandle or https://www.youtube.com/channel/UC...
- Handle: @yourhandle
- Channel ID: UC...
- Search text: channel name query (best-effort match)

### Notes On Access Scope

- Public playlist/video metadata and public stats can be fetched with an API key.
- Account-specific listings tied directly to the signed-in Google user require OAuth and additional scopes (planned later).

## First Run Checklist (Under 5 Minutes)

1. Clone the repository and open it in your terminal.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a YouTube API key and enable YouTube Data API v3.
5. Provide the API key:
	- Add YOUTUBE_API_KEY to .streamlit/secrets.toml, or
	- Paste the key directly into the app.
6. Start Streamlit:

```bash
streamlit run app.py
```

7. In the app:
	- Enter a channel URL/handle and click Discover Public Playlists.
	- Select and save one or more playlists.
	- Fetch playlist statistics.
	- Optionally save a snapshot to build history.

8. Confirm success:
	- You see a video stats table.
	- CSV download works.
	- Historical Snapshot Summary populates after one saved snapshot.

## Notebook Key Safety

Use this workflow to avoid committing secrets:

1. Use `youtube_playlist_tracker.ipynb` as the tracked template notebook.
2. Create your personal working copy named `youtube_playlist_tracker.local.ipynb`.
3. Put sensitive experimentation in the `.local.ipynb` file only.
4. Set your key with environment variable `YOUTUBE_API_KEY` or use the notebook prompt.
5. Before any commit, run `git status` and confirm no secret-bearing notebook is staged.

Files matching `*.local.ipynb` are ignored by Git.

## Notes on Discovery

Channel discovery in this version is based on public channel data (channel URL/handle/ID/query). Retrieving playlists specifically tied to the currently signed-in Google account requires OAuth-based flows and additional scopes, which is a later enhancement.

## Planned Next Phases

- Add richer charting and trend dashboards.
- Add optional OAuth account flow for user-specific playlist listing.
- Add multi-user API key/config storage model.
- Add pluggable persistent backend (SQLite/Postgres).

## Current Scope (Reference)

- Accept a YouTube Data API key.
- Accept a playlist URL or playlist ID.
- Discover public playlists from a channel URL, handle, channel ID, or query.
- Save selected discovered playlist IDs to local config.
- Retrieve playlist videos and per-video public stats.
- Display results in a Streamlit table and allow CSV export.
- Save local historical snapshots for trend tracking.
