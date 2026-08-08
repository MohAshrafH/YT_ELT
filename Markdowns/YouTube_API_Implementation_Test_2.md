# YouTube Data API Extraction — Implementation/Test 2

## Overview

This version refactors the initial YouTube API proof of concept into a reusable Python function:

```python
get_playlist_id()
```

The function queries the **YouTube Data API v3** using the `channels.list` endpoint, retrieves the target channel's `contentDetails`, extracts the special **Uploads Playlist ID**, and returns that ID to the caller.

This iteration also introduces:

- A reusable function instead of executing all logic at module level
- A `try` / `except` structure for request-related errors
- A returned value instead of relying only on `print()`
- The Python `if __name__ == "__main__":` entry-point pattern
- A clearer separation between reusable code and direct script execution

---

## Functional Objective

The functional flow is:

```text
@MrBeast
    |
    | channels.list
    v
Channel JSON response
    |
    v
items[0]
    |
    v
contentDetails
    |
    v
relatedPlaylists
    |
    v
uploads
    |
    v
Uploads Playlist ID
```

Example returned value:

```text
UUX6OQ3DkcsbYNE6H8uQQuVA
```

This value is the ID of the channel's special uploads playlist.

It is **not** the list of videos itself.

A later API call using `playlistItems.list` will use this playlist ID to retrieve the individual uploaded video IDs.

---

# Current Code

> **Important:** Do not commit a real API key to GitHub. Replace it with a placeholder or load it from `.env` before committing.

```python
import requests
import json


# ============================================================
# CONFIGURATION
# ============================================================

# API key used to identify/authenticate the Google Cloud project
# when calling the YouTube Data API.
#
# IMPORTANT:
# Do not commit a real API key to GitHub.
# A later implementation should load this from a .env file.
API_KEY = "YOUR_API_KEY"


# Public YouTube handle of the channel we want to query.
# This corresponds to the @MrBeast channel.
CHANNEL_HANDLE = "MrBeast"


# ============================================================
# FUNCTION: get_playlist_id()
# ============================================================

# Purpose:
# Retrieve the special "uploads playlist" ID associated with
# the YouTube channel identified by CHANNEL_HANDLE.
#
# Functional flow:
#
# CHANNEL_HANDLE
#      |
#      v
# channels.list API request
#      |
#      v
# JSON response
#      |
#      v
# items[0]
#      |
#      v
# contentDetails
#      |
#      v
# relatedPlaylists
#      |
#      v
# uploads
#      |
#      v
# Uploads Playlist ID
#
# The returned playlist ID will later be passed to another
# YouTube API request (playlistItems.list) to retrieve the
# individual uploaded video IDs.
def get_playlist_id():

    # The try block contains operations that may potentially
    # raise a requests-related exception.
    try:

        # Build the URL for the YouTube Data API channels.list request.
        #
        # Query parameters:
        #   part=contentDetails
        #       Requests the channel section containing related playlists.
        #
        #   forHandle=CHANNEL_HANDLE
        #       Identifies the target YouTube channel.
        #
        #   key=API_KEY
        #       Supplies the API key associated with the Google Cloud project.
        url = (
            "https://youtube.googleapis.com/youtube/v3/channels"
            f"?part=contentDetails"
            f"&forHandle={CHANNEL_HANDLE}"
            f"&key={API_KEY}"
        )

        # Send an HTTP GET request to the YouTube Data API.
        response = requests.get(url)

        # Parse the JSON response body into Python dictionaries/lists.
        data = response.json()

        # Optional debugging output.
        # print(json.dumps(data, indent=4))

        # The API returns channel results inside the "items" list.
        # [0] selects the first returned channel object.
        channel_items = data["items"][0]

        # Navigate through the nested response and extract:
        #
        # contentDetails
        #   -> relatedPlaylists
        #       -> uploads
        #
        # The final value is the channel's uploads playlist ID.
        channel_playlistID = (
            channel_items["contentDetails"]
            ["relatedPlaylists"]
            ["uploads"]
        )

        # Optional debugging output.
        # print(f"Channel Playlist ID: {channel_playlistID}")

        # Return the playlist ID so other code can reuse it.
        return channel_playlistID

    # Catch request-related exceptions raised by the requests library.
    except requests.exceptions.RequestException as e:

        # Re-raise the original exception so the caller/runtime
        # receives the actual failure and traceback.
        raise e


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

# __name__ is a special built-in Python variable.
#
# If this file is run directly:
#
#     python video_stats.py
#
# then:
#
#     __name__ == "__main__"
#
# If this file is imported from another Python module:
#
#     import video_stats
#
# then __name__ is set to the module name instead.
#
# This allows the function to be reusable without automatically
# executing it whenever the file is imported.
if __name__ == "__main__":

    print("get_playlist_id() function is being called")

    get_playlist_id()

else:

    print("get_playlist_id() function is not being called")
```

---

# What Changed from Implementation/Test 1

## 1. Logic moved into a function

Previously, the API request and JSON extraction logic ran directly at module level.

Now it is encapsulated inside:

```python
def get_playlist_id():
```

This improves modularity and makes the logic reusable.

For example, another function can later do:

```python
playlist_id = get_playlist_id()
```

and use the returned value as input to the next extraction step.

---

## 2. The playlist ID is returned

The function now uses:

```python
return channel_playlistID
```

instead of relying only on:

```python
print(channel_playlistID)
```

The difference is important:

```text
print()
    -> displays a value for a human

return
    -> gives the value back to the calling code
```

Returning the value enables composition:

```text
get_playlist_id()
        |
        v
playlist ID
        |
        v
get_video_ids(playlist_id)
        |
        v
video IDs
```

---

## 3. Request-related error handling introduced

The function is wrapped in:

```python
try:
    ...
except requests.exceptions.RequestException as e:
    raise e
```

This introduces structured handling for failures related to the `requests` library.

`RequestException` is the general base exception used by `requests` for request-related problems.

The exception is re-raised so the failure is not silently hidden.

---

## 4. `if __name__ == "__main__":` introduced

The file now distinguishes between:

### Direct execution

```bash
python video_stats.py
```

In this case:

```python
__name__ == "__main__"
```

and the function is called.

### Importing the module

```python
import video_stats
```

In this case:

```python
__name__ == "video_stats"
```

so the function is defined and available, but it is not automatically executed.

This is useful for:

- Reusability
- Unit testing
- Future Airflow integration
- Importing functions from other modules
- Separating library logic from script execution

---

# Technical Flow

```text
Python starts video_stats.py
        |
        v
Imports requests and json
        |
        v
Defines configuration variables
        |
        v
Defines get_playlist_id()
        |
        v
Checks __name__
        |
        +-----------------------------+
        |                             |
        | Direct execution            | Imported module
        v                             v
__name__ == "__main__"          __name__ != "__main__"
        |                             |
        v                             v
Call get_playlist_id()          Do not auto-call function
        |
        v
Build channels.list URL
        |
        v
requests.get(url)
        |
        v
Parse JSON response
        |
        v
data["items"][0]
        |
        v
["contentDetails"]
        |
        v
["relatedPlaylists"]
        |
        v
["uploads"]
        |
        v
Return Uploads Playlist ID
```

---

# JSON Navigation

The important JSON path is:

```text
$["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
```

In Python, the root `$` corresponds to the parsed `data` variable:

```python
data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
```

Path breakdown:

| Expression | Meaning |
|---|---|
| `data` | Root parsed response |
| `["items"]` | Access the `items` list |
| `[0]` | Select the first channel result |
| `["contentDetails"]` | Access channel content details |
| `["relatedPlaylists"]` | Access related playlist metadata |
| `["uploads"]` | Retrieve the uploads playlist ID |

---

# Current Limitations

This implementation is cleaner than the first proof of concept, but it is not yet the finalized version.

## No `raise_for_status()`

The code currently sends:

```python
response = requests.get(url)
```

but does not yet call:

```python
response.raise_for_status()
```

Without it, an HTTP response such as `403`, `404`, or `500` does not automatically become an `HTTPError`.

A later improvement should use:

```python
response = requests.get(url)
response.raise_for_status()
```

This makes HTTP failures participate properly in the `RequestException` handling flow.

---

## API key still needs external configuration

The final version should not contain:

```python
API_KEY = "actual-secret-key"
```

The API key should be loaded from `.env` or an environment variable.

---

## No validation for an empty `items` list

The current code assumes:

```python
data["items"][0]
```

exists.

If the channel is not found, this could raise an `IndexError`.

A future version should validate that `items` contains at least one result before accessing index `0`.

---

## No timeout

The request currently uses:

```python
requests.get(url)
```

A more robust implementation should eventually specify a timeout:

```python
requests.get(url, timeout=30)
```

---

# Why This Version Is Worth Committing

This version represents a meaningful development milestone because it changes the code from a simple sequential proof of concept into a reusable software component.

The Git history can now show the evolution clearly:

```text
Implementation/Test 1
Basic API request and JSON inspection
        |
        v
Implementation/Test 2
Reusable get_playlist_id() function
+ try/except
+ return value
+ __name__ entry point
        |
        v
Future implementation
+ raise_for_status()
+ .env
+ validation
+ playlistItems.list
```

This is a good example of practical version control: each commit captures a meaningful stage of the implementation.

---

# Suggested Commit

After confirming that no real API key is present:

```bash
git add video_stats.py Markdowns/YouTube_API_Implementation_Test_2.md
git status
git commit -m "refactor playlist extraction into reusable function"
git push
```

If you want to stage all current safe changes:

```bash
git add .
git status
git commit -m "refactor playlist extraction into reusable function"
git push
```

---

# Next Step

The next logical improvement is to add:

```python
response.raise_for_status()
```

and then move the API key to `.env`.

After that, the extracted uploads playlist ID can be supplied to the YouTube Data API `playlistItems.list` endpoint to begin retrieving individual video IDs.
