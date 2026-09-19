#!/usr/bin/python
# SPDX-License-Identifier: MIT

import argparse
import collections
import struct
import re
import sys
from pathlib import Path

# Import from sibling module — handle both:
#   python3 contrib/get_amdgpu_fw_version.py
#   python3 -c "...from contrib.get_amdgpu_fw_version import ..."
try:
    from fw_helpers import open_firmware
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fw_helpers import open_firmware

DESC = """
Get the amdgpu firmware .bin version, and crc32 checksum.
"""

parser = argparse.ArgumentParser(
    description=DESC, formatter_class=argparse.RawTextHelpFormatter
)
parser.add_argument(
    "fw_bin", type=str, nargs="+", help="Path(s) to firmware .bin file(s)"
)

# AMDGPU common firmware header v1.0, copied from
# drivers/gpu/drm/amd/amdgpu/amdgpu_ucode.h
#
# struct common_firmware_header {
#     uint32_t size_bytes; /* size of the entire header+image(s) in bytes */
#     uint32_t header_size_bytes; /* size of just the header in bytes */
#     uint16_t header_version_major; /* header version */
#     uint16_t header_version_minor; /* header version */
#     uint16_t ip_version_major; /* IP version */
#     uint16_t ip_version_minor; /* IP version */
#     uint32_t ucode_version;
#     uint32_t ucode_size_bytes; /* size of ucode in bytes */
#     uint32_t ucode_array_offset_bytes; /* payload offset from the start of the header */
#     uint32_t crc32;  /* crc32 checksum of the payload */
# };
#
# I = unsigned int (4 bytes), H = unsigned short (2 bytes)
# See https://docs.python.org/3/library/struct.html#format-characters
HEADER_FORMAT_STRING = "IIHHHHIIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT_STRING)

CommonVersion = collections.namedtuple(
    "CommonVersion", ["ip_major", "ip_minor", "ucode_version", "ucode_bytes", "crc32"]
)
DMCUBVersion = collections.namedtuple(
    "DMCUBVersion",
    ["major", "minor", "revision", "is_test", "is_vbios", "hotfix"],
)


def get_common_version(fw_header: str):
    """Parse common amdgpu firmware header"""
    unpacked_header = struct.unpack(HEADER_FORMAT_STRING, fw_header)

    return CommonVersion(
        ip_major=unpacked_header[4],
        ip_minor=unpacked_header[5],
        ucode_version=unpacked_header[6],
        ucode_bytes=unpacked_header[7],
        crc32=unpacked_header[9],
    )


def get_dmcub_version_a(ucode_version: int):
    """Parse DMCUB ucode version without is_test, is_vbios, and hotfix fields"""
    # DMCUB ucode version is 32 bits, defined as:
    # #define DMUB_FW_VERSION_UCODE (
    #     (DMUB_FW_VERSION_MAJOR << 24) | \
    #     (DMUB_FW_VERSION_MINOR << 16) | \
    #     DMUB_FW_VERSION_REVISION)
    return DMCUBVersion(
        major=(ucode_version >> 24) & 0xFF,
        minor=(ucode_version >> 16) & 0xFF,
        revision=ucode_version & 0xFF,
        is_test=0,
        is_vbios=0,
        hotfix=0,
    )


def get_dmcub_version_b(ucode_version: int):
    """Parse DMCUB ucode version"""
    # DMCUB ucode version is 32 bits, defined as:
    # #define DMUB_FW_VERSION_UCODE (
    #     ((DMUB_FW_VERSION_MAJOR & 0xFF) << 24) | \
    #     ((DMUB_FW_VERSION_MINOR & 0xFF) << 16) | \
    #     ((DMUB_FW_VERSION_REVISION & 0xFF) << 8) | \
    #     ((DMUB_FW_VERSION_TEST & 0x1) << 7) | \
    #     ((DMUB_FW_VERSION_VBIOS & 0x1) << 6) | \
    #     (DMUB_FW_VERSION_HOTFIX & 0x3F))
    return DMCUBVersion(
        major=(ucode_version >> 24) & 0xFF,
        minor=(ucode_version >> 16) & 0xFF,
        revision=(ucode_version >> 8) & 0xFF,
        is_test=(ucode_version >> 7) & 0x1,
        is_vbios=(ucode_version >> 6) & 0x1,
        hotfix=ucode_version & 0x3F,
    )


"""
Determine IP by filename

DMCUB ucode version format changed after yellow_carp. The major.minor.revision
IP version can be used to identify whether old or new ucode version is used.
However, the common header format does not include the revision. So we'll use
hard-coded filename matching instead.

The list defines file-name regex and ucode version parser pairs. When finding
the parser, we run through this list top down, returning the first match.
"""
PARSERS = [
    {
        "name": "DMCUB",
        "regex": (
            r"(green_sardine_dmcub.bin)|"
            r"(sienna_cichlid_dmcub.bin)|"
            r"(navy_flounder_dmcub.bin)|"
            r"(dimgrey_cavefish_dmcub.bin)|"
            r"(beige_goby_dmcub.bin)|"
            r"(yellow_carp_dmcub.bin)|"
            r"(renoir_dmcub.bin)|"
            r"(vangogh_dmcub.bin)"
        ),
        "ucode_parser": get_dmcub_version_a,
    },
    {"name": "DMCUB", "regex": r".+dmcub\.bin", "ucode_parser": get_dmcub_version_b},
    {
        # Default case
        "name": "amdgpu generic",
        "regex": r".+",
        "ucode_parser": None,
    },
]


def int_and_hex(val):
    return f"{val} ({hex(val)})"


def get_header(fw_bin_path: Path):
    with open_firmware(fw_bin_path) as f:
        return f.read(HEADER_SIZE)


def get_fw_version(fw_bin_path: Path):
    fw_header = get_header(fw_bin_path)

    if len(fw_header) != HEADER_SIZE:
        print(
            f"ERRROR: Invalid firmware. Expected a {HEADER_SIZE} bytes "
            f"header, got {len(fw_header)} bytes"
        )

        return None

    common_vers = get_common_version(fw_header)

    ret = ""
    ucode_vers = None

    for parser in PARSERS:
        if re.match(parser["regex"], fw_bin_path.name):
            ret += f"{fw_bin_path.name}: {parser['name']} FW\n"

            if parser["ucode_parser"] is not None:
                ucode_vers = parser["ucode_parser"](common_vers.ucode_version)

            break

    # Pretty print common version
    for k, v in common_vers._asdict().items():
        ret += f"{k:>16} = {int_and_hex(v)}\n"

    # Pretty print detailed ucode version
    if ucode_vers is not None:
        ret += "-" * 32 + "\n"
        ret += "Detailed uCode version:\n"
        for k, v in ucode_vers._asdict().items():
            ret += f"{k:>16} = {int_and_hex(v)}\n"

    return ret


if __name__ == "__main__":
    args = parser.parse_args()
    for fw_bin_path in args.fw_bin:
        print(get_fw_version(Path(fw_bin_path)))
    exit(0)
