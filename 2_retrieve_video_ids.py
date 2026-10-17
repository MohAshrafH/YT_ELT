# Stage 2: channel handle -> uploads playlist ID -> list of video IDs.
# The uploads playlist includes videos also organized into other playlists.
# This script prints IDs only; views, likes, and comments require a later request.
# Run from the project folder: python -B 2_retrieve_video_ids.py

# Third-party library used to send HTTP requests to the YouTube Data API.
import requests

# Standard Python library for working with JSON.
# Currently not required unless you use something like json.dumps() for formatted output.
import json

# Standard Python library that gives access to operating-system features,
# including environment variables through os.getenv().
import os

# Imports load_dotenv() from the python-dotenv package.
# python-dotenv reads variables stored in a .env file and loads them
# into the environment of the running Python process.
from dotenv import load_dotenv


# Read environment variables from the .env file located in the current directory.
# Example .env content:
# API_KEY=your_youtube_api_key
#
# After this executes, API_KEY can be retrieved using os.getenv().
load_dotenv(dotenv_path="./.env")


# Retrieve the environment variable named "API_KEY".
# The actual API key is therefore kept outside the Python source code.
# This helps prevent the secret from being committed directly to Git.
API_KEY = os.getenv("API_KEY")


# YouTube channel handle that will be passed to the API request.
CHANNEL_HANDLE = "MrBeast"

# This limits each response page, not the total number of IDs collected.
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


# __name__ is a special Python variable.
# When this file is executed directly, its value is "__main__".
if __name__ == "__main__":
    # First resolve the configured channel handle to its uploads playlist ID.
    playlist_id = get_playlist_id()
    # Then fetch all pages and print the resulting list of video IDs.
    # Nothing prints here until get_video_id() finishes collecting the list.
    print(get_video_id(playlist_id))
