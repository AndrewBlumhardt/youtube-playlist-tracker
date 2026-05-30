# youtube_tracker Package

This folder contains API helper logic for YouTube playlist and video statistics retrieval.

## Files

- `youtube_api.py`: Parses playlist IDs, paginates playlist items, fetches batched video stats, and returns a pandas DataFrame.

## Design Notes

- Keeps YouTube API calls outside the Streamlit page code.
- Returns normalized tabular output for easy CSV export and future persistence.
