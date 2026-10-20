# Stage 3: channel handle -> uploads playlist ID -> video IDs -> records -> JSON file.
# The uploads playlist includes videos also organized into other playlists.
# Each record includes title, publication time, duration, views, likes, and comments.
# Run from the project folder: python -B 3_video_stats.py
# The result is saved under ./data with today's date; no result is printed.

# Third-party library used to send HTTP requests to the YouTube Data API.
import requests

# Standard Python library used by json.dump() to write records as JSON.
import json

# Standard Python library that gives access to operating-system features,
# including environment variables through os.getenv().
import os

# Standard timing utilities; currently unused because retries are not implemented.
import time

# Import the module so its date class is accessed as datetime.date.
# datetime.date.today() supplies the machine's local date for the output filename.
import datetime

# Imports load_dotenv() from the python-dotenv package.
# python-dotenv reads variables stored in a .env file and loads them
# into the environment of the running Python process.
from dotenv import load_dotenv


# Read environment variables from the .env file located in the current directory.
# Example .env content:
# API_KEY=your_youtube_api_key
#
# After this executes, API_KEY can be retrieved using os.getenv().
# The path is relative to the terminal's working directory, not the script file.
# By default, variables already present in the environment are not overwritten.
load_dotenv(dotenv_path="./.env")


# Retrieve the environment variable named "API_KEY".
# The actual API key is therefore kept outside the Python source code.
# This helps prevent the secret from being committed directly to Git.
# If the variable is missing, the value is None; this code does not validate it.
API_KEY = os.getenv("API_KEY")


# YouTube channel handle that will be passed to the API request.
CHANNEL_HANDLE = "MrBeast"

# Used both as playlist page size and video-request batch size.
# This does not limit the total number of videos collected.
maxResults = 50  # Maximum number of results to retrieve per API request (max is 50).


# Define a reusable function that retrieves the channel's uploads playlist ID.
def get_playlist_id():

    try:
        # Construct the YouTube Data API endpoint.
        #
        # part=contentDetails:
        # Requests the part of the channel resource that contains
        # related playlist information.
        #
        # forHandle:
        # Identifies the YouTube channel using its handle.
        #
        # key:
        # Sends the API key that was loaded from the .env file.
        url = (
            "https://youtube.googleapis.com/youtube/v3/channels"
            f"?part=contentDetails"
            f"&forHandle={CHANNEL_HANDLE}"
            f"&key={API_KEY}"
        )


        # Send an HTTP GET request to the YouTube API.
        # The returned Response object contains the HTTP response from YouTube.
        # Allow 10 seconds for connection and 30 seconds of read inactivity.
        # These are network timeouts, not a total runtime limit for the script.
        response = requests.get(url, timeout=(10, 30))


        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx).

        # Convert the JSON response body into Python objects,
        # mainly dictionaries and lists.
        data = response.json()


        # "items" contains the channel resources returned by YouTube.
        # Since we requested one specific channel, [0] gets the first result.
        # An empty result list raises IndexError here; it is not handled below.
        channel_items = data["items"][0]


        # Navigate through the nested response structure:
        #
        # contentDetails
        #   -> relatedPlaylists
        #       -> uploads
        #
        # "uploads" contains the playlist ID automatically maintained
        # by YouTube for all uploaded videos on the channel.
        channel_playlistID = (
            channel_items["contentDetails"]
            ["relatedPlaylists"]
            ["uploads"]
        )


        # Optional debugging/output line.
        # Uncomment it if you want to display the playlist ID.
        # print(f"Channel Playlist ID: {channel_playlistID}")


        # Return the playlist ID so another function can use it later.
        return channel_playlistID


    # Catch errors raised by the requests library, such as
    # connection failures, timeouts, or other request-related problems.
    except requests.exceptions.RequestException as e:

        # Re-raise the same exception instead of hiding the error.
        raise e


# Accept one playlist ID string and return a list of video ID strings.
# Despite the singular function name, this collects IDs across multiple pages.
def get_video_id(playlist_id):
    # Keep this list outside the loop so previous pages remain in the result.
    video_ids = []

    # None means the first request does not need a pageToken parameter.
    pageToken = None  # Initialize the page token to None for the first request.

    # Request playlist entries, with each video's ID inside contentDetails.
    # The playlistId input comes from get_playlist_id(), not from a video URL.
    base_url = f"https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults={maxResults}&playlistId={playlist_id}&key={API_KEY}"

    try:
        # Continue fetching pages until the response has no nextPageToken.
        while True:
            # Reset the URL so tokens from earlier iterations do not accumulate.
            url = base_url
            if pageToken:
                # Send the previous response's nextPageToken as pageToken.
                url += f"&pageToken={pageToken}"
            # Apply connection/read timeouts separately to every page request.
            response = requests.get(url, timeout=(10, 30))
            # Stop on HTTP errors before attempting to process playlist entries.
            response.raise_for_status()
            # Convert this page's JSON into Python dictionaries and lists.
            data = response.json()

            # Example entry: {"contentDetails": {"videoId": "Y8IJi7iP5vk"}}
            # If items is missing, the default [] makes this loop do nothing.
            for item in data.get("items", []):
                # item['id'] would identify the playlist entry, not the video.
                video_id = item["contentDetails"]["videoId"]
                # Append one string; earlier pages stay in the list.
                video_ids.append(video_id)

            # Missing nextPageToken becomes None, indicating the final page.
            # Keep the Python variable spelling consistent throughout the loop.
            pageToken = data.get("nextPageToken")

            if not pageToken:
                break  # Exit the loop if there are no more pages.

        # Return only after all available pages have been processed.
        # IDs are kept as received; this does not remove duplicates or save a file.
        return video_ids
                   
    # Propagate request failures rather than returning an incomplete list.
    # Dictionary/index errors are not caught by this request-specific handler.
    except requests.exceptions.RequestException as e:
        raise e

# Convert a list of video ID strings into a list of dictionaries of selected fields.
def extract_video_data(video_ids):
    # Accumulate records across every batch, rather than resetting per request.
    extracted_data = []

    # A nested generator yields successive slices without building all batches first.
    def batch_list(video_id_list, batch_size):
        # Despite its name, video_id here is a numeric start index: 0, 50, 100, ...
        for video_id in range(0, len(video_id_list), batch_size):
            # The slice includes the start index and excludes start + batch_size.
            # yield pauses the generator until the next batch is requested.
            yield video_id_list[video_id:video_id + batch_size]
            
    
    try:
        # Pagination discovers IDs; batching requests details for IDs already known.
        for batch in batch_list(video_ids,  maxResults):
            # Convert ['id1', 'id2'] into the API's comma-separated 'id1,id2'.
            video_ids_str = ",".join(batch)

            # Request metadata (snippet), duration (contentDetails), and counts.
            # This retains the repeated part parameters used in the successful test.
            url = f"https://youtube.googleapis.com/youtube/v3/videos?part=contentDetails&part=snippet&part=statistics&id={video_ids_str}&key={API_KEY}"

            # Send an HTTP GET request to the YouTube API.
            # The returned Response object contains the HTTP response from YouTube.
            # Allow 10 seconds for connection and 60 seconds of read inactivity.
            # These are network timeouts, not a total runtime limit for the script.
            response = requests.get(url, timeout=(10, 60))


            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx).

            # Convert the JSON response body into Python objects,
            # mainly dictionaries and lists.
            data = response.json()

            # Unlike playlistItems, each item here represents a video itself.
            # The API can return fewer accessible videos than the number requested.
            for item in data.get("items",[]):
                # Here item['id'] is the video ID, not a playlist-entry ID.
                video_id = item["id"]
                # Direct indexing expects these sections to exist; otherwise KeyError.
                snippet = item["snippet"]
                contentDetails = item["contentDetails"]
                statistics = item["statistics"]
                
                # Keep only the fields needed for the next stage of this project.
                # publishedAt stays a timestamp string; duration stays ISO 8601 text.
                # Counts stay strings as returned by YouTube; absent counts become None.
                video_data = {
                    "video_id": video_id,
                    "title": snippet["title"],
                    "publishedAt": snippet["publishedAt"],
                    "duration": contentDetails["duration"],
                    "viewCount": statistics.get("viewCount", None),
                    "likeCount": statistics.get("likeCount", None),
                    "commentCount": statistics.get("commentCount", None),
                }

                # Append one complete video record to the result list.
                extracted_data.append(video_data)

        # Outside the batch loop: return only after every batch has been processed.
        # An empty input list also reaches this line and returns [].
        return extracted_data
        
    # Report request failures to the caller; this handler does not retry requests.
    except requests.exceptions.RequestException as e:
        raise e

# Serialize the complete list of video dictionaries to a dated JSON file.
# This function has no explicit return, so it returns None after saving.
def save_to_json(extracted_data):
    # ./data is relative to the current working directory and must already exist.
    # This function does not create folders. For example: YT_data_2026-10-17.json.
    # Calling date.today() requires the module prefix because we imported datetime.
    file_path = f"./data/YT_data_{datetime.date.today()}.json"

    # "w" creates the file or overwrites an existing file with the same name.
    # Repeated runs on the same date therefore replace that day's output.
    # UTF-8 supports non-English titles; with closes the file even on an error.
    with open(file_path, "w", encoding="utf-8") as json_outfile:
        # Write directly to the open file: dictionaries/lists become JSON objects/arrays.
        # indent=4 makes it readable; ensure_ascii=False preserves Unicode characters.
        # Python None becomes JSON null; existing string counts remain strings.
        json.dump(extracted_data, json_outfile, indent=4, ensure_ascii=False)

# __name__ is a special Python variable.
# When this file is executed directly, its value is "__main__".
# Importing this module runs setup but does not run the extraction/saving block.
if __name__ == "__main__":
    # First resolve the configured channel handle to its uploads playlist ID.
    playlist_id = get_playlist_id()
    # Fetch all playlist pages and keep the video ID list for the next function.
    video_ids = get_video_id(playlist_id)

    # Fetch video records in batches and keep the returned list in memory.
    # No progress messages are printed while the requests are running.
    video_data = extract_video_data(video_ids)
    
    # Save only after extraction succeeds; this call does not print a success message.
    save_to_json(video_data)
