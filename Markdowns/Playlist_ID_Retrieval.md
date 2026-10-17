# YouTube Uploads Playlist ID Retrieval

This guide explains the current `video_stats.py`, your successful VS Code test, and how to reproduce the API requests in Postman. It covers the discussion after virtual environments; activation details are in [Virtual Environment Guide](Virtual_Environment_Guide.md).

## 1. What the current script returns

**The function returns one string: the channel's uploads playlist ID. It does not return a channel ID or any statistics.**

Your VS Code screenshot shows this returned value:

```text
UUX6OQ3DkcsbYNE6H8uQQuVA
```

The current flow is:

```text
.env API key + channel handle "MrBeast"
    → channels.list request
    → channel contentDetails
    → relatedPlaylists.uploads
    → uploads playlist ID string
```

| Value | Returned by the current function? |
|---|---|
| Uploads playlist ID | Yes — one string |
| Channel ID | No |
| Individual video IDs or titles | No |
| Video views, likes, or comments | No |
| Video durations or publication dates | No |
| Channel subscribers, total views, or video count | No |

The filename describes the broader project goal. This implementation completes the discovery step needed before collecting individual video statistics.

## 2. Channel, playlist, and video IDs

A channel can have multiple playlists. Each playlist has its own ID, and each video also has its own ID.

YouTube maintains a special **uploads playlist** for a channel's uploaded videos. It is not just a collection of videos that have not been sorted into other playlists.

Adding a video to a creator-organized playlist does not remove it from uploads. The same video can appear in several playlists:

```text
Example Cooking Channel
├── Uploads playlist: Video A, Video B, Video C
├── Easy Breakfasts: Video A
└── Beginner Recipes: Video A, Video C
```

Playlists reference videos; they do not act like exclusive folders. Which entries and video details are accessible through the API depends on their availability and the request's authorization.

The channel response can include both a channel ID and an uploads playlist ID. This simplified example uses placeholders:

```json
{
  "items": [
    {
      "id": "EXAMPLE_CHANNEL_ID",
      "contentDetails": {
        "relatedPlaylists": {
          "uploads": "EXAMPLE_UPLOADS_PLAYLIST_ID"
        }
      }
    }
  ]
}
```

| Path | Identifies |
|---|---|
| `items[0]["id"]` | The channel |
| `items[0]["contentDetails"]["relatedPlaylists"]["uploads"]` | Its uploads playlist |

Your function selects the second path. The earlier example's `"id": "EXAMPLE_CHANNEL_ID"` was part of the surrounding response, not the value returned by your code.

## 3. Current code, explained in execution order

Line numbers refer to the file inspected for this guide. Comments beginning with `#` explain the code but do not execute. Blank lines provide visual spacing.

### Imports — lines 2, 6, 10, and 15

```python
import requests
import json
import os
from dotenv import load_dotenv
```

- `requests` is an external package used to send HTTP requests.
- `json` is Python's built-in JSON toolkit. This import is currently unused; `response.json()` does not depend on this separate import.
- `os` is built into Python. Here it reads environment variables.
- `load_dotenv` comes from the `python-dotenv` package, imported under the module name `dotenv`. Importing the function directly lets the script call `load_dotenv(...)`.

### Load `.env` — line 23

```python
load_dotenv(dotenv_path="./.env")
```

This reads configuration from `.env` in the **current working directory**. Therefore, run the script from the `YT_ELT` folder.

The expected variable name is illustrated below; the value is a placeholder:

```dotenv
API_KEY=YOUR_API_KEY
```

Loading the file makes its variables available to the Python process. It does not rewrite `.env`. By default, an existing environment variable takes precedence over a value loaded from the file.

The `.env` configuration file and the `venv` Python environment are different things. Activating `venv` does not automatically load `.env`; this line handles that step.

### Read the key — line 29

```python
API_KEY = os.getenv("API_KEY")
```

`os.getenv("API_KEY")` looks up that environment variable. The Python variable on the left receives its value as a string, or `None` if it is missing.

The current script does not check for a missing key. Keeping it outside the source file avoids embedding it in Python code; excluding `.env` from Git requires appropriate ignore rules separately.

### Choose the channel — line 33

```python
CHANNEL_HANDLE = "MrBeast"
```

This is the handle used to identify the channel. The API's `forHandle` parameter accepts a handle with or without `@`. Uppercase variable names indicate configuration by convention; Python does not enforce them as constants.

### Define the function — line 37

```python
def get_playlist_id():
```

`def` defines a reusable function. It declares no input parameters, but reads the module-level `CHANNEL_HANDLE` and `API_KEY` variables. The colon starts its indented body.

Defining the function does not send the API request. Calling `get_playlist_id()` executes its body.

### Start error handling — line 39

```python
try:
```

Python attempts the operations inside this block. If an exception occurs, it checks whether the later `except` clause matches that exception's type.

### Build the URL — lines 51–56

```python
url = (
    "https://youtube.googleapis.com/youtube/v3/channels"
    f"?part=contentDetails"
    f"&forHandle={CHANNEL_HANDLE}"
    f"&key={API_KEY}"
)
```

| Line | Meaning |
|---|---|
| 51 | Begin assigning the URL expression to `url`. |
| 52 | Specify the channel API endpoint. |
| 53 | Request the channel's `contentDetails` section. |
| 54 | Insert the selected channel handle. |
| 55 | Insert the API key. |
| 56 | Close the expression. |

Adjacent strings combine into one string. Parentheses allow the expression to span lines; they do not create a list. The `f` prefix enables substitution of expressions inside `{...}`. Line 53 has no substitution, so its `f` is unnecessary but harmless.

The URL has this shape, with the key deliberately replaced:

```text
https://youtube.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle=MrBeast&key=YOUR_API_KEY
```

`?` starts the query parameters; `&` separates additional parameters. **`part=contentDetails` requests playlist-related information, not statistics.** Building the URL itself makes no network call.

### Send the request — line 61

```python
response = requests.get(url)
```

This sends an HTTP GET request and waits for its response. The resulting `Response` object contains the status code, headers, and body. This is the line that contacts YouTube.

The request currently has no explicit timeout and does not call `response.raise_for_status()` to raise an exception for unsuccessful HTTP statuses.

### Parse JSON — line 66

```python
data = response.json()
```

This parses the response body into Python objects. JSON objects become dictionaries, arrays become lists, and strings become Python strings.

Parsing is not proof of API success: an error response can also contain valid JSON. This method does not save anything to `video_stats.json`; the current script contains no file-writing operation.

### Select the channel — line 71

```python
channel_items = data["items"][0]
```

`data["items"]` retrieves the result list. `[0]` selects its first element because Python indexes start at zero. Despite its plural name, `channel_items` now holds one channel dictionary.

If `items` is missing, this raises `KeyError`. If the list is empty, selecting `[0]` raises `IndexError`.

### Extract the uploads playlist ID — lines 82–86

```python
channel_playlistID = (
    channel_items["contentDetails"]
    ["relatedPlaylists"]
    ["uploads"]
)
```

Line 82 starts the assignment. Line 83 selects the content details dictionary, line 84 selects its related playlists dictionary, and line 85 retrieves the uploads ID. Line 86 closes the expression.

It is equivalent to:

```python
channel_playlistID = channel_items["contentDetails"]["relatedPlaylists"]["uploads"]
```

The result is one ID string, not the playlist's video entries.

### Disabled display — line 91

```python
# print(f"Channel Playlist ID: {channel_playlistID}")
```

The leading `#` makes this a comment. It produces no output. If enabled, it would display the ID, but no source modification is needed for the testing methods below.

### Return the ID — line 95

```python
return channel_playlistID
```

This ends the function and passes the string back to the caller.

| Operation | Purpose |
|---|---|
| `return value` | Give a value to calling code. |
| `print(value)` | Display a value for the person using the terminal. |
| `playlist_id = get_playlist_id()` | Store the returned value for reuse. |

### Re-raise matching exceptions — lines 100–103

```python
except requests.exceptions.RequestException as e:
    raise e
```

The handler catches request-related exceptions, such as connection failures, and assigns the exception to `e`. `raise e` raises it again. There is no retry or fallback; an uncaught exception ends execution with a traceback.

This handler does not catch `KeyError` or `IndexError`. Also, an HTTP error such as `403` does not automatically become an `HTTPError` here because `raise_for_status()` is never called. The code may instead parse an error body and fail when looking for `items`.

### Direct execution — lines 108–111

```python
if __name__ == "__main__":
    get_playlist_id()
```

When run as `python video_stats.py`, Python sets `__name__` to `"__main__"`, making this condition true. The function runs, but the caller neither stores nor prints its return value. **A successful direct run therefore normally produces no output.**

### Import behavior — lines 113–115

```python
else:
    print("get_playlist_id() function is not being called")
```

On a normal first import, the module's `__name__` is `"video_stats"`. The `else` branch prints this message. Imports, configuration loading, and function definition still execute, but the function's API request does not run automatically.

Another command can call the function afterward. The import message does not mean the function is unavailable or that it cannot be called later.

## 4. Run and test without editing the source

Open a PowerShell terminal in VS Code. Run commands below without copying the prompt text such as `PS ...>` or `>>>`.

### Normal script run

```powershell
Set-Location "F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT"
.\venv\Scripts\Activate.ps1
python -B video_stats.py
```

`-B` prevents Python from writing `.pyc` bytecode cache files. Successful execution normally returns silently to the terminal prompt. Silence alone is not an independent verification of the returned value; use the test below to inspect it.

### Interactive test — the method shown in your screenshots

Start Python from PowerShell:

```powershell
python -B
```

The Python version banner appears, followed by the `>>>` prompt. You are now entering Python code, not PowerShell commands.

Enter these commands individually:

```python
import video_stats
playlist_id = video_stats.get_playlist_id()
print(playlist_id)
print(type(playlist_id))
```

Your screenshots show the following sequence:

| Command or output | Explanation |
|---|---|
| `Python 3.13.5 ...` | Python started successfully; this is the interpreter banner. |
| `import video_stats` | Load the module and execute its top-level setup. |
| `get_playlist_id() function is not being called` | The import's `else` branch printed its message. This is expected, not an error. |
| `playlist_id = video_stats.get_playlist_id()` | Explicitly call the function, make the request, and store its return value. Assignment does not print it. |
| `print(playlist_id)` | Display the stored string. |
| `UUX6OQ3DkcsbYNE6H8uQQuVA` | The uploads playlist ID actually returned in your test. |
| `print(type(playlist_id))` | Ask Python for the stored value's type. |
| `<class 'str'>` | Confirm it is a string. |
| Final `>>>` | Python is ready for another command; no traceback is shown. |

This confirms the displayed call reached the extraction and return steps successfully. It does not mean statistics or video entries have been fetched.

Both new attachments show this VS Code test. **Neither includes a Postman response body**, so no live Postman counts or status can be confirmed from them. The earlier Postman screenshot showed a configured request, not a response.

You can reuse the variable in this same Python session:

```python
print(f"https://www.youtube.com/playlist?list={playlist_id}")
```

This prints a playlist URL without making another API request. To leave Python:

```python
exit()
```

The variable exists only in this session and is not saved to disk.

### One-command display alternative

From PowerShell, with the environment active:

```powershell
python -B -c "import video_stats; print(video_stats.get_playlist_id())"
```

`-c` executes the Python code inside the quotation marks. Expect the import message followed by the returned playlist ID on success.

## 5. Postman: reproduce the playlist ID retrieval

Create a **GET** request with this base URL:

```text
https://youtube.googleapis.com/youtube/v3/channels
```

In **Params**, add and enable:

| Key | Value |
|---|---|
| `part` | `contentDetails` |
| `forHandle` | `MrBeast` |
| `key` | Your private API key |

For these API-key examples, select **No Auth** in Authorization and leave the body empty. Click **Send**.

For a successful matching response, inspect:

```text
items → first item → contentDetails → relatedPlaylists → uploads
```

That value should match the Python result for the same channel. The channel object's own `id` identifies the channel instead.

## 6. Postman: use the playlist ID to get video IDs

Create a separate **GET** request:

```text
https://youtube.googleapis.com/youtube/v3/playlistItems
```

| Key | Value |
|---|---|
| `part` | `snippet,contentDetails` |
| `playlistId` | `UUX6OQ3DkcsbYNE6H8uQQuVA` |
| `maxResults` | `50` |
| `key` | Your private API key |

Click **Send**. For each returned item, inspect:

```text
items → an item → contentDetails → videoId
```

**Use `contentDetails.videoId`, not the playlist item's own `id`.** The latter identifies the entry in the playlist.

`maxResults=50` requests up to 50 entries for this page, not every video in a large channel. If the response includes `nextPageToken`, send another request with `pageToken` set to that value. Repeat until no next page token is returned.

## 7. Postman: retrieve statistics for a video

Your earlier screenshot configured this separate **GET** endpoint:

```text
https://youtube.googleapis.com/youtube/v3/videos
```

| Key | Value |
|---|---|
| `part` | `statistics` |
| `id` | `0e3GPea1Tyg`, or a video ID from the previous step |
| `key` | Your private API key |

The value `0e3GPea1Tyg` is a **video ID**. Do not put an uploads playlist ID into this endpoint's `id` parameter.

Click **Send**. For an accessible matching video, a valid key, and a successful request, expect `200 OK` and a response shaped like this. Counts below are illustrative, not observed results:

```json
{
  "kind": "youtube#videoListResponse",
  "items": [
    {
      "kind": "youtube#video",
      "id": "0e3GPea1Tyg",
      "statistics": {
        "viewCount": "123456",
        "likeCount": "7890",
        "favoriteCount": "0",
        "commentCount": "456"
      }
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `items[0].id` | The returned video ID |
| `statistics.viewCount` | Views of this video |
| `statistics.likeCount` | Likes on this video |
| `statistics.commentCount` | Comments on this video |
| `statistics.favoriteCount` | Deprecated; not a useful current metric |

Some statistics may be absent. Counts are represented as JSON strings, and these are individual video counts rather than channel totals. A `200 OK` response with an empty `items` array means no matching accessible video resource was returned; there are no statistics to extract from it.

To include the video's title and publication date, change `part` to `snippet,statistics`. For duration as well, use `snippet,contentDetails,statistics`.

## 8. What is complete, and what remains

```text
Channel handle
    ↓ channels.list
Uploads playlist ID                 ← Current Python function ends here
    ↓ playlistItems.list + pagination
Video IDs
    ↓ videos.list
Video details and statistics
```

Testing later endpoints in Postman does not add those operations to `video_stats.py`. The current script has no requests for playlist entries or video statistics, no file output, and no database-loading step.

Current limitations to recognize when troubleshooting:

- No check for a missing API key.
- No explicit request timeout.
- No `raise_for_status()` check for HTTP errors.
- No validation that `items` exists and contains a channel.
- Request exceptions are re-raised rather than recovered from.
- Direct execution discards the function's return value instead of displaying or storing it.

These describe the existing code; this guide does not change it.

## References

- [YouTube channels: uploads playlist field](https://developers.google.com/youtube/data/reference/rest/v3/channels#contentDetails.relatedPlaylists.uploads)
- [YouTube channels.list: channel lookup](https://developers.google.com/youtube/data/reference/rest/v3/channels/list)
- [YouTube playlistItems.list: playlist entries and pagination](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list)
- [YouTube videos.list: request video resources](https://developers.google.com/youtube/data/reference/rest/v3/videos/list)
- [YouTube video resource: statistics and details](https://developers.google.com/youtube/data/reference/rest/v3/videos)

API keys are intentionally omitted from this guide. The key previously shared in the URL and screenshot should be replaced in Google Cloud and the replacement kept private.
