# Open-Sourcing Plan — `ndsmath`

> **Status:** Implementation in progress on branch `feature/open-source-prep`.
> **Working doc:** This file is scratch for the open-sourcing effort. Relocate to
> `docs/` or delete before the repository goes public.

## Implementation status (branch `feature/open-source-prep`) — PR #19, **CI fully green** ✅

**Done & CI-verified (all 15 jobs green):**
- LICENSE migration: root + per-language copies (`python/`, `cpp/`, `java/`, `js/`, `go/`, `rust/`); MIT classifier; URLs fixed; Python 3.14. CI `check-license` enforces copies match root byte-for-byte.
- Shared parity vectors (`test-vectors/`) from the Python reference; CI `check-parity-vectors` guards against drift.
- **All six languages** implemented and tested against the golden vectors, green in CI: Python (3.10–3.14), C++ (Linux/macOS/Windows), Java (JaCoCo ≥95%), JS/TS (100%), Go, Rust.
- C++ now consumes the parity vectors (Catch2 → dependency-free harness + header-only nlohmann/json); `PackedTileId::value()` fixed to **signed int32** per spec; Windows DLL co-located.
- SPDX `MIT` headers across all sources (existing + new ports).
- CI rewritten: 6-language matrix + parity/license checks + Codecov upload + per-job timeouts; Artifactory removed; publish jobs scaffolded (PyPI OIDC active path; npm/crates/Maven gated behind repo vars).
- `CONTRIBUTING.md`, `SECURITY.md`; README rewritten (badges + domain primer); CHANGELOG updated.

**Partial:**
- Coverage uploaded to Codecov for Python/Java/JS/Go/Rust; hard **≥95% gate only on Java** (JaCoCo). C++ has no coverage instrumentation yet; no `codecov.yml` threshold for the others.

**Not started:**
- Lint/format/static analysis (ruff/mypy, clang-format/-tidy, spotless, `.pre-commit-config`, CodeQL, Dependabot).
- Hosted docs site (GitHub Pages: Sphinx/Doxygen/Javadoc) + `examples/` dirs.
- Actual distribution: nothing published. PyPI OIDC env, npm org, crates.io name reservation, Maven creds, Conan/vcpkg recipes, GitHub Release automation — mostly account-gated (Appendix B/C).

**Skipped per maintainer:** Code of Conduct, PR template, issue templates, CODEOWNERS.

**Pre-publish cleanups:** remove `api_docs_review.md` (internal repo refs); optional `NOTICE`/THIRD-PARTY (GLM, nlohmann/json).

**Open decisions:** copyright year (legal, Q1); Go module layout (Q10); Java Maven groupId (confirm with `ndsev` Maven team).

**C++ spec-compliance fixes — DONE** (verified against the normative spec in `_ext/` + the full golden parity set): north/south (and east/west) neighbours rewritten via deinterleave/wrap/reinterleave; `boundingBoxFromTileIds` added; `lonNdsDelta`/`latNdsDelta` corrected to `360/2^32` / `180/2^31`; `from_morton_and_level` negative-coord off-by-one fixed; `value()` signed int32. The C++ parity test now validates the full golden set (only out-of-range representation edges skipped). Other languages were already parity-faithful to the (spec-correct) Python reference.

This plan turns the private, association-internal `ndsmath` repo into a polished
public open-source project. It is organized as decisions → open questions →
phased work, with a per-file licensing checklist at the end (the riskiest part).

---

## Decisions locked in

| Topic | Decision |
|---|---|
| **License** | MIT + an explicit no-patent-grant clause (canonical text from legal in [Appendix A](#appendix-a--canonical-license-text-from-legal)). Labeled as **`MIT`** in registry classifiers and `SPDX-License-Identifier` headers; the LICENSE file carries the patent carve-out. |
| **Contributions** | **Issues only.** External pull requests are *not* accepted; NDS implements requested changes internally. No CLA/DCO tooling needed. |
| **Python support** | Add **3.14** to the support matrix and classifiers (currently 3.10–3.13). `requires-python` stays `>=3.10`. |
| **Languages** | Existing: **C++, Python**. To add: **Java, JavaScript/TypeScript, Go, Rust** — all first-class, validated against shared parity vectors (Phase 1). |
| **Coverage** | Gate CI at **≥95% line + branch** across all three languages (not exact-100%). |
| **Distribution** | **Drop the NDS Artifactory deploy entirely.** Publish to public registries: PyPI (Python), Maven Central (Java), Conan/vcpkg (C++). |
| **Name / repo** | Public name + GitHub repo: **`ndslive-math`** (`github.com/ndsev/ndslive-math`). Python: dist `ndslive-math`, import `ndslive.math`. **C++ stays `ndsmath`** (target, `<ndsmath/...>` headers, `namespace ndsmath`) — *do not rename*; downstream tools already depend on it. |
| **Java** | Build with **Gradle**; publish artifactId **`ndslive-math`** to Maven Central. **groupId TBC** — reuse the verified namespace of the NDS team already publishing under `ndsev` (tentatively `io.github.ndsev`). See [Appendix B](#appendix-b--publishing-prerequisites--account-handoff). |
| **C++ packaging** | **Conan Center + vcpkg**, plus CMake `FetchContent` (unchanged). |
| **Docs** | Combined **GitHub Pages** site (Sphinx/Doxygen/Javadoc) built in CI. Must not break the parent-SDK / NDS.Live-portal docs contract (`__all__` + docstrings). |
| **Release flow** | Publish **pre-releases from `main`**, **releases from `v*` tags**. |
| **LICENSE layout** | Canonical text at root **+ per-language copies** (`python/`, `cpp/`, `java/`), kept in sync by a CI check. |

---

## Open questions (need a maintainer decision before/while executing)

1. ~~**SPDX label for the MIT-no-patent variant.**~~ ✅ *Resolved:* label as plain
   `MIT` in classifiers and `SPDX-License-Identifier: MIT` headers; the LICENSE
   file (Appendix A) carries the patent carve-out. **Confirm with legal:** the
   copyright line has **no year** (see Appendix A note) — intended or add one?
2. **Public name & coordinates.** ✅ *Resolved:* public name + GitHub repo are
   **`ndslive-math`** (`github.com/ndsev/ndslive-math`); Python keeps dist
   `ndslive-math` / import `ndslive.math`. **C++ stays `ndsmath`** (target,
   `<ndsmath/...>` headers, `namespace ndsmath`) — *do not rename*, downstream
   tools depend on it. **Java:** built with **Gradle**, artifactId
   **`ndslive-math`**; Maven **groupId** to be confirmed with the NDS team that
   owns `ndsev` publishing (tentatively `io.github.ndsev`).
3. ~~**Coverage target.**~~ ✅ *Resolved:* gate at ≥95% line + branch in CI
   (see Decisions).
4. ~~**C++ distribution channels.**~~ ✅ *Resolved:* submit to **Conan Center +
   vcpkg**; keep CMake `FetchContent` working regardless.
5. ~~**Docs hosting.**~~ ✅ *Resolved:* combined **GitHub Pages** site built in CI.
   ⚠️ No docs build exists *in this repo* — API docs are generated by the **parent
   SDK** (its `devportal.yaml` references `ndslive.math` with `mode: curated`,
   driven by `__all__`). GitHub Pages is additive, but we must **preserve the
   `__all__` + docstring contract** so the SDK/portal build keeps working
   (see Phase 4 and `api_docs_review.md`).
6. ~~**Registry account ownership.**~~ ✅ *Resolved:* **public PyPI project** and
   **Codecov** already exist (wire CI to them). **Maven Central + GPG are owned
   by another NDS team** that already publishes under `ndsev` — obtain namespace
   + tokens + signing key from them. See
   [Appendix B](#appendix-b--publishing-prerequisites--account-handoff).
7. ~~**`api_docs_review.md` disposition.**~~ ✅ *Resolved:* **remove** before
   publish (the curated-API rationale lives on via `__all__` + docstrings).
8. ~~**CI publish cadence.**~~ ✅ *Resolved:* **tags + `main` pre-releases** —
   releases on `vX.Y.Z` tags; pre-release/dev builds from `main` (TestPyPI,
   Maven snapshots, etc.).
9. ~~**LICENSE file layout.**~~ ✅ *Resolved:* **root + per-language copies**
   (one per language dir), kept in sync by a CI check; each artifact bundles
   its own.
10. **Go module layout.** Subdirectory module (`go/`, tags `go/vX.Y.Z`) vs a
    separate `ndslive-math-go` repo (plain `vX.Y.Z` tags). Affects the unified
    tag scheme — see Appendix C.

---

## Phase 0 — Going-public blockers (do first; mostly one-way doors)

These must land before the repo is flipped to public.

- [ ] **License migration.** Replace the current proprietary `LICENSE` files with
      the MIT-no-patent license, and update every reference in lockstep (see
      [checklist](#licensing-lockstep-checklist) below). The current license
      *explicitly forbids* open-source use, so this is a reversal, not an addition.
- [ ] **Remove Artifactory deploy / fix CI trust model.** `ci.yml` currently runs
      `build-and-deploy-snapshot` **on every PR** with `NDS_ARTIFACTORY_*`
      secrets — which breaks for fork PRs (GitHub withholds secrets) and is the
      wrong trust model for a public repo. **Delete the Artifactory deployment
      entirely** (and the `.github/actions/python-build-deploy` action if it is
      Artifactory-specific). Replace with: test on all PRs; publish to the public
      registries (Phase 3) only on `main` (pre-release) and `v*` tags (release).
      Audit that no secret is reachable from a fork-triggered workflow.
- [ ] **Community health files:**
  - [ ] `README` rework (badges, domain primer, per-language quickstart, public
        install instructions) — see Phase 4.
  - [ ] `CONTRIBUTING.md` — explains the **issues-only** policy clearly so
        outsiders don't waste effort on PRs; documents build/test and the
        CHANGELOG-on-PR rule for internal devs.
  - [ ] `CODE_OF_CONDUCT.md` (Contributor Covenant) — still relevant for issue
        interactions.
  - [ ] `SECURITY.md` — vulnerability reporting channel + supported versions.
  - [ ] `.github/ISSUE_TEMPLATE/` — bug report + feature request (issues are the
        contribution channel, so make them good).
  - [ ] `CODEOWNERS`.
  - [ ] *(Optional)* `GOVERNANCE.md` / `MAINTAINERS.md`.
- [ ] **Replace private install instructions.** README points at
      `--index-url=https://pip.nds.live`; switch to public PyPI.
- [ ] **Audit for internal leakage before publish.** **Remove
      `api_docs_review.md`** (references internal-only repos `zs-yaml`,
      `ndslive-yaml` and the SDK's `devportal.yaml`; its rationale survives via
      `__all__` + docstrings). Grep the tree for other internal
      URLs/paths/credentials.
- [ ] **Add Python 3.14** to CI matrix + classifiers.
- [ ] **Fix wrong repo URLs.** `pyproject.toml [project.urls]` (`Homepage`,
      `Repository`) point at `github.com/ndsev/ndsmath` → correct to
      `github.com/ndsev/ndslive-math`. Sweep for other stale `ndsmath` repo URLs
      (README install/FetchContent examples, etc.). **Note:** only the
      *repository URL* changes (`ndsmath.git` → `ndslive-math.git`); the C++
      target, `<ndsmath/...>` include path, and `namespace ndsmath` stay as-is —
      downstream consumers depend on them.

## Phase 1 — Test infrastructure & coverage

- [ ] **Language-neutral parity vectors.** Author a shared `test-vectors/`
      dataset (JSON: input → expected) for WGS84↔NDS, Morton encode/decode, and
      tile-ID round-trips. All three language suites load it. This is the single
      best guard against cross-language drift — the changelog already shows parity
      bugs (floor-vs-truncate, v0.5.1; MSVC-only breakage). Worth doing *before*
      Java so the new impl is validated against the same vectors from day one.
- [ ] **Coverage tooling:** Python `coverage.py`/`pytest-cov`, C++ `lcov`/`gcov`
      (or `llvm-cov`), Java JaCoCo.
- [ ] **Codecov** integration + badge; upload from all three jobs; gate at the
      agreed threshold (see open question 3).
- [ ] **Multi-OS C++ matrix** — add Windows (MSVC) + macOS; CI is Linux-only today
      and MSVC has bitten us before.
- [ ] **Lint/format/static analysis:** ruff + mypy (Python), clang-format +
      clang-tidy (C++), spotless/checkstyle (Java); `.pre-commit-config.yaml`;
      enable CodeQL + Dependabot (free for public repos).

## Phase 2 — New language implementations

Each mirrors the C++/Python API (`Wgs84`, `PackedTileId`, `MortonCode`,
`NdsBoundingBox`, bbox/tile helpers), is validated against the Phase 1 parity
vectors, and wires into CI (build + test + coverage → Codecov).

- [ ] **Java** — `java/` **Gradle** module; Maven coords
      `io.github.ndsev:ndslive-math` (groupId TBC, Appendix B). JaCoCo coverage.
- [ ] **JavaScript / TypeScript** — `js/` package written in **TypeScript**,
      shipping compiled JS + `.d.ts` types (covers the previously-"planned" TS
      item). Vitest/Jest + c8 coverage.
- [ ] **Go** — Go module (layout per open question 10); `go test -cover`.
- [ ] **Rust** — `rust/` crate; `cargo test` + coverage (cargo-llvm-cov).

## Phase 3 — Public distribution

- [ ] **PyPI** via **Trusted Publishing (OIDC)** — no long-lived tokens. Dry-run
      on Test PyPI first.
- [ ] **Maven Central** via Sonatype Central Portal + GPG signing; complete POM
      metadata (SCM, license, developers).
- [ ] **C++** — submit a Conan Center recipe **and** a vcpkg port; keep
      `FetchContent` documented and working.
- [ ] **npm (JavaScript)** — publish a scoped package (org TBC) with
      `--access public`; prefer **OIDC provenance** from GitHub Actions over a
      stored `NPM_TOKEN`. See Appendix C.
- [ ] **crates.io (Rust)** — **reserve the `ndslive-math` crate name early**
      (global flat namespace); publish via `cargo publish` (OIDC trusted
      publishing or `CARGO_REGISTRY_TOKEN`). See Appendix C.
- [ ] **Go modules** — no registry/account; release = tag + push. Mind the
      sub-module tag-prefix caveat (open question 10 / Appendix C).
- [ ] **Release automation** — GitHub Releases generated from `CHANGELOG.md` on
      `v*` tags, with artifacts attached. **Pre-release/dev builds publish from
      `main`** (TestPyPI; Maven snapshots repo; Conan test channel); **releases
      from `v*` tags**. Document the SemVer policy and how the unified `v*` tag
      maps onto each ecosystem.

## Phase 4 — Documentation polish

- [ ] README **badges**: CI, Codecov, PyPI, Maven Central, license, Python
      versions.
- [ ] **Domain primer** — explain NDS.Live, tile IDs, Morton/Z-order curves, and
      WGS84↔NDS for readers new to the space (the README currently assumes
      familiarity with "Packed Tile ID").
- [ ] **Hosted API docs** — combined **GitHub Pages** site aggregating Sphinx
      (Python) + Doxygen (C++) + Javadoc (Java), deployed from CI; link from README.
  - [ ] ⚠️ **Preserve the parent-SDK docs contract.** This repo has *no* docs
        build of its own — the **parent SDK** renders `ndslive.math` via its
        `devportal.yaml` (`apidoc.packages`, `mode: curated`), relying on the
        package's `__all__` and docstrings (see `api_docs_review.md`). Keep
        `__all__` curated and docstrings intact; the GitHub Pages Sphinx build
        should reuse the same `mode: curated` / `__all__`-respecting setup so both
        renderings agree. Don't rename/move modules in ways that break the SDK's
        reference to `ndslive.math`.
- [ ] `examples/` per language.
- [ ] SPDX headers in all source files (open question 1).

---

## Licensing lockstep checklist

When the proprietary license is replaced, **all** of these must change together
or the repo will ship contradictory licensing signals:

- [x] `LICENSE` (root) created from [Appendix A](#appendix-a--canonical-license-text-from-legal);
      **per-language copies** done for `python/`, `cpp/` (the rest added with
      their modules). ⬜ TODO: CI check that all copies match root byte-for-byte.
- [ ] `python/pyproject.toml` — classifier `License :: Other/Proprietary License`
      → MIT; update the `license` field per open question 1.
- [x] `cpp/LICENSE`, `python/LICENSE` — proprietary text replaced with the
      MIT-no-patent text from Appendix A.
- [ ] SPDX headers added to every source file under `cpp/` and
      `python/src/ndslive/math/`.
- [ ] README files (root, `cpp/`, `python/`) — any "proprietary / NDS-members-only"
      wording removed; public install instructions.
- [ ] Confirm build/test deps' licenses are compatible & attributed: **GLM**
      (header, MIT/Happy Bunny), **Catch2** (BSL-1.0). Add a `NOTICE`/THIRD-PARTY
      file if desired (not strictly required for MIT).

---

## Out of scope / explicitly deferred

- Accepting external code contributions (issues-only by decision; revisit later
  if the policy changes — that's when DCO/CLA tooling would be added).

*(TypeScript is now in scope — folded into the JavaScript/TS implementation in
Phase 2. Six languages total: C++, Python, Java, JavaScript/TS, Go, Rust.)*

---

## Appendix A — Canonical LICENSE text (from legal)

This is the exact, authoritative license text supplied by NDS legal. It is the
source of truth for the root `LICENSE` file and any per-language copies. Do not
reword. Labeled as `MIT` for tooling (see Decisions / open question 1).

```text
Copyright (c) Navigation Data Standard (NDS) e.V.
The following permission does NOT include any patent rights. It is the user’s responsibility to verify whether any patents exist and are required for the exercise of the copyright permission.
Permission under copyright is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software") to deal in the Software without restriction, including, without limitation, the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice including the patent notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

**Notes / things to confirm with legal before baking into every file:**
- **No copyright year.** Standard MIT has `Copyright (c) <year> <holder>`; this
  omits it. Common and acceptable (avoids annual churn), but confirm it's
  deliberate rather than an oversight.
- **Patent notice must be retained.** The permission clause requires "this
  permission notice **including the patent notice**" in all copies — so the
  full block (including the patent sentence) must travel with redistributions.
  This is fine but reinforces using the complete notice, not an abbreviated
  `SPDX-License-Identifier: MIT` header *alone*; pair the SPDX header with the
  full LICENSE file in each distributable artifact (sdist/wheel, jar, Conan pkg).
- Otherwise this is MIT (Expat) verbatim apart from the patent carve-out.

---

## Appendix B — Publishing prerequisites & account handoff

What exists today, what must be obtained, and from whom. I can wire all the CI
config, but cannot create accounts or hold keys — these are maintainer actions.

| Channel | Status | Action / owner |
|---|---|---|
| **PyPI (Python)** | ✅ Public `ndslive-math` project exists | Confirm the repo has maintainer/publish access; set up **Trusted Publishing (OIDC)** from the GitHub repo (preferred over a long-lived token). Pre-releases → **TestPyPI**. |
| **Codecov** | ✅ Exists | Confirm the repo is added; public repos usually upload tokenless, otherwise set `CODECOV_TOKEN`. Add the badge to README. |
| **Maven Central (Java)** | ⚠️ Owned by another NDS team (already publishes under `ndsev`) | Obtain from them: (1) the **verified namespace / groupId** we publish under — *reuse theirs* rather than registering a new one (confirms or overrides the tentative `io.github.ndsev`); (2) a **Central Portal publishing token**; (3) the **GPG signing key** (or have our own key trusted). Confirm artifactId `ndslive-math` is free under that namespace and coordinate versioning so we don't collide. |
| **GPG signing** | ⚠️ From the Maven team | Required by Central. Use the team's key, or generate one and publish it to keyservers; store the private key + passphrase as repo secrets for CI signing. |
| **GitHub Pages (docs)** | n/a — no external account | Enable in repo Settings → Pages with **GitHub Actions** as the source; deploy from the docs workflow. |
| **Conan Center / vcpkg (C++)** | n/a — PR-based, no stored creds | Submission is via PRs to `conan-center-index` / `vcpkg`; no credentials live in this repo. |

**Repo secrets / variables to provision once the above are confirmed:**
- PyPI: none if OIDC Trusted Publishing is used; otherwise `PYPI_API_TOKEN` +
  `TEST_PYPI_API_TOKEN`.
- Maven: Central Portal token (user/password), `GPG_PRIVATE_KEY`,
  `GPG_PASSPHRASE`.
- Codecov: `CODECOV_TOKEN` (only if not tokenless).
- **Delete** all `NDS_ARTIFACTORY_*` secrets once the Artifactory deploy is
  removed (Phase 0).

---

## Appendix C — Publishing guideline for JavaScript, Go, and Rust

These three ecosystems have **nothing set up yet**. Below is exactly what you
need to do (accounts, names, tokens) for each. I can write all the build configs
and CI workflows; the account/token/name-reservation steps are yours.

### JavaScript / TypeScript → npm

1. **Decide the package name.** Recommend a **scoped** name under an npm org you
   control, e.g. `@ndsev/ndslive-math` (or unscoped `ndslive-math` if free).
   Scoped packages need the org created first and `--access public` to publish
   openly.
2. **Account setup (manual):**
   - Create/secure an **npm account**; enable **2FA** (required for publishing).
   - Create the npm **organization** (the `@ndsev` scope) and add maintainers.
3. **CI publishing:** GitHub Actions, on `v*` tags. Prefer **npm Trusted
   Publishing + provenance via OIDC** (no stored secret, adds a verified
   supply-chain badge) over an **automation token** (`NPM_TOKEN` secret).
   Publish with `npm publish --provenance --access public`.
4. **`package.json` essentials:** `name`, `version`, `license: "MIT"`,
   `repository`, `description`, `types`, `exports`, `files`, `engines`. Keep
   `version` aligned with the unified `v*` tag.

### Rust → crates.io

1. **Reserve the crate name NOW.** crates.io is a **single global flat
   namespace** (no scoping) — names are first-come and effectively permanent.
   Publish a `0.0.0` placeholder of `ndslive-math` to claim it before someone
   else does.
2. **Account setup (manual):**
   - Log in to **crates.io** with GitHub and accept the terms.
   - Either create an **API token** (store as `CARGO_REGISTRY_TOKEN` secret), or
     set up crates.io **Trusted Publishing (OIDC)** from GitHub Actions
     (preferred; no stored token).
3. **CI publishing:** `cargo publish` on `v*` tags.
4. **`Cargo.toml` essentials:** `name`, `version`, `license = "MIT"`,
   `description`, `repository`, `readme`, `keywords`, `categories`
   (crates.io **requires** `license`/`license-file` and `description`).
5. **Caveat:** every published version is **immutable** — you can `yank` but not
   delete. Get the first real release right.

### Go → Go modules (no central registry, no account)

Go does **not** have a registry you publish to — distribution is straight from
the git repo + version tags, and `pkg.go.dev` indexes on demand. So there is
**no account, token, or upload step**. But the layout decision matters:

1. **Module path = import path.** Two options (open question 10):
   - **Subdirectory module** `go/` → `module github.com/ndsev/ndslive-math/go`;
     users `go get github.com/ndsev/ndslive-math/go`.
     ⚠️ **Sub-module version tags must be prefixed:** `go/vX.Y.Z`, *not* plain
     `vX.Y.Z`. This collides with the unified tag scheme — each release would
     need **both** `vX.Y.Z` (for the others) and `go/vX.Y.Z` (for Go).
   - **Separate repo** `github.com/ndsev/ndslive-math-go` → plain `vX.Y.Z`
     tags, cleaner, but a second repo to maintain.
2. **Major versions:** v2+ require a `/vN` suffix in the module path
   (`.../go/v2`). Plan to stay v0/v1 initially.
3. **`go.mod` essentials:** the module path + a `go` version directive; the
   `LICENSE` file in the module root conveys licensing.
4. **Trigger indexing (optional):** after pushing a tag,
   `GOPROXY=https://proxy.golang.org go list -m <module>@vX.Y.Z` (or just open
   the `pkg.go.dev/<module>` page) warms the proxy and renders the docs.

### Summary — what to set up before first release

| Ecosystem | Account/registry | Name to reserve | CI auth |
|---|---|---|---|
| npm | npm account + `@ndsev` org, 2FA | `@ndsev/ndslive-math` | OIDC provenance (pref.) or `NPM_TOKEN` |
| crates.io | crates.io login (GitHub) | `ndslive-math` (**reserve early**) | OIDC (pref.) or `CARGO_REGISTRY_TOKEN` |
| Go | none | n/a (module path only) | none — tag + push |

