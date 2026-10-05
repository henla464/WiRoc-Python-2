# Releasing WiRoc-Python-2

This documents the version numbering and branching strategy for this repository.

## Version scheme (do not change)

The only supported version format is **`vMAJOR.MINOR`** (e.g. `v1.51`, `v2.0`).
This is the only scheme understood by the program, the webserver and the mobile
app, so it must not be changed. `versionNumber` is stored as a string in the
webserver database.

* `MAJOR` identifies the line / generation.
* `MINOR` is the release counter within that line.

**No zero-padding.** Minors are plain integers: `v2.0`, `v2.1`, … `v2.10`, … `v2.51`.

## Lines, and how previews are numbered

We keep a **stable** line and a **next** line in parallel. A line is only
declared stable when it earns a **new major number**; until then its pre-stable
builds are numbered in the **top of the previous major's space**:

> **Previews of line `N` are numbered `(N-1).9xx`.  The first stable release is `N.0`.**

The `9xx` block sits above everything the old line has released
(`v1.51 < v1.900`) and below the new line's stable cut (`v1.900 < v2.0`). There
is no number that means "after `v2.x` but before `v3.0`", which is exactly why
the previews borrow the *old* major.

Example — the current transition (v1 → v2) and the next one (v2 → v3):

| Line | Branch | Previews (BETA) | First stable (PROD) | Bugfixes (PROD) |
|---|---|---|---|---|
| v1 (shipped) | tags only (`release/1.x` if hotfixing) | — | `1.0` | `1.1` … `1.51` |
| **v2 (current, being stabilised)** | `master` | `1.900`, `1.901`, … | `2.0` | `2.1`, `2.2`, … |
| **v3 (the larger work)** | `develop` | `2.900`, `2.901`, … | `3.0` | `3.1`, `3.2`, … |

`900` is used (rather than, say, `100`) to leave the whole `…–899` range free for
the old line's own bugfixes before it reaches the preview block.

## Version comparison in the webserver must be numeric

`versionNumber` is an `nvarchar` column and the webserver currently compares it
**as a string**, where `"2.10" < "2.9"` — which is wrong, and is exactly why
zero-padding was previously suggested. **The no-padding scheme requires the
webserver comparison to be made numeric** (compare `(major, minor)` as
integers). The two places to change are listed in the Appendix.

Until that fix lands, treat the *ordering* returned by the API as unreliable for
minors of different digit-length (e.g. `2.9` vs `2.10`). Exact matching of a
specific version string is unaffected.

## Release status channel

The webserver has a release-status dimension (`ReleaseStatuses`):

| keyName | sortOrder | Meaning |
|---|---|---|
| `DEV` | 0 | internal |
| `BETA` | 5 | pre-release / preview |
| `PROD` | 10 | production |

Each device has a `releaseStatusKeyName`, and the release feed only returns
releases whose status `sortOrder >=` the device's. So a **PROD** device never
sees BETA/DEV releases. This is how preview builds stay off the production fleet.

* A **preview** release is registered with status **BETA** (or `DEV` internally).
* A **stable** release is registered with status **PROD**.

## Branches — branch = line, status = maturity

Two long-lived branches, one per line, plus short-lived topic branches.

```
   master   ──● v1.51 ──● v1.900 ──● v1.901 ──● v2.0 ──● v2.1 ──►
   (v2 line)            └─ BETA previews of v2 ─┘ └ PROD, stable v2 ┘
                        ( v2.0 is the first stable v2 — the major bump
                          itself is the "now stable" cut )

               fixes always flow up:  master ──► develop
               │
               ▼
   develop  ────● v2.900 ──● v2.901 ──●  ...  ──● v3.0 ──►
   (v3 line)    └─ BETA previews of v3 ─┘       (PROD)
                                                 │
               promote at the stable cut:        │
                       develop ──► master ◄───────┘
```

* `hotfix/*` branches off `master` (in the diagram, off any `v2.x` tag) to patch
  a shipped version, then merges back to `master` and forward into `develop`.
* `feature/*` branches off `develop` and merges back into `develop`.

### Branch table

| Branch | What it is | Tags cut here |
|---|---|---|
| `master` | the **current** line (v2) — what becomes `v2.0` | `v1.9xx` **BETA** previews, `v2.x` **PROD** |
| `develop` | the **next** line (v3), built in parallel — may be broken | `v2.9xx` **BETA** previews, `v3.x` **PROD** |
| `feature/*` | one topic, off `develop` | — |
| `hotfix/*` | patch a shipped release, off `master` | `v2.x` **PROD** |
| `release/1.x` | maintenance of an older line once `master` moves on | `v1.x` **PROD** |

### The rules

1. **The branch identifies the line; the release status identifies maturity.**
   Both `master` and `develop` host BETA previews while their line is
   pre-stable, and PROD releases once it stabilises. (A release status is *not*
   fixed to a branch.)
2. **Fixes flow up, never down.** Merge `master` → `develop` regularly (e.g.
   after each v2 release) so the next line inherits bugfixes. Do **not** merge
   `develop` → `master` except at the deliberate stable cut.
3. **Tags are immutable release points.** A branch moves; a tag never does.

## Flows

| Goal | Steps |
|---|---|
| New v3 feature | branch `feature/x` off `develop`, merge back to `develop` |
| Publish a v2 preview | tag `v1.9xx` on `master`; register as **BETA** |
| Publish a v3 preview | tag `v2.9xx` on `develop`; register as **BETA** |
| Fix a bug on the shipped v2 line | branch `hotfix/v2.x` off `master`; tag `v2.x`; merge to `master`, then into `develop` |
| v2 is stable | tag `v2.0` on `master`; register as **PROD**. Nothing to promote — `master` already is the v2 line. |
| v3 is stable | tag `v3.0` on `develop`; register as **PROD**; then promote `develop` → `master`; move the old line to `release/2.x` |

## Cutting a release (checklist)

Every release is a git tag **plus** a `WiRocPython2Releases` row in the webserver
(`versionNumber`, `releaseStatusId`, HW min/max, `md5HashOfReleaseFile`).

Preview of the current line (on `master`):
1. Ensure `master` is good enough for testers.
2. `git tag v1.900 && git push origin v1.900`
3. Register `versionNumber="1.900"` with the **BETA** status. Set `releaseName`
   to something readable like `v2 preview 1`, since `1.900` does not obviously
   say "v2".
4. Only BETA/DEV devices pick it up.

Stable release:
1. Get the change onto the line's branch (`master` for v2, `develop` for v3).
2. Tag `vN.0` (or the next minor) and push.
3. Register with the **PROD** status.

Stable cut to a new line:
1. Tag `vN.0` on the line's branch; register as **PROD**.
2. Promote: merge the line's branch into `master` (only needed when the line
   lived on `develop`).
3. Branch `release/(N-1).x` off the last commit of the old line for critical
   fixes.

## Appendix: the two places the webserver compares versions

Fix these to compare `(major, minor)` numerically:

* `Helper::getSort()` — turns `sort=versionNumber` into `ORDER BY versionNumber`
  (used by the release list and the upgrade-script list).
* `slim.php` upgrade-script range filters —
  `versionNumber > :limitFromVersion AND versionNumber <= :limitToVersion`
  (WiRocPython2 at ~`:3404`, WiRocBLEAPI at ~`:3184`).

Until fixed, both are string comparisons (`"2.10" < "2.9"`).
