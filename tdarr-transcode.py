#!/usr/bin/python3

import os
import sys
import time
from pathlib import Path

# try:
#     (
#         scriptname,
#         directory,
#         orgnzbname,
#         jobname,
#         reportnumber,
#         category,
#         group,
#         postprocstatus,
#         url,
#     ) = sys.argv
# except Exception:
#     print(
#         "No SAB compliant number of commandline parameters found (should be 8):",
#         len(sys.argv) - 1,
#     )
#     sys.exit(1)  # non-zero return code

if os.environ.get("SAB_FAIL_MSG"):
    print("SAB_FAIL_MSG indicates error. Not running.")
    sys.exit(0)

complete_dir_str: str = os.environ.get("SAB_COMPLETE_DIR") or ""
if not complete_dir_str:
    print("SAB_COMPLETE_DIR not present.")
    sys.exit(1)


completed_path: Path = Path(complete_dir_str)
print("completed_path: ", completed_path)

staging_path: Path = completed_path.parent
print("staging_path: ", staging_path)

child_name: str = completed_path.name
print("child_name: ", child_name)

staging_name: str = staging_path.name
print("staging_name: ", staging_name)

staging_suffix: str = "-staging"
print("staging_suffix: ", staging_suffix)

nonstaging_name: str = staging_name[: -len(staging_suffix)]
print("nonstaging_name: ", nonstaging_name)

if not staging_name.endswith(staging_suffix):
    print(staging_path)
    print("- Does not appear to be a staging directory.")
    sys.exit(1)

input_path: Path = staging_path.parent
print("input_path: ", input_path)
if not input_path.name.lower() == "in":
    print(input_path)
    print("Path structure incorrect; 'in' expected.")
    sys.exit(1)

input_nonstaging_target_path: Path = input_path / nonstaging_name / child_name
print("input_nonstaging_target_path: ", input_nonstaging_target_path)

input_nonstaging_target_path.mkdir(parents=True, exist_ok=True)

output_path: Path = input_path.parent / "out"
print("output_path: ", output_path)

output_staging_watch_path: Path = output_path / staging_name / child_name
print("output_staging_watch_path: ", output_staging_watch_path)

output_final_path: Path = output_path / nonstaging_name / child_name
print("output_final_path: ", output_final_path)

output_final_path.mkdir(parents=True, exist_ok=True)

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
}

WAIT_TIMEOUT_SECONDS = 60 * 60  # 1 hour
POLL_INTERVAL_SECONDS = 5


def hardlink(src: Path, dst: Path) -> None:
    try:
        # if dst.exists():
        #     dst.unlink()

        os.link(src, dst)
    except OSError as e:
        print(f"Failed linking {src} -> {dst}: {e}")
        sys.exit(1)


video_inputs: list[Path] = []
non_video_inputs: list[Path] = []

for entry in completed_path.iterdir():
    if not entry.is_file():
        continue

    if entry.suffix.lower() in VIDEO_EXTENSIONS:
        destination = input_nonstaging_target_path / entry.name
        hardlink(entry, destination)
        video_inputs.append(entry)
    else:
        non_video_inputs.append(entry)

#
# Wait for all transcoded MKVs to appear.
#
expected_outputs: dict[Path, Path] = {}

for source_video in video_inputs:
    expected_mkv = output_staging_watch_path / source_video.with_suffix(".mkv").name
    expected_outputs[source_video] = expected_mkv

deadline = time.time() + WAIT_TIMEOUT_SECONDS
wait_start = time.monotonic()

while True:
    missing = [
        output_file
        for output_file in expected_outputs.values()
        if not output_file.is_file()
    ]

    if not missing:
        break

    if time.time() >= deadline:
        print("Timed out waiting for transcoded outputs:")
        for path in missing:
            print(f"  {path}")
        sys.exit(1)

    time.sleep(POLL_INTERVAL_SECONDS)

time.sleep(POLL_INTERVAL_SECONDS * 2)

wait_duration = int(time.monotonic() - wait_start)

many_minutes, process_seconds = divmod(wait_duration, 60)
process_hours, process_minutes = divmod(many_minutes, 60)

#
# Link transcoded video files.
#
for transcoded_file in expected_outputs.values():
    hardlink(
        transcoded_file,
        output_final_path / transcoded_file.name,
    )
    transcoded_file.unlink()
    transcoded_file.parent.rmdir()

#
# Link original non-video files.
#
for source_file in non_video_inputs:
    hardlink(
        source_file,
        output_final_path / source_file.name,
    )
    source_file.unlink()
    source_file.parent.rmdir()

#
# Remove original video files.
#
for input_file in video_inputs:
    input_file.unlink()
    input_file.parent.rmdir()

if completed_path.exists():
    completed_path.rmdir()
if input_nonstaging_target_path.exists():
    input_nonstaging_target_path.rmdir()
if output_staging_watch_path.exists():
    output_staging_watch_path.rmdir()

print(f"Tdarr took {process_hours:02}:{process_minutes:02}:{process_seconds:02}")

sys.exit(0)
