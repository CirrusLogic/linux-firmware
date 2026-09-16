#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

"""
Get the version of Qualcomm firmware images.

The version is taken from the QC_IMAGE_VERSION_STRING= marker embedded in the
image. xz and zstd compressed files (as installed by copy-firmware.sh) are
decompressed first.
"""

import argparse
import re
import sys
from pathlib import Path

# Import from sibling module — handle both:
#   python3 contrib/get_qcom_fw_version.py
#   python3 -c "...from contrib.get_qcom_fw_version import ..."
try:
    from fw_helpers import open_firmware
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fw_helpers import open_firmware

# Restrict the charset, so that the version can be safely embedded in Markdown
VERSION_RE = re.compile(rb"QC_IMAGE_VERSION_STRING=([A-Za-z0-9._:+~-]+)")


def get_versions(data):
    """Return the unique version strings in the image, in order of appearance."""
    versions = []
    for m in VERSION_RE.finditer(data):
        v = m.group(1).decode("ascii")
        # False positive: venus.mbn keeps this string in its string table,
        # among the log messages, instead of in an image header
        if v == "ENGG.FW":
            continue

        if v not in versions:
            versions.append(v)
    return versions


def get_fw_versions(fw_path: Path):
    with open_firmware(fw_path) as f:
        return get_versions(f.read())


def format_versions(versions):
    if versions is None:
        return "(none)"
    if not versions:
        return "(no version)"
    return "; ".join(versions)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "fw_file", type=Path, nargs="+", help="Path(s) to firmware file(s)"
    )
    args = parser.parse_args()

    ret = 0
    for fw_path in args.fw_file:
        try:
            versions = get_fw_versions(fw_path)
        except Exception as e:
            # Unreadable file or corrupt compressed data
            print(f"{fw_path}: ERROR: {e}", file=sys.stderr)
            ret = 1
            continue
        print(f"{fw_path}: {format_versions(versions)}")

    sys.exit(ret)


if __name__ == "__main__":
    main()
