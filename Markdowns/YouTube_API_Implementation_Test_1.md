# YouTube Data API Extraction — Implementation/Test 1

## Overview

This implementation is the first working proof of concept for extracting data from a YouTube channel using the **YouTube Data API v3** with Python.

The current objective is to start from a human-readable YouTube channel handle such as `@MrBeast`, call the YouTube API, inspect the returned channel metadata, and extract the channel's special **Uploads Playlist ID**.

The extracted playlist ID is not the list of videos itself. It is a reference to YouTube's system-managed uploads playlist for that channel. A later API request will use this ID to enumerate the uploaded videos.

---

## Functional Purpose

The current code performs the following flow:

```text
@MrBeast
    |
    | channels.list
    v
YouTube channel metadata
    |
    | contentDetails
    v
relatedPlaylists
    |
    | uploads
    v
Uploads Playlist ID
UUX6OQ3DkcsbYNE6H8uQQuVA
```

The value:

```text
UUX6OQ3DkcsbYNE6H8uQQuVA
```

is the ID of MrBeast's special uploads playlist.

It does **not** itself contain all video details. It acts as the identifier that will be supplied to the next API operation.

The broader extraction flow is:

```text
@MrBeast
    |
    | channels.list
    v
Uploads Playlist ID
    |
    | playlistItems.list
    v
Video IDs
    |
    | videos.list
    v
Video details and statistics
```

Eventually, the project is intended to retrieve fields such as:

- Video ID
- Title
- Published date/time
- Duration
- View count
- Like count
- Comment count

This implementation completes only the **first discovery step**: resolving a channel handle to its uploads playlist ID.

---

# 1. Current Code

```python
import requests
import json

# API key used to identify/authorize the Google Cloud project
# when calling the YouTube Data API.
#
# IMPORTANT:
# Do not commit a real API key to GitHub.
# Replace this hard-coded value with an environment variable
# or .env-based configuration before publishing the code.
API_KEY = "YOUR_API_KEY"

# YouTube channel handle to query.
# This corresponds to @MrBeast on YouTube.
CHANNEL_HANDLE = "MrBeast"

# Build the YouTube Data API channels.list request.
#
# Endpoint:
#   /youtube/v3/channels
#
# Query parameters:
#   part=contentDetails
#       Requests the part of the channel resource containing
#       related playlist information.
#
#   forHandle=MrBeast
#       Identifies the channel using its public YouTube handle.
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
# The result is a requests.Response object.
response = requests.get(url)

# Print the numeric HTTP status code.
# A successful request normally returns 200.
print(response.status_code)

# Print the Response object itself.
# A successful request normally appears as:
# <Response [200]>
print(response)

# Parse the JSON response body into native Python objects.
#
# JSON objects -> Python dictionaries
# JSON arrays  -> Python lists
data = response.json()

# Pretty-print the full parsed response so its nested
# structure can be inspected during this proof-of-concept stage.
print(json.dumps(data, indent=4))

# JSONCrack path:
# $["items"][0]["contentDetails"]["relatedPlaylists"]
#
# Path breakdown:
# $                    -> root of the JSON response
# ["items"]            -> access the "items" property; value is an array/list
# [0]                  -> select the first item in that list
# ["contentDetails"]   -> access the contentDetails object
# ["relatedPlaylists"] -> access the relatedPlaylists object
#
# In Python, the JSON root "$" corresponds to the `data` variable.
related_playlists = data["items"][0]["contentDetails"]["relatedPlaylists"]

# Print the relatedPlaylists dictionary.
print(related_playlists)

# Access the "uploads" key inside the relatedPlaylists dictionary.
# Its value is the channel's uploads playlist ID.
uploads_playlist_id = related_playlists["uploads"]

# Print the final value needed for the next extraction stage.
print(uploads_playlist_id)
```

---

# 2. Libraries Used

## `requests`

`requests` is a Python HTTP client library. It allows the script to communicate with the YouTube Data API using HTTP requests.

```python
response = requests.get(url)
```

Conceptually:

```text
Python script
    |
    | HTTP GET
    v
YouTube Data API
    |
    | HTTP response
    v
requests.Response object
```

The returned `Response` object contains information such as:

- HTTP status code
- Response headers
- Response body
- Encoding
- Requested URL

## `json`

Python's built-in `json` module is used mainly to make the response easier to inspect.

```python
print(json.dumps(data, indent=4))
```

This converts the parsed Python object into formatted JSON-style text and is primarily a development/debugging aid.

---

# 3. API Configuration

The current implementation uses:

```python
API_KEY = "YOUR_API_KEY"
CHANNEL_HANDLE = "MrBeast"
```

## `CHANNEL_HANDLE`

```python
CHANNEL_HANDLE = "MrBeast"
```

identifies the YouTube channel to query and corresponds to `@MrBeast`.

Using a variable makes the code reusable for another channel later.

## `API_KEY`

The API key identifies the Google Cloud project making the request to the YouTube Data API.

A real API key should **not** be committed to GitHub.

A later implementation should load it from an environment variable or `.env` file.

Example:

```env
YOUTUBE_API_KEY=your_actual_key_here
```

The repository's `.gitignore` should contain:

```gitignore
.env
```

so the secret remains local and is not version-controlled.

---

# 4. Constructing the API Request

The request URL is built as:

```python
url = (
    "https://youtube.googleapis.com/youtube/v3/channels"
    f"?part=contentDetails"
    f"&forHandle={CHANNEL_HANDLE}"
    f"&key={API_KEY}"
)
```

Conceptually:

```text
https://youtube.googleapis.com/youtube/v3/channels
    ?part=contentDetails
    &forHandle=MrBeast
    &key=<API_KEY>
```

It consists of an API endpoint and query parameters.

## Endpoint

```text
/youtube/v3/channels
```

This selects the YouTube Data API **Channels resource**.

The operation being used is effectively:

```text
channels.list
```

## `part=contentDetails`

Requests the section of the channel resource that contains:

```text
contentDetails
    |
    v
relatedPlaylists
    |
    v
uploads
```

## `forHandle=MrBeast`

Identifies the target channel by its public handle.

## `key=API_KEY`

Supplies the API key associated with the Google Cloud project.

---

# 5. Sending the HTTP Request

The request is sent using:

```python
response = requests.get(url)
```

This performs an HTTP `GET` request.

The API request does **not scrape the normal YouTube webpage**. It communicates directly with the YouTube Data API and receives structured JSON data.

```text
YouTube Website
    -> Human-facing interface

YouTube Data API
    -> Programmatic interface
```

---

# 6. Checking the HTTP Response

The code prints:

```python
print(response.status_code)
```

A successful request normally returns:

```text
200
```

HTTP `200` means:

```text
200 OK
```

The code also prints:

```python
print(response)
```

which typically produces:

```text
<Response [200]>
```

These checks confirm that the API request is reaching YouTube successfully.

---

# 7. Parsing the JSON Response

The response body is parsed with:

```python
data = response.json()
```

YouTube returns JSON, which Python converts into native structures.

| JSON Type | Python Type |
|---|---|
| Object | `dict` |
| Array | `list` |
| String | `str` |
| Number | `int` / `float` |
| Boolean | `bool` |

So `data` becomes a Python dictionary containing nested dictionaries and lists.

---

# 8. Pretty-Printing the Response

The code uses:

```python
print(json.dumps(data, indent=4))
```

The flow is:

```text
JSON response body
    |
    | response.json()
    v
Python dictionaries/lists
    |
    | json.dumps(..., indent=4)
    v
Readable JSON-style output
```

This makes the nested response easier to understand before writing extraction logic.

---

# 9. Relevant JSON Response

A simplified relevant response is:

```json
{
    "kind": "youtube#channelListResponse",
    "pageInfo": {
        "totalResults": 1,
        "resultsPerPage": 5
    },
    "items": [
        {
            "id": "UCX6OQ3DkcsbYNE6H8uQQuVA",
            "contentDetails": {
                "relatedPlaylists": {
                    "likes": "",
                    "uploads": "UUX6OQ3DkcsbYNE6H8uQQuVA"
                }
            }
        }
    ]
}
```

Hierarchy:

```text
Root
|
+-- kind
|
+-- pageInfo
|
+-- items
    |
    +-- [0]
        |
        +-- id
        |
        +-- contentDetails
            |
            +-- relatedPlaylists
                |
                +-- likes
                |
                +-- uploads
                    |
                    +-- UUX6OQ3DkcsbYNE6H8uQQuVA
```

---

# 10. Understanding the JSONCrack Path

JSONCrack shows:

```text
$["items"][0]["contentDetails"]["relatedPlaylists"]
```

| Component | Meaning |
|---|---|
| `$` | Root of the JSON document |
| `["items"]` | Access the `items` property |
| `[0]` | Select the first element in the `items` array |
| `["contentDetails"]` | Access the `contentDetails` object |
| `["relatedPlaylists"]` | Access the `relatedPlaylists` object |

In Python, `$` corresponds to:

```python
data
```

Therefore:

```text
$["items"][0]["contentDetails"]["relatedPlaylists"]
```

becomes:

```python
data["items"][0]["contentDetails"]["relatedPlaylists"]
```

---

# 11. Dictionary Keys vs List Indexes

```python
data["items"][0]["contentDetails"]["relatedPlaylists"]
```

moves through both dictionaries and lists.

```text
data
 |
 | ["items"]             dictionary key lookup
 v
items list
 |
 | [0]                   list index
 v
first channel dictionary
 |
 | ["contentDetails"]    dictionary key lookup
 v
contentDetails dictionary
 |
 | ["relatedPlaylists"]  dictionary key lookup
 v
relatedPlaylists dictionary
```

Dictionary lookup:

```python
dictionary["key"]
```

List lookup:

```python
list_name[0]
```

Python uses zero-based indexing, so `[0]` means the first element.

---

# 12. Extracting `relatedPlaylists`

The code assigns:

```python
related_playlists = data["items"][0]["contentDetails"]["relatedPlaylists"]
```

This produces a Python dictionary similar to:

```python
{
    "likes": "",
    "uploads": "UUX6OQ3DkcsbYNE6H8uQQuVA"
}
```

So `related_playlists` is a `dict`.

---

# 13. Extracting the Uploads Playlist ID

The required value is retrieved using:

```python
uploads_playlist_id = related_playlists["uploads"]
```

This returns:

```text
UUX6OQ3DkcsbYNE6H8uQQuVA
```

The complete extraction could also be written directly as:

```python
uploads_playlist_id = (
    data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
)
```

The current implementation keeps `related_playlists` as an intermediate variable because it makes the nested JSON structure easier to understand.

---

# 14. Channel ID vs Uploads Playlist ID

The response contains two identifiers that should not be confused.

## Channel ID

```text
UCX6OQ3DkcsbYNE6H8uQQuVA
```

This identifies the **MrBeast YouTube channel**.

## Uploads Playlist ID

```text
UUX6OQ3DkcsbYNE6H8uQQuVA
```

This identifies the channel's special **uploads playlist**.

```text
UCX6OQ3DkcsbYNE6H8uQQuVA
        |
        +-- MrBeast channel

UUX6OQ3DkcsbYNE6H8uQQuVA
        |
        +-- MrBeast uploads playlist
```

The current implementation specifically needs the uploads playlist ID.

---

# 15. What the Uploads Playlist Represents

The uploads playlist is a special playlist associated with the YouTube channel.

It should not be confused with manually created playlists shown on the channel's public **Playlists** page.

The API property:

```json
"uploads": "UUX6OQ3DkcsbYNE6H8uQQuVA"
```

identifies the channel's system-associated uploads playlist.

This playlist acts as the next reference point for discovering the channel's uploaded videos.

---

# 16. Why Another API Call Is Required

The current `channels.list` request does **not** return every uploaded video.

It returns the uploads playlist ID:

```text
channels.list
    |
    v
Uploads Playlist ID
UUX6OQ3DkcsbYNE6H8uQQuVA
```

The next API operation will use:

```text
playlistItems.list
```

with that playlist ID.

```text
playlistItems.list
    |
    | playlistId = UUX6OQ3DkcsbYNE6H8uQQuVA
    v
Individual uploaded video entries
    |
    v
Video IDs
```

A later `videos.list` request can then retrieve richer metadata and statistics for those video IDs.

---

# 17. Technical Flow

```text
API_KEY + CHANNEL_HANDLE
          |
          v
Build channels.list URL
          |
          v
requests.get(url)
          |
          v
HTTP Response
          |
          +-- status_code
          |
          +-- response body
                  |
                  v
           response.json()
                  |
                  v
           Python dictionary
                  |
                  v
              ["items"]
                  |
                  v
                [0]
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
       Uploads Playlist ID
```

---

# 18. What This Implementation Proves

This first implementation validates:

- Python can communicate with the YouTube Data API.
- The Google Cloud API key can be supplied with the request.
- The `channels` resource can be queried using `channels.list`.
- A channel can be identified with `forHandle`.
- `part=contentDetails` returns the relevant related-playlist metadata.
- JSON can be parsed into Python dictionaries and lists.
- Nested JSON can be navigated using dictionary keys and list indexes.
- The uploads playlist ID can be extracted successfully.

---

# 19. Current Development Status

This code is still a **proof-of-concept / test implementation**.

It intentionally prints intermediate values:

```python
print(response.status_code)
print(response)
print(json.dumps(data, indent=4))
print(related_playlists)
print(uploads_playlist_id)
```

These are useful for learning and debugging but would normally be reduced or replaced with structured logging in a finalized pipeline.

---

# 20. Current Technical Limitations

## Hard-Coded API Key

A real API key should be moved to `.env` or another environment-variable mechanism before the code is committed publicly.

## No HTTP Error Handling

A stronger implementation should use:

```python
response.raise_for_status()
```

## No Structured Exception Handling

The request should later be wrapped in something such as:

```python
try:
    ...
except requests.exceptions.RequestException:
    ...
```

## No Reusable Function

The current logic runs directly at module level.

A later version should encapsulate it:

```python
def get_playlist_id():
    ...
    return uploads_playlist_id
```

## No Response Validation

The current code assumes:

```python
data["items"][0]
```

exists.

A stronger implementation should account for:

- Invalid or nonexistent channel handle
- Empty `items` array
- Missing fields
- Unexpected response structures

## No Explicit Timeout

A more robust request should include a timeout, for example:

```python
requests.get(url, timeout=30)
```

---

# 21. Intended Evolution

```text
Implementation 1
Basic channels.list request
+ inspect JSON
+ extract uploads playlist ID
        |
        v
Implementation 2
Refactor into get_playlist_id()
        |
        v
Implementation 3
Add response/error handling
        |
        v
Implementation 4
Move API key to .env
        |
        v
Implementation 5
Use playlistItems.list
        |
        v
Implementation 6
Retrieve video IDs
        |
        v
Implementation 7
Use videos.list
        |
        v
Implementation 8
Build final video dataset
```

Each meaningful stage can be stored as its own Git commit.

---

# 22. Relationship to Git Versioning

This proof-of-concept is a valid version to commit to Git **after removing any real API key**.

Example:

```bash
git add video_stats.py
git commit -m "add initial YouTube channel API extraction"
git push
```

A later refactored implementation can become another commit.

```text
Commit 1
Initial project setup
    |
    v
Commit 2
Basic YouTube channels API request
    |
    v
Commit 3
Extract uploads playlist ID
    |
    v
Commit 4
Refactor extraction into reusable function
    |
    v
Commit 5
Move credentials to environment variables
```

This is the practical use of **version control**: Git preserves meaningful stages of the software as it develops.

---

# 23. Relationship to the Future ELT Pipeline

The current code belongs to the **Extract** portion of the project.

```text
YouTube Data API
        |
        v
     Extract
        |
        v
Raw video data
        |
        v
      Load
        |
        v
Storage / Warehouse
        |
        v
   Transform
        |
        v
Analytics-ready data
```

Later project stages may introduce:

- Airflow for orchestration
- Containers for reproducible environments
- Environment variables for configuration
- Automated tests
- GitHub CI workflows
- Persistent storage
- Data transformation logic

---

# 24. Key Takeaway

The important result is not simply obtaining:

```text
UUX6OQ3DkcsbYNE6H8uQQuVA
```

The more important engineering workflow is:

```text
Understand API resource
        |
        v
Construct API request
        |
        v
Send HTTP GET request
        |
        v
Receive response
        |
        v
Parse JSON
        |
        v
Understand nested structure
        |
        v
Navigate dictionaries and lists
        |
        v
Extract required identifier
        |
        v
Use identifier in next API request
```

The current implementation establishes the first functional link in the YouTube ELT extraction chain:

```text
@MrBeast
    |
    v
channels.list
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

The next major step is to use that uploads playlist ID with `playlistItems.list` to enumerate the channel's uploaded videos.
