#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

"""
Get the version of Qualcomm firmware images.

The version is taken from the QC_IMAGE_VERSION_STRING= marker embedded in the
image, from the header of Adreno SQE and AQE microcode (*_sqe.fw, *_aqe.fw) and
ZAP shaders (*_zap.mbn) or from Adreno GMU and RGMU firmware (*_gmu.bin,
gmu_*.bin, *_rgmu.bin). xz and zstd compressed files (as installed by copy-
firmware.sh) are decompressed first.
"""

import argparse
import re
import struct
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
# Iris video firmware version, e.g. "vfw-3.1:rel0093-<sha1>", listed in WHENCE
# as VIDEO.VPU.3.1-0093
VFW_VERSION_RE = re.compile(
    r"vfw-(?P<version>[0-9]+(?:\.[0-9]+)+):rel(?P<release>[0-9]+)-[0-9a-f]{40}"
)
SQE_NAME_RE = re.compile(r"_[as]qe\.fw")
ZAP_NAME_RE = re.compile(r"_zap\.mbn")
RGMU_NAME_RE = re.compile(r"_rgmu\.bin")
GMU_NAME_RE = re.compile(r"(^|[/_])gmu(_\w+)?\.bin")

# Address of GMU_CORE_FW_VERSION in the GMU memory of the older GPUs, which
# keep the version in the lowest 12 bits, like the microcode does
GMU_LEGACY_CORE_VER_ADDR = 0x00043FE0
# Address of GMU_CORE_FW_VERSION in the GMU memory of a650 and newer, split
# into the major, minor and step fields
GMU_CORE_VER_ADDR = 0x10007FE0

# The RGMU firmware writes its version to GMU_GENERAL_0 (register 0x1f9c5),
# where the downstream kgsl driver reads it from once the firmware has booted
RGMU_VER_REG_ADDR = 0x1F9C5 * 4
# Fixed-size records of the RGMU firmware image
RGMU_RECORD = struct.Struct("<4I")

PT_LOAD = 1


def _version(major, minor, patch=None):
    """Format an Adreno firmware version, e.g. v2.07 or v1.89.01."""
    version = f"v{major:X}.{minor:02X}"
    return version if patch is None else f"{version}.{patch:02X}"


def _ucode_version(ucode):
    """Return the version kept in the lowest 12 bits of an Adreno header."""
    return _version((ucode >> 8) & 0xF, ucode & 0xFF)


def get_sqe_versions(data):
    """Return the version of Adreno SQE or AQE microcode.

    AQE microcode uses the same header as the SQE one.
    See a6xx_ucode_check_version() in drivers/gpu/drm/msm/adreno/a6xx_gpu.c.
    The kernel drops the first dword of the file, so its buf[0] and buf[2]
    are dwords 1 and 3 of the file.
    """
    if len(data) < 16:
        return []

    zero, ucode, _, patched = struct.unpack_from("<4I", data)
    if zero != 0:
        return []

    # The lowest nibble 0xa marks patched a630 microcode, the actual version
    # (with the patch level) is in dword 3
    if (ucode & 0xF) == 0xA:
        major, minor = (patched >> 20) & 0xF, (patched >> 12) & 0xFF
        return [_version(major, minor, patched & 0xFF)]

    return [_ucode_version(ucode)]


def _block_word(data, start, addr, size, word_addr):
    """Return the word loaded at word_addr by the block, or None."""
    if addr > word_addr or word_addr + 4 > addr + size:
        return None

    (word,) = struct.unpack_from("<I", data, start + word_addr - addr)
    return word


def get_gmu_versions(data):
    """Return the core version of Adreno GMU firmware.

    The firmware is a list of blocks loaded at the given addresses, see
    a6xx_gmu_fw_load(). Look for the block initializing the version. Legacy
    GMU firmware is a plain image and carries no version.
    """
    off = 0
    while off + 16 <= len(data):
        addr, size = struct.unpack_from("<2I", data, off)
        start = off + 16
        if start + size > len(data):
            break

        ver = _block_word(data, start, addr, size, GMU_LEGACY_CORE_VER_ADDR)
        if ver is not None:
            return [_ucode_version(ver)]

        ver = _block_word(data, start, addr, size, GMU_CORE_VER_ADDR)
        if ver is not None:
            return [_version(ver >> 28, (ver >> 16) & 0xFFF, ver & 0xFFFF)]

        off = start + size

    return []


def get_zap_versions(data):
    """Return the version of an Adreno ZAP shader.

    The ZAP shader is a 32-bit ELF image, whose first loadable segment starts
    with the same header dword as the SQE microcode.
    """
    if len(data) < 52 or data[:6] != b"\x7fELF\x01\x01":
        return []

    (phoff,) = struct.unpack_from("<I", data, 28)
    phentsize, phnum = struct.unpack_from("<HH", data, 42)
    for i in range(phnum):
        entry = phoff + i * phentsize
        if entry + 20 > len(data):
            break

        p_type, offset, _, _, filesz = struct.unpack_from("<5I", data, entry)
        if p_type != PT_LOAD or filesz < 4 or offset + 4 > len(data):
            continue

        (ucode,) = struct.unpack_from("<I", data, offset)
        return [_ucode_version(ucode)]

    return []


def get_rgmu_versions(data):
    """Return the version of Adreno RGMU firmware.

    Look for the record writing the version to GMU_GENERAL_0.
    """
    for off in range(0, len(data) - RGMU_RECORD.size + 1, RGMU_RECORD.size):
        value, _, addr, _ = RGMU_RECORD.unpack_from(data, off)
        if addr & 0xFFFFF == RGMU_VER_REG_ADDR:
            return [_version(value >> 16, value & 0xFF)]

    return []


def get_versions(data, name=""):
    """Return the unique version strings in the image, in order of appearance.

    The format is selected by the firmware file name.
    """
    if SQE_NAME_RE.search(name):
        return get_sqe_versions(data)

    if ZAP_NAME_RE.search(name):
        return get_zap_versions(data)

    if RGMU_NAME_RE.search(name):
        return get_rgmu_versions(data)

    if GMU_NAME_RE.search(name):
        return get_gmu_versions(data)

    versions = []
    for m in VERSION_RE.finditer(data):
        v = m.group(1).decode("ascii")
        # False positive: venus.mbn keeps this string in its string table,
        # among the log messages, instead of in an image header
        if v == "ENGG.FW":
            continue

        vfw = VFW_VERSION_RE.fullmatch(v)
        if vfw:
            v = f"VIDEO.VPU.{vfw['version']}-{int(vfw['release']):04d}"
        if v not in versions:
            versions.append(v)
    return versions


def get_fw_versions(fw_path: Path):
    with open_firmware(fw_path) as f:
        return get_versions(f.read(), fw_path.name)


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
