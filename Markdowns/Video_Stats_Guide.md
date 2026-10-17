# Video Statistics Extraction

A guide to `3_video_stats.py`, based on the code inspected on 17 October 2026. The script now goes beyond video IDs: it collects selected metadata and statistics for the channel's available videos.

## 1. Flow overview

```text
.env API_KEY + CHANNEL_HANDLE = "MrBeast"
    ↓ get_playlist_id()
Uploads playlist ID — one string
    ↓ get_video_id(playlist_id), following response pages
Video IDs — list of strings
    ↓ extract_video_data(video_ids), requesting batches
Video records — list of dictionaries
    ↓ print(...)
Terminal output
```

| Function | Receives | Returns |
|---|---|---|
| `get_playlist_id()` | Reads the configured handle and key | One uploads playlist ID |
| `get_video_id(playlist_id)` | Playlist ID | Video ID list |
| `extract_video_data(video_ids)` | Video ID list | Video record list |
| Nested `batch_list(video_id_list, batch_size)` | A list and batch size | Yields one slice at a time |

The uploads playlist is maintained by YouTube for uploaded videos. It also contains videos organized into other playlists; it is not just an unsorted-video collection. The channel ID, uploads playlist ID, playlist-entry ID, and video ID identify different objects.

## 2. Configuration and shared request pattern

The imports serve these purposes:

| Import | Purpose in this version |
|---|---|
| `requests` | Send HTTP GET requests and check HTTP failures. |
| `os` | Read the API key through `os.getenv()`. |
| `load_dotenv` | Load configuration from `.env`. |
| `json` | Currently unused; available if formatted JSON output is added later. |
| `time` | Currently unused; importing it does not implement retries. |

```python
load_dotenv(dotenv_path="./.env")
API_KEY = os.getenv("API_KEY")
CHANNEL_HANDLE = "MrBeast"
maxResults = 50
```

`./.env` is relative to the terminal's working directory, so run from `YT_ELT`. The expected variable is `API_KEY`; if absent, `os.getenv()` returns `None`. By default, an existing environment variable takes precedence over its `.env` value.

`maxResults` is used in two ways: up to 50 playlist entries per page, and 50 known video IDs per details request. It does not cap the total number collected.

All requests follow this pattern:

```python
response = requests.get(url, timeout=(10, 30))
response.raise_for_status()
data = response.json()
```

1. Send a GET request and obtain a response object.
2. Raise an HTTP error for unsuccessful statuses such as `403` or `500`.
3. Parse the JSON body into Python dictionaries and lists.

The channel and playlist requests use `(10, 30)`; video-details requests use `(10, 60)`. The first value is the connection timeout; the second is the read inactivity timeout. It is not a deadline for downloading an entire batch or finishing the whole script.

## 3. Find the uploads playlist: `get_playlist_id()`

This function calls `/youtube/v3/channels` with:

| Parameter | Value | Reason |
|---|---|---|
| `part` | `contentDetails` | Retrieve related playlist information. |
| `forHandle` | `MrBeast` | Identify the channel. |
| `key` | Private API key | Identify the calling API project. |

The URL is constructed using adjacent strings and f-strings:

```python
url = (
    "https://youtube.googleapis.com/youtube/v3/channels"
    f"?part=contentDetails"
    f"&forHandle={CHANNEL_HANDLE}"
    f"&key={API_KEY}"
)
```

Parentheses let one expression span lines. The `f` prefix substitutes expressions inside `{...}`. The resulting URL uses `?` to start query parameters and `&` to separate them.

An abbreviated response, using placeholder IDs:

```json
{
  "items": [
    {
      "id": "CHANNEL_ID",
      "contentDetails": {
        "relatedPlaylists": {
          "uploads": "UPLOADS_PLAYLIST_ID"
        }
      }
    }
  ]
}
```

The code follows that structure:

```python
channel_items = data["items"][0]
channel_playlistID = (
    channel_items["contentDetails"]
    ["relatedPlaylists"]
    ["uploads"]
)
return channel_playlistID
```

`[0]` selects the first channel because Python indexes start at zero. Each string-key lookup enters a nested dictionary. The returned value is the uploads playlist ID, not the channel's own `id`. The commented-out `print` does nothing.

## 4. Collect IDs: `get_video_id(playlist_id)`

This function calls `/youtube/v3/playlistItems` with `part=contentDetails`, the playlist ID, a page size, and the API key.

Its simplified response can look like this. Tokens and playlist-entry IDs are illustrative:

```json
{
  "nextPageToken": "NEXT_PAGE_TOKEN",
  "items": [
    {
      "id": "PLAYLIST_ENTRY_ID",
      "contentDetails": {
        "videoId": "aNI2jv7lBPQ"
      }
    }
  ]
}
```

The function's logic is:

```python
video_ids = []
pageToken = None
```

The list persists across pages. `None` means the first request has no page token.

```python
while True:
    url = base_url
    if pageToken:
        url += f"&pageToken={pageToken}"
```

`while True` repeats until `break`. Resetting `url` avoids accumulating old token parameters. Later requests send the previous response's `nextPageToken` as `pageToken`.

After requesting and parsing each page:

```python
for item in data.get("items", []):
    video_id = item["contentDetails"]["videoId"]
    video_ids.append(video_id)

pageToken = data.get("nextPageToken")
if not pageToken:
    break
```

`.get("items", [])` supplies an empty list if the key is missing. `append()` adds one ID to the existing list. Use `contentDetails.videoId`: the playlist item's own `id` identifies an entry, not its video.

When no next token exists, `.get()` returns `None`, the loop ends, and `return video_ids` returns the accumulated list. Despite its singular function name, the result contains multiple IDs.

## 5. Fetch records: `extract_video_data(video_ids)`

### Split known IDs into batches

```python
extracted_data = []

def batch_list(video_id_list, batch_size):
    for video_id in range(0, len(video_id_list), batch_size):
        yield video_id_list[video_id:video_id + batch_size]
```

`batch_list` is defined inside `extract_video_data` for use there. `range(0, length, batch_size)` produces numeric start indexes such as `0`, `50`, and `100`. Here, the variable named `video_id` is actually an index, not an ID string.

The slice includes its start and excludes its end. `yield` returns one batch and pauses the generator until the next iteration requests another.

For example, five IDs with batch size two produce:

```text
[A, B] → [C, D] → [E]
```

### Request each batch

```python
for batch in batch_list(video_ids, maxResults):
    video_ids_str = ",".join(batch)
```

`join` converts a list such as `['id1', 'id2']` into `id1,id2`, the API's format for multiple video IDs.

The videos endpoint requests three sections:

```text
/youtube/v3/videos
?part=contentDetails&part=snippet&part=statistics
&id=id1,id2
&key=YOUR_API_KEY
```

The current code retains repeated `part` parameters from your successful test. Google's documented form is `part=contentDetails,snippet,statistics`; the repeated form was not established as the cause of the earlier network failure.

**Pagination and batching are different:** pagination discovers entries across server response pages; batching groups already-known IDs into requests for their video details. This function uses batching, not page tokens.

### Read the video response

This shortened JSON uses values from your previously supplied response; the counts are a past snapshot, not live results:

```json
{
  "items": [
    {
      "id": "aNI2jv7lBPQ",
      "snippet": {
        "title": "Giving $10,000 To A Random Subscriber",
        "publishedAt": "2026-10-09T16:00:01Z"
      },
      "contentDetails": {
        "duration": "PT40S"
      },
      "statistics": {
        "viewCount": "34443266",
        "likeCount": "952533",
        "commentCount": "23829"
      }
    }
  ]
}
```

The code unpacks each returned video:

```python
video_id = item["id"]
snippet = item["snippet"]
contentDetails = item["contentDetails"]
statistics = item["statistics"]
```

Here, `item["id"]` identifies the video itself because this response comes from **videos**, rather than **playlistItems**.

It then builds one dictionary:

```python
video_data = {
    "video_id": video_id,
    "title": snippet["title"],
    "publishedAt": snippet["publishedAt"],
    "duration": contentDetails["duration"],
    "viewCount": statistics.get("viewCount", None),
    "likeCount": statistics.get("likeCount", None),
    "commentCount": statistics.get("commentCount", None),
}
extracted_data.append(video_data)
```

| Output field | Meaning and retained type |
|---|---|
| `video_id` | Video identifier string. |
| `title` | Video title string. |
| `publishedAt` | Publication timestamp string; `Z` means UTC. |
| `duration` | ISO 8601 duration string; `PT40S` means 40 seconds. |
| `viewCount` | Views, retained as a string, or `None` if absent. |
| `likeCount` | Likes, retained as a string, or `None` if absent. |
| `commentCount` | Comments, retained as a string, or `None` if absent. |

No numeric or date conversions happen. Missing counts become `None`; missing required sections or directly indexed fields raise `KeyError`.

Finally, `return extracted_data` is **outside the batch loop**. All batches are processed before returning, and an empty input returns `[]`. This fixes the earlier indentation bug that returned after the first batch.

## 6. Main block and expected output

```python
if __name__ == "__main__":
    playlist_id = get_playlist_id()
    video_ids = get_video_id(playlist_id)
    print(extract_video_data(video_ids))
```

Direct execution sets `__name__` to `"__main__"`. The first return value feeds the second function; the second return value feeds the third. `print` displays the final return value only after extraction completes. There are no progress messages in this version.

From an activated PowerShell terminal in `YT_ELT`, run:

```powershell
python -B 3_video_stats.py
```

`-B` prevents bytecode-cache writes. The terminal output is a Python list of dictionaries, for example:

```python
[{'video_id': 'aNI2jv7lBPQ', 'title': 'Giving $10,000 To A Random Subscriber', 'publishedAt': '2026-10-09T16:00:01Z', 'duration': 'PT40S', 'viewCount': '34443266', 'likeCount': '952533', 'commentCount': '23829'}]
```

The actual list can contain many records. This is Python's printed representation, not a saved JSON document. In particular, Python `None` would appear as `null` only after JSON serialization. No output file or database load is implemented.

## 7. Reliability and practical limits

- Both earlier stages use a 30-second read timeout; video batches use 60 seconds. Each request gets its own timeout.
- There are **no retries**. Each `except RequestException` handler re-raises the failure; `raise e` does not try again.
- A connection reset and a timeout are different failures. Increasing a timeout does not directly fix a connection reset.
- If extraction fails on a later batch, the function raises instead of returning the partial list. Nothing has been saved to disk.
- The script assumes the API key and expected response fields exist; it does not validate an empty channel list.
- Returned records may be fewer than requested IDs if some videos are unavailable. IDs and records are not deduplicated by this code.

For scale, 1,007 IDs require 21 video batches at size 50. With 21 full/partial playlist pages and one channel request, that would be 43 HTTP requests in total, assuming no failures and the stated page sizes. The process can therefore take longer than a single Postman request.

## References

- [YouTube channels: uploads playlist information](https://developers.google.com/youtube/data/reference/rest/v3/channels)
- [YouTube playlistItems.list: pages and tokens](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list)
- [YouTube videos.list: request parameters](https://developers.google.com/youtube/data/reference/rest/v3/videos/list)
- [YouTube video resource: fields and statistics](https://developers.google.com/youtube/data/reference/rest/v3/videos)
- [Requests: timeouts](https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts)

Earlier guides: [Video ID Retrieval](Video_ID_Retrieval.md) · [Playlist ID Retrieval](Playlist_ID_Retrieval.md) · [Virtual Environment Guide](Virtual_Environment_Guide.md).
