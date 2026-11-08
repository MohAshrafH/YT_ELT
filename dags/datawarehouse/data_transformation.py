from datetime import timedelta, datetime  # Import a type representing a duration in days, seconds, and microseconds.


def parse_duration(duration_str):  # Accept duration text such as "P1DT2H3M4S".
    duration_str = duration_str.replace("P", "").replace("T", "")  # Remove the duration prefix and date/time separator.

    components = ["D", "H", "M", "S"]  # Process days, hours, minutes, and seconds in this order.
    values = {"D": 0, "H": 0, "M": 0, "S": 0}  # Default missing units to zero.

    for component in components:  # Examine each unit marker, starting with days.
        if component in duration_str:  # Extract a unit only if its marker appears in the remaining text.
            value, duration_str = duration_str.split(component)  # Separate the number before the marker from the remaining text.
            values[component] = int(value)  # Convert the extracted number to an integer and store it under its unit.

    total_duration = timedelta(  # Build a duration object using the extracted unit values.
        days=values["D"], hours=values["H"], minutes=values["M"], seconds=values["S"]
    )

    return total_duration  # Return the timedelta object to the caller if construction succeeds.

def transform_data(row):  # Accept a video dictionary; modify and return the same dictionary.
    duration_td = parse_duration(row["Duration"])  # Convert the duration text into a timedelta using the helper function.

    # Add the duration to the earliest datetime (year 1, midnight), then extract its clock time.
    row["Duration"] = (datetime.min + duration_td).time()

    # Use a conditional expression to label durations of 60 seconds or less as Shorts.
    row["Video_Type"] = "Shorts" if duration_td.total_seconds() <= 60 else "Normal"

    return row  # Return the dictionary containing the converted duration and assigned video type.