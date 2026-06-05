#!/usr/bin/env python3

import subprocess
import sys
import time

COMMAND = ["/config/scripts/tdarr-transcode.py"]


def main():
    # spawn subprocess in isolated new Python session
    proc = subprocess.Popen(
        COMMAND + sys.argv[1:],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    time.sleep(2)

    if proc.poll() is None:
        print(f"Transcode started (pid {proc.pid})")
        sys.exit(0)

    print(f"Failed (pid {proc.pid}: exit {proc.returncode})")
    sys.exit(1)


if __name__ == "__main__":
    main()
