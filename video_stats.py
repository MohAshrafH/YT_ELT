import requests
import json


# ============================================================
# CONFIGURATION
# ============================================================

# API key used to identify/authenticate the Google Cloud project
# when sending requests to the YouTube Data API.
#
# IMPORTANT:
# Do not commit a real API key to GitHub.
# A later implementation should load this from a .env file.
API_KEY = "AIzaSyDtZItkRFupuSKY32kBHA0lrNzUHy7ubpU"


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
    # raise a requests-related exception, such as a connection
    # problem or other HTTP/network request issue.
    try:

        # Build the URL for the YouTube Data API channels.list request.
        #
        # Endpoint:
        #   /youtube/v3/channels
        #
        # Query parameters:
        #
        # part=contentDetails
        #   Requests the channel's contentDetails section.
        #   This contains relatedPlaylists, including the
        #   special uploads playlist.
        #
        # forHandle=CHANNEL_HANDLE
        #   Identifies which YouTube channel we want.
        #
        # key=API_KEY
        #   Supplies the Google API key.
        url = (
            "https://youtube.googleapis.com/youtube/v3/channels"
            f"?part=contentDetails"
            f"&forHandle={CHANNEL_HANDLE}"
            f"&key={API_KEY}"
        )


        # Send an HTTP GET request to the YouTube Data API.
        #
        # The returned object is a requests.Response object,
        # which contains:
        # - HTTP status code
        # - headers
        # - response body
        # - other HTTP metadata
        response = requests.get(url)


        # Parse the JSON response body into native Python objects.
        #
        # JSON objects -> Python dictionaries
        # JSON arrays  -> Python lists
        data = response.json()


        # Development/debugging statement.
        #
        # json.dumps(..., indent=4) converts the Python object
        # into nicely formatted JSON-style text so the structure
        # can be inspected more easily.
        #
        # It is commented out because we no longer need to print
        # the entire response during normal execution.
        # print(json.dumps(data, indent=4))


        # The API response contains an "items" list.
        #
        # Because this request targets one channel using its handle,
        # the required channel object is expected to be the first
        # item in the list.
        #
        # JSON:
        #
        # "items": [
        #     {
        #         ...
        #     }
        # ]
        #
        # [0] means: select the first element.
        channel_items = data["items"][0]


        # Navigate through the nested channel JSON object:
        #
        # channel_items
        #     |
        #     v
        # contentDetails
        #     |
        #     v
        # relatedPlaylists
        #     |
        #     v
        # uploads
        #
        # Example returned value:
        #
        # UUX6OQ3DkcsbYNE6H8uQQuVA
        #
        # This is the ID of the special uploads playlist
        # associated with the channel.
        channel_playlistID = (
            channel_items["contentDetails"]
            ["relatedPlaylists"]
            ["uploads"]
        )


        # Optional development/debugging output.
        #
        # This can be uncommented when we want to verify that
        # the expected playlist ID was extracted successfully.
        # print(f"Channel Playlist ID: {channel_playlistID}")


        # Return the extracted playlist ID to whichever piece
        # of code called get_playlist_id().
        #
        # Returning the value is preferable to only printing it,
        # because other functions can later reuse it:
        #
        # playlist_id = get_playlist_id()
        # get_video_ids(playlist_id)
        return channel_playlistID


    # Catch exceptions raised by the requests library.
    #
    # RequestException is the general/base Requests exception
    # used for request-related failures such as connection errors.
    #
    # "as e" stores the exception object in the variable e.
    except requests.exceptions.RequestException as e:

        # Re-raise the exception instead of silently hiding it.
        #
        # This allows the caller or Python runtime to see
        # the actual error and traceback.
        raise e


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

# __name__ is a special built-in Python variable.
#
# When this file is executed directly:
#
#     python video_stats.py
#
# Python sets:
#
#     __name__ = "__main__"
#
# Therefore the IF block below executes.
#
# However, if this file is imported by another Python file:
#
#     import video_stats
#
# then:
#
#     __name__ = "video_stats"
#
# and the IF condition becomes False.
#
# This prevents get_playlist_id() from automatically running
# whenever this module is imported elsewhere.
if __name__ == "__main__":

    # This message confirms that video_stats.py is being
    # executed directly.
    print("get_playlist_id() function is being called")

    # Call the function.
    #
    # The function returns the uploads playlist ID.
    # At the moment the returned value is not assigned or printed
    # because this block is mainly demonstrating function execution.
    get_playlist_id()


else:

    # This block executes if video_stats.py was imported as a
    # module by another Python script instead of run directly.
    #
    # In that situation get_playlist_id() is defined and available,
    # but it is NOT automatically called.
    print("get_playlist_id() function is not being called")