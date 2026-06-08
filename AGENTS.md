# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this
repository. Humans should start with [README.md](README.md); this file
restates the contribution rules in the operational order an agent needs them.

## What this repository is

This is **linux-firmware**, the upstream collection of binary firmware images
loaded by the Linux kernel at runtime. It is *not* a normal software project:

- The payload is **binary blobs**, not source you compile here. A few entries
  ship buildable source (see `keyspan_pda/`), but the overwhelming majority are
  redistributed binaries.
- The most important file is **`WHENCE`** — a hand-maintained manifest that
  records the origin, license, and redistribution terms of *every* file.
- The repository's core value is **licensing provenance**, not code. Most of
  the rules below exist to keep that provenance accurate and auditable.

Upstream lives at <https://gitlab.com/kernel-firmware/linux-firmware.git>.

## Golden rules (read before any change)

1. **Every file in git must be accounted for in `WHENCE`.** Adding a firmware
   blob without a matching `WHENCE` entry breaks the build. Removing or renaming
   a file without updating `WHENCE` does too.
2. **Never invent license information.** The license and the redistributability
   of a blob are facts that come from the firmware's owner — usually conveyed in
   the submitter's commit and `Signed-off-by`. If you don't have it, don't guess.
   Surface the gap to the user instead.
3. **Always run `make check` before considering a change complete** (see below).
4. **Preserve the `Signed-off-by` line.** It is a legal attestation of the right
   to redistribute. Never add, fabricate, or alter one on someone's behalf.
5. **Don't edit binary firmware files.** Agents add, move, link, or remove
   blobs and document them; they do not modify blob contents.

## The most common task: adding or updating a firmware file

1. Place the blob(s) in the appropriate vendor/driver subdirectory (e.g.
   `qcom/`, `cirrus/`, `intel/`). Match the directory convention of similar
   existing files.
2. Add a stanza to `WHENCE` (see "WHENCE format" below) declaring the file and
   its license. Group it with related entries; keep the file roughly ordered as
   the surrounding content is.
3. If the firmware needs a new license, add a `LICENSE.<vendor>` (or
   `LICENCE.<vendor>` — both spellings exist) file and reference it from
   `WHENCE` with `See LICENSE.<vendor> for details.`
4. Run `make check`.
5. Commit with a `Signed-off-by` from someone authoritative on the license (see
   "Commit conventions").

## WHENCE format

`WHENCE` is parsed by `check_whence.py`, so the syntax is load-bearing. The
keywords that matter:

- `Driver: <name> - <description>` — human-readable section header.
- `File: <path>` — a binary firmware file tracked in git. This is the usual one.
- `RawFile: <path>` — a file shipped verbatim (not converted to ihex form).
- `Link: <linkname> -> <target>` — a symlink. The target is relative to the
  link's directory. `check_whence.py` verifies the target exists and that links
  don't point at other links.
- `Source: <path>` — source for firmware that is compiled here (rare).
- `Version:` / `Info:` — optional metadata lines.
- `Licence:` / `License:` — the license terms. Either name an inline word
  (e.g. `Redistributable`, `GPLv2`) or refer out with
  `See <LICENSE-file> for details.` The referenced file must exist in the tree.

Paths with spaces are escaped as `\` in `WHENCE`. Study a few existing stanzas
in `WHENCE` before writing a new one — matching an existing pattern is the
safest approach.

## Validation: `make check`

`make check` runs `pre-commit run --all-files`, which is the same gate CI
enforces. It includes:

- **`check_whence.py`** — the critical check. It cross-references `WHENCE`
  against `git ls-files` and fails if: a tracked file isn't listed, a listed
  file doesn't exist, a `File:` entry is actually a symlink, a `Link:` target is
  missing, duplicate entries exist, or execute bits are wrong (blobs must *not*
  be executable; the listed scripts must be).
- **shellcheck** on shell scripts, **black** on Python, **markdownlint** on
  Markdown, plus symlink and YAML sanity checks.

If `pre-commit` isn't installed: `pip install pre-commit`. You can run the
manifest check alone with `./check_whence.py` from the repo root.

Note: `check_whence.py` uses `git ls-files`, so **stage new files** (`git add`)
before running it, or it won't see them and will report a phantom mismatch.

## Commit conventions

- Subject line style: `<vendor/area>: <imperative summary>`, e.g.
  `qcom: Update DSP firmware for qcs8300 platform` or
  `cirrus: cs35l56: Add firmware for Cirrus Amps for a Dell laptop`.
- A **`Signed-off-by:`** line is **mandatory** and must come from someone with
  authority over the firmware's licensing (typically from within the owning
  company). CI (`ci-fairy check-commits --signed-off-by`) rejects commits
  without it. Do not add one yourself — ask the user.
- Never include a `CONFIDENTIALITY STATEMENT` anywhere in the commit or MR;
  per README that causes the firmware to be rejected outright.
- New work goes on a branch and is submitted as a GitLab MR, an emailed git
  binary diff, or a pull request to `linux-firmware@kernel.org`.

## Repository tooling (don't reinvent these)

- `copy-firmware.sh` — installs firmware to a destdir per `WHENCE` (used by
  `make install` / `install-xz` / `install-zst`). Supports optional compression.
- `dedup-firmware.sh` — replaces duplicate installed files with symlinks
  (`make dedup`).
- `build_packages.py` — builds `.deb`/`.rpm` (`make deb` / `make rpm`); templates
  in `contrib/templates/`.
- `make dist` — builds a release tarball.
- `contrib/process_linux_firmware.py` — maintainer-side processing helper.

## Things to leave alone unless explicitly asked

- The `known_files` / `executable_files` allowlists inside `check_whence.py`:
  only touch them when you are genuinely adding a new top-level tooling file,
  and understand you're changing the validator itself.
- License text files (`LICENSE.*` / `LICENCE.*`): treat as authoritative legal
  text. Add new ones when a new license is needed; don't reword existing ones.
