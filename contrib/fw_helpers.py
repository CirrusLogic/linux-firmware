# SPDX-License-Identifier: MIT

"""
Helpers shared by the firmware version scripts in contrib/.
"""

import json
import os
import subprocess
import sys

XZ_MAGIC = b"\xfd\x37\x7a\x58\x5a\x00"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def open_firmware(path):
    """Open a firmware file for binary reading.

    xz and zstd compressed files (as installed by copy-firmware.sh) are
    transparently decompressed.
    """
    with open(path, "rb") as f:
        magic = f.read(max(len(XZ_MAGIC), len(ZSTD_MAGIC)))

    if magic.startswith(XZ_MAGIC):
        try:
            import lzma
        except ModuleNotFoundError:
            print("ERROR: lzma python module not found. Please install it.")
            sys.exit(1)

        return lzma.open(path, "rb")

    if magic.startswith(ZSTD_MAGIC):
        try:
            import zstandard as zstd
        except ModuleNotFoundError:
            print("ERROR: zstandard python module not found. Please install it.")
            sys.exit(1)

        return zstd.ZstdDecompressor().stream_reader(open(path, "rb"))

    return open(path, "rb")


def get_changed_files(base_ref, target_ref, paths):
    """Return the files below paths changed between base_ref and target_ref."""
    out = subprocess.run(
        ["git", "diff", "--name-only", base_ref, target_ref, "--", *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode not in (0, 1):
        return []
    return out.stdout.strip().splitlines()


def git_show_file(ref, path):
    """Return the contents of path at ref, or None if it does not exist there."""
    result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout


def post_mr_comment(body):
    """Post a comment on the current MR via the GitLab API."""
    if not all(
        [
            os.environ.get("CI_PROJECT_ID"),
            os.environ.get("CI_PIPELINE_ID"),
            os.environ.get("CI_MERGE_REQUEST_IID", ""),
            os.environ.get("CI_API_V4_URL"),
        ]
    ):
        print(
            "WARNING: Missing GitLab CI environment variables; skipping comment",
            file=sys.stderr,
        )
        return

    import urllib.request
    import urllib.error

    api_url = os.environ["CI_API_V4_URL"]
    project = os.environ["CI_PROJECT_ID"]
    mr_iid = os.environ["CI_MERGE_REQUEST_IID"]
    token = os.environ.get("MR_COMMENT_TOKEN", "")

    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(
        f"{api_url}/projects/{project}/merge_requests/{mr_iid}/discussions",
        data=data,
        headers={
            "PRIVATE-TOKEN": token,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            discussion_id = result.get("id", "unknown")
            print(
                f"Posted new MR comment: {api_url}/projects/{project}/"
                f"merge_requests/{mr_iid}#note_{discussion_id}"
            )
    except urllib.error.HTTPError as e:
        print(
            f"WARNING: Failed to post MR comment: {e.read().decode()}", file=sys.stderr
        )
