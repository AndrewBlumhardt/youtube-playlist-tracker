# youtube_tracker Package

This folder contains API helper logic for YouTube playlist and video statistics retrieval.

## Files

- `youtube_api.py`: Parses playlist/channel input, discovers playlists, paginates playlist items, and fetches batched video stats.
- `storage.py`: Saves playlist selection config and appends/loads local historical snapshot records.

## Design Notes

- Keeps YouTube API calls outside the Streamlit page code.
- Returns normalized tabular output for easy CSV export and future persistence.

