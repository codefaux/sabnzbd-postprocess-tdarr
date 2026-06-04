#!/usr/bin/python3

import os
import sys
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

for entry in completed_path.iterdir():
    if not entry.is_file():
        continue

    if entry.suffix.lower() not in VIDEO_EXTENSIONS:
        continue

    destination = target_path / entry.name

    try:
        # if destination.exists():
        #     destination.unlink()

        os.link(entry, destination)
    except OSError:
        sys.exit(1)


sys.exit(0)  # Clean exit
