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
        response = requests.get(url)


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


# __name__ is a special Python variable.
# When this file is executed directly, its value is "__main__".
if __name__ == "__main__":

    # Run the function when video_stats.py itself is executed.
    get_playlist_id()

else:
    # This branch runs when this file is imported into another Python file.
    print("get_playlist_id() function is not being called")