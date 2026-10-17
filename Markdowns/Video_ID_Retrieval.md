# YouTube Video ID Retrieval

This guide explains `video_stats.py` as inspected on 16 October 2026. The current version uses consistent pagination variables, requests up to 50 entries per page, and sets timeouts on both HTTP requests.

## 1. What the script achieves

**Given a channel handle, the script discovers its uploads playlist and returns the video IDs from the available playlist pages.** Running the script prints the resulting Python list.

```text
"MrBeast"
    │ channels.list — identify the uploads playlist
    ▼
Uploads playlist ID: one string
    │ playlistItems.list — retrieve entries, page by page
    ▼
Video IDs: a list of strings
```

There are two functions:

| Function | Input | Return value |
|---|---|---|
| `get_playlist_id()` | Uses the configured channel handle and API key | One uploads playlist ID string |
| `get_video_id(playlist_id)` | An uploads playlist ID | A list of video ID strings |

Despite its singular name, `get_video_id()` collects multiple IDs. Your previous pasted output contained **1,007 IDs, all unique**, with every value matching the expected 11-character video ID format. That was the result of that test, not a fixed count guaranteed for future runs.

The script does **not yet retrieve views, likes, comments, titles, or durations**. It also does not write to `video_stats.json` or a database.

### Why use an uploads playlist?

A channel has its own ID and can have many playlists, each with a different ID. YouTube maintains an uploads playlist for the channel's uploaded videos. It includes videos that also appear in creator-organized playlists; it is not a collection of only unsorted videos.

The same video can appear in both uploads and a themed playlist. Playlists reference videos rather than moving them into exclusive folders. API visibility and access still depend on the videos and authorization used.

## 2. Setup and the first request

Line numbers below match the inspected source. Comments (`# ...`) explain the code but do not execute; blank lines provide spacing.

### Imports and configuration

| Line | Code | Explanation |
|---|---|---|
| 2 | `import requests` | Load the external package that sends HTTP requests. |
| 6 | `import json` | Load Python's JSON toolkit; this import is currently unused. |
| 10 | `import os` | Load built-in operating-system utilities, used here to read environment variables. |
| 15 | `from dotenv import load_dotenv` | Import the configuration loader from the `python-dotenv` package. |
| 23 | `load_dotenv(dotenv_path="./.env")` | Load `.env` from the current working folder into this process's environment. |
| 29 | `API_KEY = os.getenv("API_KEY")` | Read the key as a string, or `None` if missing. |
| 33 | `CHANNEL_HANDLE = "MrBeast"` | Choose the channel for the first request. |
| 35 | `maxResults = 50` | Set the maximum number of playlist entries per page, not the total number to collect. |

Run from `YT_ELT` so `./.env` resolves to the intended file. The expected configuration name is `API_KEY`. By default, `load_dotenv()` does not overwrite an environment variable that already exists.

The `.env` configuration file and `venv` Python environment serve different purposes: activating `venv` chooses Python and its packages; `load_dotenv()` loads configuration values. No real key is included in this guide.

### `get_playlist_id()` — lines 39–107

```python
def get_playlist_id():
    try:
        url = (
            "https://youtube.googleapis.com/youtube/v3/channels"
            f"?part=contentDetails"
            f"&forHandle={CHANNEL_HANDLE}"
            f"&key={API_KEY}"
        )
```

- **39:** Define the function. It declares no parameters and reads the module-level configuration. Defining it does not make a request; calling it does.
- **41:** Begin a block whose request-related exceptions are handled below.
- **53:** Start assigning the URL expression to `url`.
- **54:** Select the channels endpoint.
- **55:** Request `contentDetails`, which contains the related playlist information.
- **56:** Insert the channel handle using an f-string: `{CHANNEL_HANDLE}` becomes its value.
- **57:** Insert the API key.
- **58:** Close the expression. Adjacent strings form one URL; parentheses allow multiple lines.

In the URL, `?` starts query parameters and `&` separates them. Constructing the string does not contact YouTube.

```python
response = requests.get(url, timeout=(10, 30))
response.raise_for_status()
data = response.json()
channel_items = data["items"][0]
```

- **63:** Send the GET request. The tuple sets connection and read timeouts of 10 and 30 seconds. The read timeout limits waiting for incoming data; it is not a total runtime limit for the script.
- **66:** Raise an HTTP error for unsuccessful statuses such as `403` or `500`.
- **70:** Parse the response JSON into Python dictionaries and lists. This uses the response object's method, not the unused `json` import.
- **75:** Read the `items` list and select its first channel. Python indexes begin at zero. Despite its plural name, `channel_items` holds one dictionary.

Here is a simplified response with illustrative IDs:

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

The remaining extraction is:

```python
channel_playlistID = (
    channel_items["contentDetails"]
    ["relatedPlaylists"]
    ["uploads"]
)
return channel_playlistID
```

- **86:** Begin assigning the extracted value.
- **87:** Enter the channel's `contentDetails` dictionary.
- **88:** Enter its `relatedPlaylists` dictionary.
- **89:** Retrieve the uploads playlist ID string.
- **90:** Close the expression.
- **95:** The optional `print(...)` is commented out and displays nothing.
- **99:** Return the playlist ID to the caller. This is different from the channel's own `id`.
- **104:** Catch a `requests.exceptions.RequestException` as `e`.
- **107:** Re-raise it. There is no retry or fallback; the failure remains visible to the caller.

## 3. The second request and its JSON

`get_video_id(playlist_id)` calls the **playlistItems** endpoint. It retrieves entries in that playlist, with the underlying video ID inside each entry's `contentDetails`.

For readability, this illustrative response contains two entries and omits unrelated fields:

```json
{
  "kind": "youtube#playlistItemListResponse",
  "nextPageToken": "EXAMPLE_NEXT_TOKEN",
  "pageInfo": {
    "totalResults": 3,
    "resultsPerPage": 2
  },
  "items": [
    {
      "id": "EXAMPLE_PLAYLIST_ENTRY_1",
      "contentDetails": {
        "videoId": "Y8IJi7iP5vk",
        "videoPublishedAt": "2026-10-16T16:00:02Z"
      }
    },
    {
      "id": "EXAMPLE_PLAYLIST_ENTRY_2",
      "contentDetails": {
        "videoId": "aNI2jv7lBPQ"
      }
    }
  ]
}
```

| Field | Meaning and use |
|---|---|
| `items` | Entries returned on this page; the code loops over them. |
| `items[i].id` | ID of the playlist entry, not the video. The code does not extract it. |
| `items[i].contentDetails.videoId` | The video ID that the code collects. |
| `videoPublishedAt` | Video publication timestamp, if returned; the code ignores it. `Z` means UTC. |
| `nextPageToken` | Opaque value used to request the next page. Do not calculate or modify it. |
| `pageInfo` | Paging metadata; the code does not use it to control the loop. |

JSON objects become Python dictionaries, arrays become lists, and JSON strings become Python strings. Thus `item["contentDetails"]["videoId"]` follows dictionary keys to reach one ID.

## 4. `get_video_id()` line by line

### Prepare the collection and request — lines 110–117

```python
def get_video_id(playlist_id):
    video_ids = []
    pageToken = None
```

- **110:** Define the function and its `playlist_id` input parameter.
- **111:** Create an empty list to accumulate IDs across all pages.
- **113:** Set `pageToken` to `None`. The first request needs no page token.

Line **115** builds the base URL with these parameters:

| Part | Purpose |
|---|---|
| `/youtube/v3/playlistItems` | Retrieve playlist entries. |
| `part=contentDetails` | Include the section containing each entry's video ID. |
| `maxResults={maxResults}` | Request up to 50 entries per page in the current code. |
| `playlistId={playlist_id}` | Select the uploads playlist returned by the first function. |
| `key={API_KEY}` | Supply the API key. |

Line **117** starts the request exception-handling block.

### Fetch one page — lines 118–124

```python
while True:
    url = base_url
    if pageToken:
        url += f"&pageToken={pageToken}"
    response = requests.get(url, timeout=(10, 30))
    response.raise_for_status()
    data = response.json()
```

| Line | Explanation |
|---|---|
| 118 | Repeat until an explicit `break` ends the loop. |
| 119 | Start from the clean base URL on every iteration, avoiding accumulated token parameters. |
| 120 | Check whether a next-page token is available. `None` is false, so the first request skips this block. |
| 121 | Append that token under YouTube's `pageToken` query parameter. |
| 122 | Fetch this page with connection/read timeouts. |
| 123 | Check for HTTP error statuses. |
| 124 | Parse this page's JSON response. |

### Extract and accumulate IDs — lines 126–128

```python
for item in data.get("items", []):
    video_id = item["contentDetails"]["videoId"]
    video_ids.append(video_id)
```

- **126:** Iterate over this page's entries. `.get("items", [])` supplies an empty list if the key is absent, causing the loop to do nothing.
- **127:** Extract one video's ID from the nested dictionaries.
- **128:** Append it to the accumulating list. This does not clear earlier pages or remove duplicates.

For the example JSON, the list becomes:

```python
['Y8IJi7iP5vk', 'aNI2jv7lBPQ']
```

### Advance or finish — lines 130–138

```python
pageToken = data.get("nextPageToken")

if not pageToken:
    break

return video_ids
```

- **130:** Store the next-page token. If the key is absent, `.get()` returns `None`.
- **132:** Test whether no usable next token remains.
- **133:** Exit the `while` loop when there is no next page.
- **135:** Return the accumulated list after the loop finishes. Its indentation places it outside `while`, so it does not return after each page.
- **137–138:** Catch request-related exceptions and re-raise them, with no retry or partial-result return.

For the illustrative three-entry playlist:

```text
Request 1: no pageToken → two IDs + nextPageToken
Request 2: send that token → one more ID + no nextPageToken
Finish: return a list containing all three collected IDs
```

**`maxResults` limits each page, not the final list.** At 50 entries per page, 1,007 entries would take 21 playlist requests if the first 20 pages were full, plus the initial channel request.

The earlier bug used `page_token` in some places and `pageToken` in others. Those are different Python variables. The current code consistently uses `pageToken`; YouTube's response key remains `nextPageToken`.

## 5. How execution starts and what prints

```python
if __name__ == "__main__":
    playlist_id = get_playlist_id()
    print(get_video_id(playlist_id))
```

- **143:** Run this block when the file is executed directly. A normal import defines the functions and loads configuration but does not execute this block. The current version has no import-message `else` branch.
- **144:** Call the first function and store its returned playlist ID.
- **145:** Pass that ID to the second function, wait for its entire list, then print the list.

`return` supplies a value to calling code; `print` displays it. Because the print waits for all pages, a large retrieval can be quiet for a while. The current file contains no progress printing.

From an activated PowerShell terminal in `YT_ELT`, run:

```powershell
python -B video_stats.py
```

`-B` prevents bytecode cache writes. On success, expect a list such as:

```python
['Y8IJi7iP5vk', 'aNI2jv7lBPQ', 'plN7JMbadRg', ...]
```

The ellipsis above abbreviates the example; your actual printed list contains the collected strings. There are no statistics attached to them yet.

## 6. What your API screenshots demonstrate

The API Explorer screenshot configures `playlistItems.list` with `part=contentDetails` and `maxResults=1`. It shows a generated request, not a successful response. The displayed Bearer token is an authorization template; your script supplies an API key for its public-data request.

The Postman screenshot uses the same endpoint with `maxResults=2`, your uploads playlist ID, and a key. It shows **200 OK**, approximately **436 ms**, and **1.15 KB** for that single response. These describe that request, not the runtime or size of the whole Python retrieval.

Its first visible entry contains:

```json
{
  "contentDetails": {
    "videoId": "Y8IJi7iP5vk",
    "videoPublishedAt": "2026-10-16T16:00:02Z"
  }
}
```

That video ID matches the first ID in your previously pasted Python output. The timestamp represents 19:00:02 in Asia/Amman's UTC+3 timezone. The code extracts the ID and ignores the timestamp.

Postman displays one response page per Send action. Python follows `nextPageToken` automatically, which explains why its final list contains much more than the two entries requested per page in that Postman test.

## 7. Limits and the next stage

The current code does not validate a missing API key or an empty channel result. Missing nested fields can raise `KeyError`, and an empty channel list can raise `IndexError`; the request exception handlers do not catch those errors. The list also preserves duplicates if the API returns any.

A `KeyboardInterrupt` means execution was interrupted, usually with Ctrl+C. A traceback ending in an SSL read shows where Python was waiting; it does not by itself establish an SSL certificate error. The added timeouts limit network waiting, not total pagination duration.

The next stage would pass these video IDs to `/youtube/v3/videos` with `part=statistics` to retrieve counts such as views, likes, and comments. Titles/publication dates require `snippet`; duration requires `contentDetails`. Requesting `contentDetails` on **playlistItems**, as the current code does, describes playlist entries rather than video durations.

## References

- [YouTube channel resource and uploads playlist](https://developers.google.com/youtube/data/reference/rest/v3/channels)
- [YouTube playlistItems.list parameters and pagination](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list)
- [YouTube video resource and statistics](https://developers.google.com/youtube/data/reference/rest/v3/videos)
- [Requests: timeout behavior](https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts)

For the earlier discovery stage, see [Playlist ID Retrieval](Playlist_ID_Retrieval.md). For environment activation, see [Virtual Environment Guide](Virtual_Environment_Guide.md).
