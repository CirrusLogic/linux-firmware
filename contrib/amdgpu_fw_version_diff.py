#!/usr/bin/python3
# SPDX-License-Identifier: MIT

"""
Compare amdgpu firmware versions between the current branch and the MR diff base.

Delegates all firmware-header parsing to get_amdgpu_fw_version.py by importing
its functions directly (no subprocess, no duplication).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Import from sibling module — handle both:
#   python3 contrib/amdgpu_fw_version_diff.py
#   python3 -c "...from contrib.amdgpu_fw_version_diff import ..."
try:
    from get_amdgpu_fw_version import (
        HEADER_SIZE,
        get_common_version,
        get_dmcub_version_a,
        get_dmcub_version_b,
        get_header,
        int_and_hex,
        PARSERS,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from get_amdgpu_fw_version import (
        HEADER_SIZE,
        get_common_version,
        get_dmcub_version_a,
        get_dmcub_version_b,
        get_header,
        int_and_hex,
        PARSERS,
    )

SCRIPT_DIR = Path(__file__).resolve().parent


def _compact_version(fw_path):
    """Return a compact one-line version string by reusing get_amdgpu_fw_version
    logic, but producing output suitable for table cells.

    Uses the same header parser and version formatters; the difference from
    get_fw_version() is that the result is a single, concise line.
    """
    header = get_header(fw_path)
    if len(header) != HEADER_SIZE:
        return "(parse error)"

    common_vers = get_common_version(header)
    ucode_vers = None

    for parser in PARSERS:
        if re.match(parser["regex"], fw_path.name):
            if parser["ucode_parser"] is not None:
                ucode_vers = parser["ucode_parser"](common_vers.ucode_version)
            break

    # Build compact label
    base = f"v{common_vers.ip_major}.{common_vers.ip_minor}.{int_and_hex(common_vers.ucode_version)}"

    if ucode_vers is not None:
        # DMCUB special — prefer human-friendly major.minor.revision
        parts = []
        for k, v in ucode_vers._asdict().items():
            parts.append(f"{k}={v}")
        return f"{base} ({', '.join(parts)})"

    return base


def _get_changed_firmware(base_ref, target_ref):
    """Return list of amdgpu .bin files changed between base_ref and target_ref."""
    out = subprocess.run(
        ["git", "diff", "--name-only", base_ref, target_ref, "--", "amdgpu/"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode not in (0, 1):
        return []
    return [p for p in out.stdout.strip().splitlines() if p.endswith(".bin")]


def _dump_versions(directory):
    """Return dict {filename: version_string} for all amdgpu .bin files."""
    bin_files = sorted(Path(directory).glob("amdgpu/*.bin"))
    if not bin_files:
        return {}

    versions = {}
    for p in bin_files:
        versions[p.name] = _compact_version(p)
    return versions


def _table_row(name, before, after):
    """Return a single Markdown table row."""
    b = before if before else "(none)"
    a = after if after else "(none)"
    return f"| `{name}` | `{b}` | `{a}` |"


# ── GitLab MR comment ───────────────────────────────────────────────────────


def post_mr_comment(project_id, pipeline_id, summary, table_rows):
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
    token = os.environ.get("CI_JOB_TOKEN", "")

    body = f"## AMDGPU firmware version changes\n\n"
    if summary:
        body += f"{summary}\n\n"
    body += "| File | Before | After |\n"
    body += "|------|--------|-------|\n"
    body += "\n".join(table_rows)
    body += (
        "\n\n---\n\n_"
        "Parsed by [contrib/get_amdgpu_fw_version.py](contrib/get_amdgpu_fw_version.py)"
        "_\n"
    )

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
            print(
                f"Posted new MR comment: {api_url}/projects/{project}/"
                f"merge_requests/{mr_iid}/discussions/{result[0]['id']}"
            )
    except urllib.error.HTTPError as e:
        print(
            f"WARNING: Failed to post MR comment: {e.read().decode()}", file=sys.stderr
        )


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    import argparse

    p = argparse.ArgumentParser(
        description="Compare amdgpu firmware versions across an MR diff.",
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
        versions = _dump_versions(".")
        for name in sorted(versions):
            print(f"{name}: {versions[name]}")
        return

    # Diff mode
    mr_iid = os.environ.get("CI_MERGE_REQUEST_IID", "")
    base_ref = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", "")

    if not base_ref:
        print("ERROR: CI_MERGE_REQUEST_DIFF_BASE_SHA not set.", file=sys.stderr)
        sys.exit(1)

    changed = _get_changed_firmware(base_ref, "HEAD")
    if not changed:
        print("No amdgpu .bin files changed in this MR.")
        return

    # Dump versions from the base commit
    base_versions = {}
    for rel in changed:
        name = os.path.basename(rel)
        result = subprocess.run(
            ["git", "show", f"{base_ref}:{rel}"],
            capture_output=True,
        )
        if result.returncode == 0:
            tmp = Path(f"/tmp/_amdgpu_fw_{name}")
            tmp.write_bytes(result.stdout)
            base_versions[name] = _compact_version(tmp)
            tmp.unlink()
        else:
            base_versions[name] = None

    # Dump versions from working tree
    current_versions = {}
    for rel in changed:
        name = os.path.basename(rel)
        current_versions[name] = _compact_version(Path(rel))

    # Build diff table (only rows where before != after)
    all_names = sorted(set(base_versions) | set(current_versions))
    rows = []
    for name in all_names:
        b = base_versions.get(name, None)
        a = current_versions.get(name, None)
        if b != a:
            rows.append(_table_row(name, b, a))

    if not rows:
        print("No version changes detected in changed files.")
        return

    # Count truly new / removed vs merely changed
    new_files = sum(
        1
        for n in current_versions
        if n not in base_versions or base_versions.get(n) is None
    )
    removed_files = sum(
        1
        for n in base_versions
        if n not in current_versions or current_versions.get(n) is None
    )

    if new_files or removed_files:
        summary = f"**{new_files} new / {removed_files} removed** firmware file(s)."
    else:
        summary = f"**{len(rows)}** firmware file(s) changed."

    print(summary)
    print()
    print("| File | Before | After |")
    print("|------|--------|-------|")
    print("\n".join(rows))

    # Post MR comment (only in GitLab CI)
    if mr_iid:
        post_mr_comment(
            os.environ["CI_PROJECT_ID"],
            os.environ["CI_PIPELINE_ID"],
            summary,
            rows,
        )


if __name__ == "__main__":
    main()
