# License Requirements for linux-firmware Submissions

This document describes the licensing requirements for firmware submitted to the
linux-firmware repository. It explains which licenses the project accepts, the
criteria a license must meet, and how new license texts are reviewed.

These requirements will be used to evaluate new firmware license submissions
or materially changed license terms.  Firmware licenses included before this
requirement document was introduced may not fully adhere to the requirements
and will be considered an exception at this time.  The project may choose to
work with vendors to address existing license inconsistencies.

Nothing in this document is legal advice. It describes the policy of the
linux-firmware project.

---

## 1. Purpose and scope of this repository

The purpose of this repository is to provide standalone firmware images and
related device data files that:

- is loaded by the Linux kernel, a kernel driver, or a device the kernel
supports. The firmware should be necessary for hardware support, device
operation, or boot, in service of an open source kernel or driver
functionality. Submissions to this repository must be a standalone firmware
image or device-data file — not a host application, shared library, kernel
driver, or other userspace or operating-system component. Firmware may be
binary-only. Source is welcome whenever the firmware's owner can provide it,
but a binary-only image is acceptable as long as its license meets the
criteria.

- is provided under a license that allows unrestricted redistribution by
everyone, with no signatures, registration, click-through, or payment required.
Anyone may copy the firmware onward to anyone else — recipients who have no
relationship with a company and have signed nothing. This is not specific to
operating systems or any class of redistributor.

A license that works for your direct customers but not for an arbitrary
downstream recipient cannot be accepted. This document describes the bar the
project applies to keep that unrestricted redistribution intact.

## 2. Licenses the project accepts

### 2.1 Existing license texts already in the repository (preferred)

The `LICENSES/` directory contains every license text currently in use, both
standard open-source licenses (e.g. `Apache-2.0`, `GPL-2.0`, `GPL-3.0-only`)
and vendor-specific redistributable firmware licenses (`LICENCE.<vendor>` /
`LICENSE.<vendor>` files).

**If your company already has a license file in `LICENSES/`, reuse it.** New
firmware files from the same vendor should reference the existing license in
their `WHENCE` entry. Do not submit per-product or per-file license variants;
proliferation of near-identical texts multiplies review burden for everyone
who has to evaluate them.

### 2.2 Standard open-source licenses

Firmware offered under a well-known OSI/FSF license (MIT, BSD-2/3-Clause,
Apache-2.0, GPL-2.0, etc.) is welcome and is the easiest path through review.

One important caveat: **copyleft licenses carry source code obligations**, and
a submission under such a license should include the corresponding source code.

### 2.3 Proprietary redistributable firmware licenses

Most firmware in the repository is under vendor-specific proprietary licenses.
These are acceptable when they grant the rights in section 3 and confine their
restrictions to those in section 3.2.

## 3. Criteria a license must meet

### 3.1 Required grants

A firmware license must, at minimum:

1. **Permit redistribution, royalty-free, by anyone — unconditionally.** The
   grant must not be contingent on incorporating the firmware into a product,
   operating system, or anything else, because recipients are free to copy the
   firmware onward whether or not they build anything from it. A grant scoped
   to product incorporation does not reach those bare redistributors or the
   downstream archives and mirrors they create. Grants limited to a named
   licensee, to "authorized partners," or contingent on a separate agreement
   are likewise not acceptable.
2. **Permit use with the associated hardware, royalty-free.** Recipients must
   be able to actually load and run the firmware on the device without further
   permission or payment.
3. **Include a patent grant adequate for device operation.** The upstream
   project requires that "redistributable" includes an implicit or explicit
   patent license to end users sufficient for full functionality of the device
   with the firmware. If your standard license text is silent on patents,
   expect this to be raised in review; an explicit grant avoids the question.
4. **Permit copying necessary for distribution mechanics** — mirroring,
   inclusion in install media and container/cloud images, and packaging
   (compression, packaging-format transformation) — even where modification of
   the firmware image itself is prohibited.
5. **Be perpetual and irrevocable for distributed copies.** A license that the
   vendor can revoke at will, or that expires, makes every downstream archive
   and released distribution image retroactively non-compliant and is not
   acceptable.

### 3.2 Restrictions that are acceptable

The project accepts the following restrictions in firmware licenses:

- **Prohibition on modification** of the firmware image.
- **Prohibition on reverse engineering, disassembly, or decompilation.**
- **Restriction of use to the vendor's associated hardware** (the hardware the
  firmware was designed for).
- **Requirement that the license text accompany redistributed copies.**
- **Warranty disclaimers and limitations of liability.**
- **Trademark non-grants** (the license conveys no trademark rights).
- Any restriction that would already be acceptable in an ordinary
  distribution-approved software license.
- **Export-control notices** that inform recipients of applicable law. These
  are tolerated when they are informational; clauses that convert export
  compliance into an affirmative certification, reporting, or indemnification
  obligation on redistributors are not.

### 3.3 Terms that will cause rejection

A license containing any of the following will not be accepted:

- "Internal use only," evaluation-only, or any grant that excludes
  redistribution.
- Redistribution grants scoped to "as part of" a product, operating system,
  or distribution. Older license files in the tree contain such language; new
  licenses must permit redistribution by anyone, product or not (see 3.1).
- Fees, royalties, or per-unit accounting of any kind.
- **Confidentiality or non-disclosure terms.** Note that this applies to the
  submission as well as the license: per the project README, a submission
  email, patch, or merge request carrying a corporate confidentiality
  statement will never be accepted. Make sure your mail system does not append
  one.
- Requirements for click-through acceptance, registration, account creation,
  or execution of a separate agreement before use or redistribution.
- Grants limited to named licensees or to parties with an existing business
  relationship with the vendor.
- Audit rights, usage reporting, or indemnification obligations imposed on
  redistributors or users.
- Termination at the vendor's convenience, or time-limited grants.
- Field-of-use restrictions beyond association with the vendor's hardware
  (e.g. "non-commercial only," "not for use in competing products,"
  geographic restrictions).
- Choice-of-law/venue or arbitration clauses that impose affirmative
  obligations on passive recipients. (A simple governing-law statement is
  usually tolerated; mandatory arbitration with fee-shifting is not.)
- Copyleft-licensed binaries without corresponding source (see 2.2).
- Terms that attempt to bind the linux-firmware project or kernel.org to any
  obligation. The repository is a conduit; it cannot accept duties on your
  behalf.

## 4. Mechanics: where license information lives in a submission

Every submission must encode its licensing in the repository's standard
structures so that automated tooling and downstream packagers can consume it.

**The `WHENCE` file.** Every firmware file in the tree has an entry in
`WHENCE` documenting its origin and licensing. A typical entry:

```text
Driver: foo -- FooCorp FOO-1234 Wireless Adapter

File: foocorp/foo1234.bin
Version: 2.7.1

Licence: Redistributable. See LICENSE.foocorp for details.
```

The `Licence:` line must clearly state the license and that the firmware is
redistributable. For standard licenses, name the license (e.g.
`Licence: GPL-2.0`, with source files listed). Optional `Version:` and `Info:`
lines, and `Link:` entries for symlinks, complete the entry.

**The `LICENSES/` directory.** If the license text is more than a short
statement, it must be placed as a separate file in `LICENSES/` and referenced
from `WHENCE` (e.g. "See LICENSE.foocorp for details"). The preferred naming
convention for new vendor license files is `LICENSE.<vendor>`; both
`LICENSE.<vendor>` and `LICENCE.<vendor>` spellings exist in the tree and are
accepted, but new files should use `LICENSE.<vendor>`. Standard licenses use
their SPDX-style name (e.g. `GPL-2.0`). One file per vendor license text —
reuse it across all your firmware.

**Signed-off-by.** Every commit must include a `Signed-off-by:` line from
someone with authority over the licensing of the firmware — typically a person
within the company that owns or controls it. This is the project's provenance
record: it attests that the submitter has the right to submit the firmware
under the stated license and that it may be redistributed under those terms.
If corporate infrastructure makes submitting from a company account difficult,
the Signed-off-by must still use the company address; the submission itself
may come from a personal address with the company address on CC.

Firmware must be submitted by the vendor that owns or controls it, or with
the vendor's explicit participation. Third-party submissions made without
vendor involvement will not be accepted: either the commit must carry a
`Signed-off-by` from the vendor, or the vendor must be copied on the
submission and acknowledge it.

**Validation.** Run `make check` before submitting; `check_whence.py` verifies
that `WHENCE` and the tree agree. CI runs the same checks on merge requests.

**Commit message.** Where possible, include a changelog of what changed in the
firmware itself. For binary files, the commit message is usually the only
human-readable record of a change. If an AI tool assisted in producing the
contribution, disclose it with an `Assisted-by:` (or similar) trailer in
addition to the Signed-off-by.

**Submission paths.** Open a merge request on the upstream GitLab project, or
send a git binary diff or pull request to `linux-firmware@kernel.org`.

## 5. How new license texts are reviewed

This process applies when a submission introduces a license text not already
present in `LICENSES/`, or modifies an existing one.

1. **Flag it.** State prominently in the merge request or cover letter that
   the submission introduces a new license text. Unflagged new licenses delay
   review for the whole series.
2. **Submit the complete text** as a `LICENSES/LICENSE.<vendor>` file in the
   same MR as the firmware it covers, referenced from the `WHENCE` entries.
   The text must unambiguously identify the copyright holder and licensor.
3. **Maintainer review.** Maintainers review the text against section 3. They
   are applying project policy, not giving your company legal advice; the
   burden of ensuring the license says what you intend rests with your counsel.
4. **Outside consultation.** For novel terms, maintainers may seek additional
   legal input before deciding. Vendors should expect questions and,
   occasionally, requests for clarification from someone able to speak
   authoritatively for the licensor.
5. **Outcomes.** A new license is accepted as-is, accepted after the vendor
   issues a clarified or corrected text, or declined with the problematic
   terms identified. Once accepted, the text becomes the vendor's canonical
   license file and is treated as settled precedent — subsequent submissions
   reusing it verbatim need no license review.
6. **Relicensing existing firmware.** The firmware is the submitter's
   intellectual property, and the project does not control its licensing
   beyond applying the section 3 criteria. A vendor may relicense their own
   firmware whenever their existing license permits, submitting the new text
   as they would any license change; the project's only requirement is that
   the replacement still meets section 3. Two mechanical consequences are
   worth being deliberate about:

   - **One license file governs every firmware that references it.** A
     vendor's firmware typically points at a single `LICENCE.<vendor>` file,
     so editing that file changes the terms for *all* of it at once. To place
     new firmware under different terms while leaving existing firmware as-is,
     add a distinct license file for the new terms and point only the new
     firmware's `WHENCE` entry at it.
   - **Copies already distributed keep their original terms.** This follows
     from copyright, not project policy: a grant made under the prior
     license — which the criteria require to be irrevocable for distributed
     copies (5.1) — cannot be withdrawn from copies already received, and any
     mirror or archive that has not taken the update still carries the text it
     was distributed with. Relicensing is forward-looking in effect, whatever
     the current tree shows.

Review of a routine firmware update against an existing license is fast.
Review of a new license text takes as long as it takes — maintainers are
volunteers, and novel legal text takes longer than routine updates. Vendors
can compress the timeline more than anyone else can, by starting from an
already-accepted license text (their own or structurally similar ones in
`LICENSES/`) instead of novel drafting. Shorter texts also review faster: the
most reviewable licenses in `LICENSES/` are under a page, and every
additional clause adds burden for everyone who must evaluate it.

---

## References

- linux-firmware repository and README:
  <https://gitlab.com/kernel-firmware/linux-firmware>
