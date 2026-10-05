# Releasing WiRoc-Python-2

This documents the version numbering and branching strategy for this repository.

## Version scheme (do not change)

The only supported version format is **`vMAJOR.MINOR`** (e.g. `v1.51`, `v2.0`).
This is the only scheme understood by the program, the webserver and the mobile
app, so it must not be changed. The `versionNumber` is stored as a string
(e.g. `"2.0"`) in the webserver database.

* `MAJOR` identifies the line / generation.
* `MINOR` is the release counter within that line.

## The two lines

We maintain a **stable** line and a **next** line in parallel.

| Line | Content | Where | Numbers |
|---|---|---|---|
| v2 (stable) | current code, stabilized | `master` | `2.0` … `2.9` |
| v3 (next) | the larger work | `develop` | previews `2.900` … `2.999`, then stable `3.0` |

The v3 work needs to be released (and tested) *before* it is stable, but there is
no number that sits "after `v2.x` but before `v3.0`". We solve this by numbering
pre-stable v3 builds as high v2 minors (`2.9xx`) and marking them **BETA**, then
cutting a clean `3.0` (**PROD**) as the first stable v3 release.

### Numbering rules

1. **Stable v2 minors stay single-digit:** `2.0`, `2.1`, … `2.9`.
2. **v3 previews use exactly three digits:** `2.900`, `2.901`, … `2.999`.
3. **Never emit `v2.10`** (see the string-comparison caveat below).
4. **The first stable v3 release is `v3.0`** (PROD).
5. v3 bugfixes after that: `3.1`, `3.2`, …

Why these rules: the webserver compares `versionNumber` **as a string**, where
`"2.10" < "2.9"`. Keeping v2 minors single-digit and previews exactly three
digits makes string order agree with numeric order at every boundary
(`2.9 < 2.900 < … < 2.999 < 3.0`).

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

Rules:

* A **preview** release is registered with status **BETA** (or `DEV` internally).
* A **stable** release is registered with status **PROD**.

## Branches

| Branch | Purpose | Releases tagged here |
|---|---|---|
| `master` | stable trunk (default branch). Always shippable. | `PROD` |
| `develop` | integration for the next line. May be broken. | `BETA` previews |
| `feature/*` | one topic, off `develop` | — |
| `hotfix/*` | patch a shipped stable release, off `master` | `PROD` |
| `release/2.x` | maintenance of an older line once `master` moves on | `PROD` |

### The two rules

1. **Fixes flow up, never down.** Merge `master` into `develop` (regularly, e.g.
   after each v2 release) so the v3 line inherits bugfixes. Do **not** merge
   `develop` into `master` except at the deliberate stable cut.
2. **Tags are cut by branch:** `master` → `PROD`, `develop` → `BETA`.

## Flows

| Goal | Steps |
|---|---|
| New v3 feature | branch `feature/x` off `develop`, merge back to `develop` |
| Publish a v3 preview | tag `v2.9xx` on `develop`; register as **BETA** |
| Fix a bug on the shipped v2 line | branch `hotfix/v2.x` off `master`; tag `v2.x`; merge to `master`, then into `develop` |
| v3 is stable | tag `v3.0` on `develop`; register as **PROD**; promote `develop` → `master`; move the old line to `release/2.x` |

## Cutting a release (checklist)

Every release is a git tag **plus** a `WiRocPython2Releases` row in the webserver
(`versionNumber`, `releaseStatusId`, HW min/max, `md5HashOfReleaseFile`).

Preview (v3, pre-stable):
1. Ensure `develop` is green enough for testers.
2. Tag, e.g. `git tag v2.905 && git push origin v2.905`.
3. Register `versionNumber="2.905"` with the **BETA** status. (Optionally set
   `releaseName` to something readable like `v3 preview 5`, since `2.905` will
   not obviously be a v3 build.)
4. Only BETA/DEV devices pick it up.

Stable v2:
1. Get the change onto `master` (directly, or via `hotfix/*`).
2. Tag `v2.x` and push.
3. Register with the **PROD** status.

Stable cut to v3:
1. Tag `v3.0` on `develop`; register with the **PROD** status.
2. Promote: merge (or fast-forward) `develop` into `master`.
3. Branch `release/2.x` off the last v2 commit for any critical fixes.

## Caveat: version strings are compared as strings

The webserver compares `versionNumber` (an `nvarchar` column) textually in two
places:

* `ORDER BY versionNumber` (only when a client passes `sort=versionNumber`).
* the upgrade-script range filter
  `versionNumber > :limitFromVersion AND versionNumber <= :limitToVersion`.

Both order/compare `"2.10" < "2.9"`. The numbering rules above keep every real
boundary (`2.9 → 2.900 → 2.999 → 3.0`) correct for both. If the scheme ever has
to support two-digit minors above 9 in a line, the server comparison must be made
numeric instead (e.g. a sort-order column, or split/CAST the major and minor).
