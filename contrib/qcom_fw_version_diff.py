#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

"""
Show Qualcomm firmware versions, or compare them across an MR diff.

All files below ath10k/, ath11k/, ath12k/, qca/ and qcom/ are considered.
Version extraction is delegated to get_qcom_fw_version.py.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Import from sibling module — handle both:
#   python3 contrib/qcom_fw_version_diff.py
#   python3 -c "...from contrib.qcom_fw_version_diff import ..."
try:
    from fw_helpers import get_changed_files, git_show_file, post_mr_comment
    from get_qcom_fw_version import format_versions, get_versions
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fw_helpers import get_changed_files, git_show_file, post_mr_comment
    from get_qcom_fw_version import format_versions, get_versions

FW_DIRS = ["ath10k/", "ath11k/", "ath12k/", "qca/", "qcom/"]
# Trailing git hash, as used by e.g. "video-firmware.3.4-<sha1>"
GIT_HASH_RE = re.compile(r"-[0-9a-f]{40}$")
# "<branch>-<build>[-<variant>-<revision>]", e.g. "ADSP.HT.5.3.c2-00082-SM8250-1"
QC_VERSION_RE = re.compile(
    r"^(?P<branch>.+?)-(?P<build>\d+(?:\.\d+)*)(?:-(?P<rest>.*))?$"
)
REVISION_RE = re.compile(r"\d+(?:\.\d+)*")
ADRENO_VERSION_RE = re.compile(r"v\d")

CHANGE_LABELS = {
    "new": "new",
    "removed": "removed",
    "upgrade": "upgraded",
    "downgrade": "downgraded",
    "changed": "not comparable",
}


# ── Version comparison ──────────────────────────────────────────────────────


def _numbers(s):
    return tuple(int(n) for n in re.findall(r"\d+", s))


def _parse_version(version):
    """Split a version string into (family, number, variant, revision).

    Only versions of the same family (same branch once all numbers are
    masked) can be ordered.
    """
    version = GIT_HASH_RE.sub("", version)

    # Adreno versions are hex numbers with a varying number of components,
    # e.g. the patched "v1.89.01" and the plain "v2.07" SQE microcode. Keep
    # them in one family, so that such two versions can still be compared.
    if ADRENO_VERSION_RE.match(version):
        return "v#", tuple(int(n, 16) for n in version[1:].split(".")), "", ()

    m = QC_VERSION_RE.match(version)
    if m is None:
        return re.sub(r"\d+", "#", version), _numbers(version), "", ()

    branch, build, rest = m.group("branch", "build", "rest")
    variant, _, revision = (rest or "").rpartition("-")
    # Not a respin counter, e.g. the git-describe suffix of "TZ.AIC.1.19.0.3-1-G8F15A640F"
    if not REVISION_RE.fullmatch(revision):
        variant, revision = rest or "", ""

    return (
        re.sub(r"\d+", "#", branch),
        (_numbers(branch), _numbers(build)),
        variant,
        _numbers(revision),
    )


def compare_versions(before, after):
    """Compare two versions of the same family.

    Returns 'upgrade' | 'downgrade' | 'equal' | 'changed', the last one
    meaning that the versions could not be ordered.
    """
    _, b_number, b_variant, b_revision = _parse_version(before)
    _, a_number, a_variant, a_revision = _parse_version(after)

    if a_number != b_number:
        return "upgrade" if a_number > b_number else "downgrade"
    if a_variant != b_variant:
        return "changed"
    if a_revision != b_revision:
        return "upgrade" if a_revision > b_revision else "downgrade"
    return "equal" if before == after else "changed"


def classify_change(before, after):
    """Classify the change between two lists of version strings.

    Each version is compared against the version of the same family. Any
    downgrade wins, then any version that could not be ordered.
    """
    remaining = list(before)
    results = set()
    for a in after:
        family = _parse_version(a)[0]
        b = next((b for b in remaining if _parse_version(b)[0] == family), None)
        if b is None:
            results.add("changed")
            continue
        remaining.remove(b)
        results.add(compare_versions(b, a))

    if remaining:
        results.add("changed")

    for result in ("downgrade", "changed", "upgrade"):
        if result in results:
            return result
    return "equal"


# ── git helpers ─────────────────────────────────────────────────────────────


def get_changed_firmware(base_ref, target_ref):
    """Return list of firmware files changed between base_ref and target_ref."""
    return get_changed_files(base_ref, target_ref, FW_DIRS)


def get_base_versions(base_ref, path):
    """Return the versions of path at base_ref, or None if it did not exist."""
    data = git_show_file(base_ref, path)
    return None if data is None else get_versions(data, path)


def get_current_versions(path):
    """Return the versions of path in the working tree, or None if it is gone."""
    path = Path(path)
    return get_versions(path.read_bytes(), str(path)) if path.is_file() else None


# ── Report ──────────────────────────────────────────────────────────────────


def _code(versions):
    # VERSION_RE guarantees that there are no backticks or pipes to escape
    return f"`{format_versions(versions)}`"


def build_report(base_ref, changed):
    """Return the Markdown report for the changed firmware, or None if there
    is nothing to report."""
    rows = []
    counts = dict.fromkeys(CHANGE_LABELS, 0)
    downgrades = []
    unchanged = []
    unversioned = 0

    for path in changed:
        before = get_base_versions(base_ref, path)
        after = get_current_versions(path)

        if not before and not after:
            unversioned += 1
            continue

        if before == after:
            unchanged.append((path, before))
            continue

        if before is None:
            change = "new"
        elif after is None:
            change = "removed"
        elif not before or not after:
            change = "changed"
        else:
            change = classify_change(before, after)

        counts[change] += 1
        if change == "downgrade":
            downgrades.append((path, before, after))

        rows.append(
            f"| `{path}` | {_code(before)} | {_code(after)} | {CHANGE_LABELS[change]} |"
        )

    if not rows and not unchanged:
        return None

    summary = [f"**{n} {CHANGE_LABELS[k]}**" for k, n in counts.items() if n]
    if unversioned:
        summary.append(f"**{unversioned} without version string**")
    if unchanged:
        summary.append(f"**{len(unchanged)} with unchanged version**")

    body = "## Qualcomm firmware version changes\n\n"
    body += " | ".join(summary) + ".\n"

    if rows:
        body += "\n| File | Before | After | Change |\n"
        body += "|------|--------|-------|--------|\n"
        body += "\n".join(rows) + "\n"

    if downgrades:
        body += "\n### ⚠️ Downgrades detected\n\n"
        body += "The following firmware files went to an older version:\n\n"
        for path, before, after in downgrades:
            body += f"- `{path}`: {_code(before)} → {_code(after)}\n"

    if unchanged:
        body += "\n### Changed without a version change\n\n"
        for path, versions in unchanged:
            body += f"- `{path}`: {_code(versions)}\n"

    body += "\n---\n\n_Parsed by `contrib/qcom_fw_version_diff.py`_\n"
    return body


# ── CLI ─────────────────────────────────────────────────────────────────────


def dump_versions():
    """Print the versions of all firmware files."""
    for d in FW_DIRS:
        for f in sorted(Path(d).rglob("*")):
            if f.is_symlink() or not f.is_file():
                continue
            versions = get_versions(f.read_bytes(), str(f))
            if versions:
                print(f"{f}: {format_versions(versions)}")


def diff_versions(base_ref):
    changed = get_changed_firmware(base_ref, "HEAD")
    if not changed:
        print("No Qualcomm firmware files changed in this MR.")
        return

    body = build_report(base_ref, changed)
    if body is None:
        print("No version changes detected in changed files.")
        return

    print(body)

    # Post MR comment (only in GitLab CI)
    if os.environ.get("CI_MERGE_REQUEST_IID", ""):
        post_mr_comment(body)


def main():
    p = argparse.ArgumentParser(
        description="Compare Qualcomm firmware versions across an MR diff.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--diff-from-base",
        action="store_true",
        help="Compare MR diff against the merge-request diff base.",
    )
    args = p.parse_args()

    # Plain mode: dump current versions
    if not args.diff_from_base:
        dump_versions()
        return

    base_ref = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", "")
    if not base_ref:
        print("ERROR: CI_MERGE_REQUEST_DIFF_BASE_SHA not set.", file=sys.stderr)
        sys.exit(1)

    diff_versions(base_ref)


if __name__ == "__main__":
    main()
