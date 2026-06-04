#!/usr/bin/python3

import os
import sys
import time
from pathlib import Path

try:
    (
        scriptname,
        directory,
        orgnzbname,
        jobname,
        reportnumber,
        category,
        group,
        postprocstatus,
        url,
    ) = sys.argv
except Exception:
    print(
        "No SAB compliant number of commandline parameters found (should be 8):",
        len(sys.argv) - 1,
    )
    sys.exit(1)  # non-zero return code

if os.environ.get("SAB_FAIL_MSG"):
    print("SAB_FAIL_MSG indicates error. Not running.")
    sys.exit(0)

complete_dir_str: str = os.environ.get("SAB_COMPLETE_DIR") or ""
if not complete_dir_str:
    print("SAB_COMPLETE_DIR not present.")
    sys.exit(1)

completed_path: Path = Path(complete_dir_str)
staging_path: Path = completed_path.parent
child_name: str = completed_path.name
staging_name: str = staging_path.name
staging_suffix: str = "-staging"
nonstaging_name: str = staging_name[: -len(staging_suffix)]

if not staging_name.endswith(staging_suffix):
    print(staging_path)
    print("- Does not appear to be a staging directory.")
    sys.exit(1)

input_path: Path = staging_path.with_name(nonstaging_name)
if not input_path.name.lower() == "in":
    print(input_path)
    print("Path structure incorrect; 'in' expected.")
    sys.exit(1)

target_path: Path = input_path / child_name

target_path.mkdir(parents=True, exist_ok=True)

output_parent_path: Path = target_path.parent / "out"

output_staging_path: Path = output_parent_path / staging_name

output_final_path: Path = output_parent_path / nonstaging_name

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
        video_inputs.append(entry)
    else:
        non_video_inputs.append(entry)

#
# Wait for all transcoded MKVs to appear.
#
expected_outputs: dict[Path, Path] = {}

for source_video in video_inputs:
    expected_mkv = output_staging_path / source_video.with_suffix(".mkv").name
    expected_outputs[source_video] = expected_mkv

deadline = time.time() + WAIT_TIMEOUT_SECONDS

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

#
# Link transcoded video files.
#
for transcoded_file in expected_outputs.values():
    hardlink(
        transcoded_file,
        output_final_path / transcoded_file.name,
    )

#
# Link original non-video files.
#
for source_file in non_video_inputs:
    hardlink(
        source_file,
        output_final_path / source_file.name,
    )

sys.exit(0)
