# Contributing to ndslive-math

Thanks for your interest in `ndslive-math`! Please read this before opening an
issue or pull request.

## How we accept contributions

**We currently do not accept external pull requests.** `ndslive-math` is
developed and maintained by the Navigation Data Standard (NDS) e.V. team, and
changes are implemented internally.

What you *can* do, and what we genuinely value:

- **Report bugs** — open an issue with a minimal reproduction (inputs, expected
  vs. actual output, language, and version).
- **Request features** — open an issue describing the use case.
- **Ask questions** about behaviour or the NDS coordinate/tiling concepts.

We triage issues and implement accepted changes ourselves. If you open a PR it
may be closed with a pointer to this policy — please don't take it personally;
it's about how this particular project is governed, not the quality of your work.

## Reporting a good issue

Use the issue templates. A useful bug report includes:

- The **language** (C++, Python, Java, JavaScript/TypeScript, Go, or Rust) and
  the **version** you're using.
- The exact inputs and the **expected vs. actual** result. Because this library
  has multiple implementations that must agree, "Python gives X but Go gives Y"
  is an especially valuable report.
- For security-sensitive reports, **do not open a public issue** — see
  [SECURITY.md](SECURITY.md).

## Project layout

This is a multi-language monorepo. Each language lives in its own directory and
implements the same API: `Wgs84`, `MortonCode`, `PackedTileId`, `NdsBoundingBox`
and the tile/bounding-box helper functions.

| Dir | Language | Build / test |
|---|---|---|
| `python/` | Python | `python -m unittest discover -s python/tests` |
| `cpp/` | C++ | `cmake -S cpp -B build && cmake --build build && ctest --test-dir build` |
| `java/` | Java | `cd java && ./gradlew test` |
| `js/` | JavaScript/TypeScript | `cd js && npm install && npm test` |
| `go/` | Go | `cd go && go test ./...` |
| `rust/` | Rust | `cd rust && cargo test` |

## Cross-language parity (for maintainers)

All implementations are validated against a shared set of golden vectors in
[`test-vectors/parity_vectors.json`](test-vectors/parity_vectors.json), generated
from the Python reference implementation:

```bash
PYTHONPATH=python/src python3 test-vectors/generate_vectors.py
```

If you change any algorithm, **regenerate the vectors and run every language's
test suite**. Integer results must match exactly; floating-point results must
match within the tolerance recorded in the JSON (`_meta.float_tolerance`).

## Changelog

Every change must be recorded in [`CHANGELOG.md`](CHANGELOG.md) under the
appropriate `### <Language>` subsection ([Keep a Changelog](https://keepachangelog.com/)
format). CI enforces that PRs touch `CHANGELOG.md` and that entries on `main`
carry a release date. Prefix breaking changes with `**BREAKING:**`.

## Coding conventions

Match the surrounding code in each language. Public API names mirror the Python
reference, adapted to each language's idioms (e.g. `to_nds_coordinates` in
Python/Rust, `toNdsCoordinates` in Java/JS/Go). Every source file carries an
`SPDX-License-Identifier: MIT` header.
