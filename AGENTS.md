# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this
repository. Humans should start with [README.md](README.md); this file
restates the contribution rules in the operational order an agent needs them.

## What this repository is

This is **linux-firmware**, the upstream collection of binary firmware images
loaded by the Linux kernel at runtime. It is *not* a normal software project:

- The payload is **normally binary blobs** rather than source you build here —
  though contributors *may* provide source, and it's welcome where the firmware
  owner permits it (see `keyspan_pda/` for a built-from-source example). The
  large majority are redistributed binaries.
- The most important file is **`WHENCE`** — a hand-maintained manifest that
  records the origin, license, and redistribution terms of *every* file.
- The repository's core value is **licensing provenance**, not code. Most of
  the rules below exist to keep that provenance accurate and auditable.

Upstream lives at <https://gitlab.com/kernel-firmware/linux-firmware.git>.

## Golden rules (read before any change)

1. **Every file in git must be accounted for** — *almost always* by a `WHENCE`
   entry. Adding a firmware blob without one breaks the build; removing or
   renaming one without updating `WHENCE` does too. **The exception is
   repository tooling/metadata** (this file, `README.md`, `check_whence.py`,
   etc.), which is registered in the `known_files` allowlist *inside*
   `check_whence.py`. If `make check` reports a non-firmware file is
   unaccounted for, add it to that allowlist — **never to `WHENCE`** (see
   "Things to leave alone").
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
5. Commit with a `Signed-off-by` from someone authoritative on the license,
   and — if an agent helped produce the change — a trailer noting AI
   involvement (e.g. `Assisted-by:`). See "Commit conventions".

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

Spaces in paths are backslash-escaped (e.g. `foo\ bar.bin`).

**Block structure.** `WHENCE` is a series of blocks separated by a delimiter
line of dashes. A block opens with one or more `Driver:` lines, then one or
more *sections* separated by blank lines. A section is a group of
`File:`/`RawFile:` entries, optionally annotated, closed by a `Licence:` line.
By convention:

- If a `Driver:` block for your device already exists, **add your files to it**
  instead of starting a duplicate block.
- A `Version:`/`Info:` line annotates the `File:` directly above it.
- A `Licence:` line applies to the files in its section. This grouping is a
  convention for human readers — `check_whence.py` does not enforce which files
  a `Licence:` covers — so keep each section's license unambiguous. A
  license/section may precede its firmware files if that reads more naturally.

Study a few existing stanzas in `WHENCE` before writing a new one — matching an
existing pattern is the safest approach.

## Validation: `make check`

Run **`make check`** before considering any change complete. It runs
`pre-commit run --all-files` — the same gate CI enforces — covering the
`WHENCE`↔tree check plus shell, Python, and Markdown linting. **Treat
`make check` as the single source of truth; don't invoke the individual
checkers directly**, so the rule set can grow without this doc going stale.

If `pre-commit` isn't installed: `pip install pre-commit`.

Note: the `WHENCE` check reads `git ls-files`, so **stage new files
(`git add`) before running `make check`** — otherwise they're invisible to the
check and it reports a phantom mismatch.

## Commit conventions

- Subject line style: `<vendor/area>: <imperative summary>`, e.g.
  `qcom: Update DSP firmware for qcs8300 platform` or
  `cirrus: cs35l56: Add firmware for Cirrus Amps for a Dell laptop`.
- A **`Signed-off-by:`** line is **mandatory** and must come from someone with
  authority over the firmware's licensing (typically from within the owning
  company). CI (`ci-fairy check-commits --signed-off-by`) rejects commits
  without it. Do not add one yourself — ask the user.
- If an AI agent assisted in producing the commit, record it with a trailer
  such as `Assisted-by: <tool/model>` (an equivalent `Co-developed-by:` /
  `Co-Authored-By:` is fine). The exact tag isn't critical; surfacing that AI
  was involved is.
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
