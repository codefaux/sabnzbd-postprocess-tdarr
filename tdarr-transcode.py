#!/usr/bin/python3

import logging
import os
import sys
import time
from pathlib import Path

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


# full public r/w/X by default
os.umask(int(os.environ.get("TDARR_SCRIPT_UMASK") or 0))
DIR_MODE = int(os.environ.get("TDARR_SCRIPT_DMODE") or 0o777)
FILE_MODE = int(os.environ.get("TDARR_SCRIPT_FMODE") or 0o666)

WAIT_TIMEOUT_SECONDS = 60 * 60  # 1 hour
POLL_INTERVAL_SECONDS = 5


def hardlink(src: Path, dst: Path) -> None:
    try:
        dst.unlink(missing_ok=True)
        src.hardlink_to(dst)
    except OSError as e:
        logging.warning(f"Failed linking: {e}")
        # sys.exit(1)

    try:
        dst.chmod(FILE_MODE)
    except OSError as e:
        logging.warning(f"Failed chmod: {e}")


pid = os.getpid()
log_path = f"/config/logs/tdarr-transcode-{pid}.log"

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path),
    ],
    format="%(asctime)s [PID %(process)d] %(message)s\n",
)

# ensure we have what we need and should be running
if os.environ.get("SAB_FAIL_MSG"):
    logging.error("SAB_FAIL_MSG indicates error. Not running.")
    sys.exit(0)

complete_dir_str: str = os.environ.get("SAB_COMPLETE_DIR") or ""
if not complete_dir_str:
    logging.error("SAB_COMPLETE_DIR not present.")
    sys.exit(1)

# compute paths/names
logging.info("- Begin\n\n")

completed_path: Path = Path(complete_dir_str)
logging.info(f"completed_path: {completed_path}")

staging_path: Path = completed_path.parent
logging.info(f"staging_path: {staging_path}")

child_name: str = completed_path.name
logging.info(f"child_name: {child_name}")

staging_name: str = staging_path.name
logging.info(f"staging_name: {staging_name}")

staging_suffix: str = "-staging"
logging.info(f"staging_suffix: {staging_suffix}")

if not staging_name.endswith(staging_suffix):
    logging.error(f"- Does not appear to be a staging directory. '{staging_path}'")
    sys.exit(1)

nonstaging_name: str = staging_name[: -len(staging_suffix)]
logging.info(f"nonstaging_name: {nonstaging_name}")

input_path: Path = staging_path.parent
logging.info(f"input_path: {input_path}")
if not input_path.name.lower() == "in":
    logging.error(f"- Path structure incorrect; 'in' expected. '{input_path}'")
    sys.exit(1)

input_nonstaging_target_path: Path = input_path / nonstaging_name / child_name
logging.info(f"input_nonstaging_target_path: {input_nonstaging_target_path}")

output_path: Path = input_path.parent / "out"
logging.info(f"output_path: {output_path}")

output_staging_watch_path: Path = output_path / staging_name / child_name
logging.info(f"output_staging_watch_path: {output_staging_watch_path}")

output_final_path: Path = output_path / nonstaging_name / child_name
logging.info(f"output_final_path: {output_final_path}")

logging.info("\n")

# create our paths
input_nonstaging_target_path.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
output_final_path.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)

# if download target path exists, iterate video vs non-video files
video_inputs: list[Path] = []
non_video_inputs: list[Path] = []

if completed_path.exists():
    for entry in completed_path.iterdir():
        if not entry.is_file():
            continue

        if entry.suffix.lower() in VIDEO_EXTENSIONS:
            logging.info(
                "found input staging file, hardlinking to nonstaging path\n"
                f"- in: '{entry}'\n- out: '{input_nonstaging_target_path}'"
            )
            destination = input_nonstaging_target_path / entry.name
            hardlink(entry, destination)
            video_inputs.append(entry)
        else:
            logging.info(
                "found input non-video file, recording\n"
                f"- file: '{input_nonstaging_target_path}'"
            )
            non_video_inputs.append(entry)

# calculate target files
expected_outputs: dict[Path, Path] = {}

for source_video in video_inputs:
    expected_mkv = output_staging_watch_path / source_video.with_suffix(".mkv").name
    logging.info(f"- expecting:\n- in: '{source_video}'\n- out: '{expected_mkv}'")
    expected_outputs[source_video] = expected_mkv

# wait for target files
deadline = time.time() + WAIT_TIMEOUT_SECONDS
wait_start = time.monotonic()

logging.info("- Waiting ...\n")

while True:
    missing = [
        output_file
        for output_file in expected_outputs.values()
        if not output_file.is_file()
    ]

    if not missing:
        break

    if time.time() >= deadline:
        logging.error("Timeout waiting for transcoded outputs:")
        for path in missing:
            logging.error(f"- '{path}'")
        sys.exit(1)

    time.sleep(POLL_INTERVAL_SECONDS)

time.sleep(POLL_INTERVAL_SECONDS * 2)

logging.info("Found all expected files.\n")

# calculate times
wait_duration = int(time.monotonic() - wait_start)

many_minutes, process_seconds = divmod(wait_duration, 60)
process_hours, process_minutes = divmod(many_minutes, 60)

# Link original non-video files.
for source_file in non_video_inputs:
    logging.info(
        "Moving source file to output final path\n"
        f"- file '{source_file}'\n- to: '{output_final_path}'"
    )
    hardlink(
        source_file,
        output_final_path / source_file.name,
    )
    source_file.unlink()
    source_file.parent.rmdir()

# Link transcoded video files.
for transcoded_file in expected_outputs.values():
    logging.info(
        "Moving transcoded file to output final path\n"
        f"- file: '{transcoded_file}'\n- to: '{output_final_path}'"
    )
    hardlink(
        transcoded_file,
        output_final_path / transcoded_file.name,
    )
    transcoded_file.unlink()
    if not any(transcoded_file.parent.iterdir()):
        transcoded_file.parent.rmdir()

# Remove original video files (transcoded now)
for video_file in video_inputs:
    logging.info(f"Removing input file\n- file: '{video_file}'")
    video_file.unlink()
    if not any(video_file.parent.iterdir()):
        video_file.parent.rmdir()

# Remove transcoder input if exists
if input_nonstaging_target_path.exists():
    for input_file in input_nonstaging_target_path.iterdir():
        logging.info(f"Removing input nonstaging file\n- file: '{input_file}'")
        input_file.unlink()
    logging.info(
        f"Removing input nonstaging path\n- path: '{input_nonstaging_target_path}'"
    )
    input_nonstaging_target_path.rmdir()

# Remove original download directory
if completed_path.exists():
    logging.info(f"Removing input staging path\n- path '{completed_path}'")
    completed_path.rmdir()

# remove tdarr output files, directory
if output_staging_watch_path.exists():
    for output_staging_file in output_staging_watch_path.iterdir():
        logging.info(f"Removing output staging file\n- file: '{output_staging_file}'")
        output_staging_file.unlink()
    logging.info(f"Removing output staging path\n- path: '{output_staging_watch_path}'")
    output_staging_watch_path.rmdir()

logging.info("Done moving.\n\n")

logging.info(f"Tdarr took {process_hours:02}:{process_minutes:02}:{process_seconds:02}")

sys.exit(0)
