import json  # Convert JSON file contents into Python objects.
from datetime import date  # Access the current date for the filename.
import logging  # Record progress and error messages.

logger = logging.getLogger(__name__)  # Name the logger after this Python module.


def load_path():  # Read today's JSON file and return its contents.
    file_path = f"./data/YT_data_{date.today()}.json"  # Use today's date (YYYY-MM-DD) in the relative path.

    try:  # Catch missing-file and invalid-JSON errors during loading.
        logger.info(f"Processing file: YT_data_{date.today()}")  # Record which dated file is being processed.

        with open(file_path, "r", encoding="utf-8") as raw_data:  # Read in text mode using UTF-8; close automatically afterward.
            data = json.load(raw_data)  # Parse the open file's JSON into Python objects, such as dictionaries or lists.

        return data  # Give the parsed contents back to the calling code.
    except FileNotFoundError:  # Run if the file or a directory in its path is missing.
        logger.error(f"File not found: {file_path}")  # Record the path that could not be opened.
        raise  # Pass the original error to the caller so the failure remains visible.
    except json.JSONDecodeError:  # Run if the file's contents are not valid JSON.
        logger.error(f"Invalid JSON in file: {file_path}")  # Record which file contains malformed JSON.
        raise  # Pass the original parsing error to the caller.