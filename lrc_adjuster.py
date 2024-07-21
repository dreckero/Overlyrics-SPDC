import sys
import os

def adjust_timestamp(timestamp, offset):
    offset = offset/1000
    minutes, seconds = timestamp.split(":")
    total_seconds = int(minutes) * 60 + float(seconds)
    adjusted_seconds = total_seconds + offset
    adjusted_minutes = int(adjusted_seconds // 60)
    adjusted_seconds %= 60
    adjusted_timestamp = f"{adjusted_minutes:02}:{adjusted_seconds:05.2f}"
    return adjusted_timestamp

def adjust_file(input_file, offset):
    if os.path.isfile(input_file):
        with open(input_file, "r") as file:
            lines = file.readlines()
            file.close()
        adjusted_lines = []
        for line in lines:
            if line.startswith("["):
                timestamp_end = line.index("]")
                timestamp = line[1:timestamp_end]
                try:
                    adjusted_timestamp = adjust_timestamp(timestamp, offset)
                    adjusted_line = f"[{adjusted_timestamp}]{line[timestamp_end+1:]}"
                    adjusted_lines.append(adjusted_line)
                except ValueError:
                    adjusted_lines.append(line)
            else:
                adjusted_lines.append(line)

        with open(input_file, "w") as file_replaced:
            file_replaced.writelines(adjusted_lines)
            file_replaced.close()

        #print("File offsetted correctly.")
    else:
        print("File doesn't exist.")