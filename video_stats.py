# ============================================================
# IMPLEMENTATION / TEST 1
# Basic YouTube Data API request using the channels.list endpoint
#
# Goal:
# 1. Send a request to the YouTube Data API.
# 2. Retrieve the "contentDetails" section for the MrBeast channel.
# 3. Confirm that the HTTP request succeeds.
# 4. Convert the returned JSON response into a Python object.
# 5. Print the full JSON response so we can inspect its structure.
#
# This is an initial proof-of-concept implementation.
# Later iterations will extract the uploads playlist ID from the
# returned JSON and refactor the logic into reusable functions.
# ============================================================

import requests
import json


# API key used to authenticate/identify this project when calling
# the YouTube Data API.
#
# IMPORTANT:
# Do not hard-code real API keys in source code that may be committed
# to GitHub. A later iteration should load this value from a .env file.
API_KEY = "AIzaSyDtZItkRFupuSKY32kBHA0lrNzUHy7ubpU"


# YouTube channel handle that we want to query.
# This corresponds to the @MrBeast handle on YouTube.
CHANNEL_HANDLE = "MrBeast"


# Build the YouTube Data API URL.
#
# Endpoint:
#   /youtube/v3/channels
#
# Query parameters:
#   part=contentDetails
#       Requests the channel's contentDetails section.
#       This section contains related playlist information,
#       including the channel's uploads playlist.
#
#   forHandle=MrBeast
#       Identifies the channel using its YouTube handle.
#
#   key=API_KEY
#       Supplies our API key to Google.
url = (
    "https://youtube.googleapis.com/youtube/v3/channels"
    f"?part=contentDetails"
    f"&forHandle={CHANNEL_HANDLE}"
    f"&key={API_KEY}"
)


# Send an HTTP GET request to the YouTube Data API.
#
# The returned object is a requests.Response object containing:
# - HTTP status code
# - response headers
# - response body
# - other HTTP-related information
response = requests.get(url)


# Print only the numeric HTTP status code.
#
# Expected successful result:
#   200
print(response.status_code)


# Print the Response object itself.
#
# A successful request normally appears as:
#   <Response [200]>
print(response)


# Parse the JSON response body into Python objects.
#
# JSON objects become Python dictionaries.
# JSON arrays become Python lists.
data = response.json()


# Convert the Python object back into formatted JSON-style text
# purely to make the response easier to read and inspect.
#
# indent=4 adds readable indentation to nested JSON structures.
print(json.dumps(data, indent=4))

# JSONCrack path:
# $["items"][0]["contentDetails"]["relatedPlaylists"]
#
# Path breakdown:
# $                   -> root of the entire JSON response
# ["items"]           -> access the "items" property; its value is an array/list
# [0]                 -> select the first element in the "items" array
# ["contentDetails"]  -> access the "contentDetails" property/object
# ["relatedPlaylists"]-> access the "relatedPlaylists" property/object
#
# In Python, "$" corresponds to our `data` variable:
# data["items"][0]["contentDetails"]["relatedPlaylists"]
#
# To retrieve the actual uploads playlist ID, go one level further:
# data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

# Navigate through the parsed JSON response:
# data                          -> root JSON object
# ["items"]                    -> "items" list
# [0]                          -> first channel object in the list
# ["contentDetails"]           -> contentDetails object
# ["relatedPlaylists"]         -> relatedPlaylists object
related_playlists = data["items"][0]["contentDetails"]["relatedPlaylists"]

print(related_playlists)

# Access the "uploads" key inside the relatedPlaylists dictionary.
# The value of this key is the channel's uploads playlist ID.
uploads_playlist_id = related_playlists["uploads"]

print(uploads_playlist_id)