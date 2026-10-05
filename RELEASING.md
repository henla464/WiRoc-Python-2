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

Several **lines** (generations) can be in development at the same time. A line is
only declared stable when it earns a **new major number**; until then its
pre-stable builds are numbered in the **top of the previous major's space**:

> **Previews of line `N` are numbered `(N-1).9xx`.  The first stable release is `N.0`.**

The `9xx` block sits above everything the previous line has released
(`v1.51 < v1.900`) and below the new line's stable cut (`v1.900 < v2.0`). There
is no number that means "after `v2.x` but before `v3.0`", which is why previews
borrow the *previous* major.

Each line lives on its own branch:

| Line | Branch | Previews (BETA) | First stable (PROD) | Bugfixes (PROD) |
|---|---|---|---|---|
| v1 (shipped) | tags only (`release/1.x` if hotfixing) | — | `1.0` | `1.1` … `1.51` |
| **v2 (current)** | `master` | `1.900`, `1.901`, … | `2.0` | `2.1`, `2.2`, … |
| v3 | `develop-v3` | `2.900`, `2.901`, … | `3.0` | `3.1`, `3.2`, … |
| v4 | `develop-v4` | `3.900`, `3.901`, … | `4.0` | `4.1`, `4.2`, … |

`900` is used (rather than, say, `100`) to leave the whole `…–899` range free for
the line's own bugfixes before it reaches the preview block.

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

## Branches — one branch per active line

**A branch holds a *line* (a body of work), not a *maturity level*.** There is
one long-lived branch per line that is actively being worked on. `master` holds
the current line (the one nearest to release); every line behind it gets its own
`develop-vN` branch. Stability is carried by the release *status* (BETA/PROD),
never by the branch name.

```
   master      ──● v1.900 ──● v1.901 ──● v2.0 ──● v2.1 ──────────────►
   (current line v2)  └─ BETA previews of v2 ─┘ └─ PROD (stable v2) ─┘

                    │   fixes flow up into every later line
                    ▼
   develop-v3  ────────● v2.900 ──● v2.901 ──●  …  ──● v3.0 ──►  promote → master
   (line v3)           └── BETA previews of v3 ──┘    (PROD)

                    │   fixes flow up
                    ▼
   develop-v4  ────────────────────● v3.900 ──● v3.901 ──● … ──● v4.0 ──►
   (line v4)                          └── BETA previews of v4 ──┘  (PROD)
```

### The branch name says the line; the number does not

A preview **borrows the previous major**, so its leading digit is *not* the line
it belongs to:

* `v2.900` is a preview of **line v3** → lives on `develop-v3`.
* `v3.900` is a preview of **line v4** → lives on `develop-v4`.

So when in doubt, read the branch, not the number: `develop-vN` holds line `N`.

### Why one branch per line

Lines overlap in time (you may start v4 work before v3 has shipped). Each line
must be able to
* take preview tags and bugfixes on its own schedule,
* stay free of the other lines' in-progress changes,

so each needs its own branch. `master` is simply the frontmost line; it never
holds two lines at once. Merging two overlapping lines onto one branch is exactly
the coupling this model avoids.

### Branch table

| Branch | Line it holds | Tags cut here |
|---|---|---|
| `master` | the **current** line (frontmost) — v2 today | `v1.9xx` **BETA** previews, `v2.x` **PROD** |
| `develop-vN` | line `N` while it is in development (may be broken) | `v(N-1).9xx` **BETA** previews, `vN.x` **PROD** |
| `feature/*` | one topic, off the `develop-vN` (or `master`) it targets | — |
| `hotfix/*` | patch a shipped release, off `master` | `vN.x` **PROD** |
| `release/N.x` | maintenance of an aged-out line | `vN.x` **PROD** |

### The rules

1. **One branch per active line.** `master` = the frontmost line; each line
   behind it = its own `develop-vN`. Create `develop-vN` when work on line `N`
   starts; retire it (→ `release/N.x`) once `N` has been promoted.
2. **Branch = line; release status = maturity.** A branch hosts BETA previews
   while its line is pre-stable and PROD releases once it stabilises.
3. **Fixes flow up, never down.** Merge `master` → each `develop-vN` (and
   `develop-v3` → `develop-v4`, etc.) so later lines inherit fixes. Do **not**
   merge a later line into an earlier one except at the deliberate stable cut.
4. **Tags are immutable release points.** A branch moves; a tag never does.

## Flows

| Goal | Steps |
|---|---|
| New v3 feature | branch `feature/x` off `develop-v3`, merge back to `develop-v3` |
| Publish a v2 preview | tag `v1.9xx` on `master`; register as **BETA** |
| Publish a v3 preview | tag `v2.9xx` on `develop-v3`; register as **BETA** |
| Publish a v4 preview (before v3 ships) | tag `v3.9xx` on `develop-v4`; register as **BETA** |
| Fix a bug on the shipped v2 line | branch `hotfix/v2.x` off `master`; tag `v2.x`; merge to `master`, then up into every `develop-vN` |
| v2 is stable | tag `v2.0` on `master`; register as **PROD**. Nothing to promote — `master` already is the v2 line. |
| v3 is stable | tag `v3.0` on `develop-v3`; register as **PROD**; then promote `develop-v3` → `master`; move the old v2 line to `release/2.x` |
| v4 is stable | tag `v4.0` on `develop-v4`; register as **PROD**; then promote `develop-v4` → `master`; move the old v3 line to `release/3.x` |

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

Preview of a later line (on its `develop-vN`):
1. Ensure `develop-vN` is good enough for testers.
2. `git tag v(N-1).900 && git push origin v(N-1).900`  (e.g. `v3.900` on `develop-v4`)
3. Register with the **BETA** status, and a readable `releaseName` such as
   `v4 preview 1`.

Stable release:
1. Get the change onto the line's branch (`master` for the current line,
   `develop-vN` for a later line).
2. Tag `vN.0` (or the next minor) and push.
3. Register with the **PROD** status.

Stable cut / promotion of a later line:
1. Tag `vN.0` on `develop-vN`; register as **PROD**.
2. Promote: merge `develop-vN` into `master` (only needed for a later line;
   the current line is already on `master`).
3. Branch `release/(N-1).x` off the last commit of the aged-out line.
4. The promoted `develop-vN` can be deleted; the next new line gets a fresh
   `develop-v(N+1)`.

## Creating a new line's branch

When you start work on line `N`, branch it off whatever base its code should
have (usually the current `master`):

```
git checkout master
git branch develop-vN
git push -u origin develop-vN
```

`develop-v4` is created this way today (currently identical to `master` until
v4 work lands on it).

## Appendix: the two places the webserver compares versions

Fix these to compare `(major, minor)` numerically:

* `Helper::getSort()` — turns `sort=versionNumber` into `ORDER BY versionNumber`
  (used by the release list and the upgrade-script list).
* `slim.php` upgrade-script range filters —
  `versionNumber > :limitFromVersion AND versionNumber <= :limitToVersion`
  (WiRocPython2 at ~`:3404`, WiRocBLEAPI at ~`:3184`).

Until fixed, both are string comparisons (`"2.10" < "2.9"`).
