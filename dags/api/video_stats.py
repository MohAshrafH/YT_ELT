# TaskFlow pipeline: channel handle -> uploads playlist -> video IDs -> records -> JSON.
import requests  # Send HTTP requests to the YouTube Data API.
import json  # Serialize Python records to JSON.
import time  # Timing utilities; currently unused.
import datetime  # Supply the worker's local date for the output filename.
from airflow.decorators import task, dag  # Build TaskFlow tasks; dag is currently unused.
from airflow.models import Variable  # Read settings through Airflow's Variable system.

# These lookups run at import/DAG-parse time; missing Variables raise an error.
API_KEY = Variable.get("API_KEY")  # API credential, configured outside this source file.
CHANNEL_HANDLE = Variable.get("CHANNEL_HANDLE")  # Channel handle to resolve through the API.
maxResults = 50  # Playlist page size and video-detail batch size, not a total-video limit.


# Decorated calls create tasks/XComArgs; Airflow executes their bodies at task runtime.
@task
def get_playlist_id():
    # Resolve the channel handle to YouTube's automatically maintained uploads playlist.
    try:
        # contentDetails includes related playlists; forHandle selects the channel.
        url = (
            "https://youtube.googleapis.com/youtube/v3/channels"
            f"?part=contentDetails"
            f"&forHandle={CHANNEL_HANDLE}"
            f"&key={API_KEY}"
        )

        # Separate connect/read-inactivity timeouts in seconds, not a total runtime cap.
        response = requests.get(url, timeout=(10, 30))
        response.raise_for_status()  # Raise on HTTP 4xx/5xx before processing the body.
        data = response.json()  # Decode JSON into Python dictionaries and lists.

        channel_items = data["items"][0]  # Expect a match; an empty list raises IndexError.
        channel_playlistID = (
            channel_items["contentDetails"]
            ["relatedPlaylists"]
            ["uploads"]
        )  # Follow the nested keys to the uploads playlist ID; missing keys raise KeyError.

        return channel_playlistID  # Airflow makes this task output available through XCom.
    except requests.exceptions.RequestException as e:
        raise e  # Propagate request failures to Airflow; this handler does not retry.


@task
def get_video_id(playlist_id):
    video_ids = []  # Accumulate IDs from every playlist page; duplicates are retained.
    pageToken = None  # The first page requires no continuation token.

    # Request playlist entries with video IDs in contentDetails, up to 50 per page.
    base_url = f"https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults={maxResults}&playlistId={playlist_id}&key={API_KEY}"

    try:
        while True:
            url = base_url  # Reset each iteration so previous tokens do not accumulate.
            if pageToken:
                url += f"&pageToken={pageToken}"  # Continue from the preceding response.
            response = requests.get(url, timeout=(10, 30))  # Connect/read timeouts per page.
            response.raise_for_status()  # Stop on HTTP errors instead of returning partial IDs.
            data = response.json()

            # Missing items defaults to an empty list, so this page adds no IDs.
            for item in data.get("items", []):
                video_id = item["contentDetails"]["videoId"]  # Video ID, not playlist-entry ID.
                video_ids.append(video_id)

            pageToken = data.get("nextPageToken")  # Missing token means the final page.
            if not pageToken:
                break

        return video_ids  # Return only after all pages; an empty playlist yields [].
    except requests.exceptions.RequestException as e:
        raise e  # Re-raise request failures; malformed response structures also fail the task.


@task
def extract_video_data(video_ids):
    extracted_data = []  # Accumulate selected video fields across all request batches.

    # Yield slices lazily: the final batch may contain fewer than batch_size IDs.
    def batch_list(video_id_list, batch_size):
        for video_id in range(0, len(video_id_list), batch_size):  # Start indices: 0, 50, 100, ...
            yield video_id_list[video_id:video_id + batch_size]  # End index is excluded.

    try:
        # Pagination discovers IDs; batching fetches details for IDs already collected.
        for batch in batch_list(video_ids,  maxResults):
            video_ids_str = ",".join(batch)  # Convert the list to comma-separated API IDs.

            # Request duration, descriptive metadata, and statistics using repeated part keys.
            url = f"https://youtube.googleapis.com/youtube/v3/videos?part=contentDetails&part=snippet&part=statistics&id={video_ids_str}&key={API_KEY}"

            response = requests.get(url, timeout=(10, 60))  # Allow longer read inactivity here.
            response.raise_for_status()
            data = response.json()

            # Each item is a video; unavailable videos may be omitted from the response.
            for item in data.get("items",[]):
                video_id = item["id"]
                snippet = item["snippet"]  # Title and publication timestamp.
                contentDetails = item["contentDetails"]  # Duration and other technical details.
                statistics = item["statistics"]  # Counts; direct section lookups require these keys.

                # Preserve API types: timestamp/duration/counts stay strings; absent counts -> None.
                video_data = {
                    "video_id": video_id,
                    "title": snippet["title"],
                    "publishedAt": snippet["publishedAt"],  # Timestamp text, not a datetime object.
                    "duration": contentDetails["duration"],  # ISO 8601 text, such as PT5M30S.
                    "viewCount": statistics.get("viewCount", None),
                    "likeCount": statistics.get("likeCount", None),
                    "commentCount": statistics.get("commentCount", None),
                }
                extracted_data.append(video_data)  # Add one complete record to the output.

        return extracted_data  # Return after all batches; empty input yields [].
    except requests.exceptions.RequestException as e:
        raise e  # Let Airflow see request failures; no retries are implemented here.


@task
def save_to_json(extracted_data):
    # Relative to the worker's current directory; ./data must already exist.
    file_path = f"./data/YT_data_{datetime.date.today()}.json"

    # Write UTF-8; same-day runs overwrite the file. The context closes it on exit.
    with open(file_path, "w", encoding="utf-8") as json_outfile:
        # Pretty-print Unicode text; Python None becomes JSON null. Returns None implicitly.
        json.dump(extracted_data, json_outfile, indent=4, ensure_ascii=False)


# Runs only when launched directly; decorated calls build task references, not API results.
# Use main.py's DAG to execute this pipeline through Airflow; this block alone does not run it.
if __name__ == "__main__":
    playlist_id = get_playlist_id()
    video_ids = get_video_id(playlist_id)
    video_data = extract_video_data(video_ids)
    save_to_json(video_data)
