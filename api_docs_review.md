# API Docs Review — `ndslive.math`

Purpose: classify every public symbol in `ndslive.math` as user-facing, advanced, or
internal so the docs build renders a curated surface. Modeled on
`zs-yaml/api_docs_review.md` and `ndslive-yaml/api_docs_review.md`.

This file is descriptive. The actual curation lives in:
1. `__all__` declarations inside the package (metadata only, no behavior change).
2. The `apidoc.packages` entry for `ndslive.math` in the parent SDK's `devportal.yaml`,
   which uses `mode: curated` so Sphinx respects `__all__` and skips undocumented
   public-named symbols.

---

## Audience model

1. **Python API consumer** — imports `ndslive.math` to convert between WGS84 and
   NDS coordinate space, work with packed tile IDs, encode/decode Morton numbers,
   reason about bounding boxes. Primary docs audience.
2. **Schema-aware consumer** — uses the math types as inputs/outputs of higher-level
   APIs (`ndslive.client`, `ndslive.server`). Same documentation needs as (1).
3. **Contributor** — reads the source. Fine with sparse internal helpers; not the
   docs target.

---

## Philosophy

- The 4 submodules (`tileid`, `morton`, `wgs84`, `bounding_box`) each expose **one
  primary class** plus a couple of free functions. `__init__.py` already re-exports
  the lot. That set is the contract.
- No submodule has anything *unique* worth a separate per-submodule page — every
  user-facing symbol is fully reachable from the top-level `ndslive.math` page.
- Therefore: render only the top-level page, exclude all four submodules from
  autodoc walking. Sphinx still imports the submodules (necessary for the
  re-exports to resolve); they just don't get their own RST page.

---

## Curated public API (top-level `ndslive.math`)

All entries are 🟢 user-facing. They appear in `__init__.py` `__all__`.

| Symbol | Source module | Notes |
|---|---|---|
| `Wgs84` | `wgs84` | WGS84 lon/lat/alt point with conversion + arithmetic |
| `NdsBoundingBox` | `bounding_box` | Bounding box in NDS coordinate space; constructors `from_tile`, `from_wgs84_corners` |
| `PackedTileId` | `tileid` | NDS Packed Tile ID (Morton + level) with neighbour traversal |
| `MortonCode` | `morton` | Morton (Z-order) encoder/decoder for 2D NDS coordinates |
| `get_tile_ids_for_bounding_box` | `tileid` | Free function: enumerate tile IDs covering a bounding box at a given level |
| `bounding_box_from_tile_ids` | `tileid` | Free function: union of tile bounds → bounding box |
| `__version__` | `__init__` | Version constant |

---

## Per-submodule notes (all excluded from doc walking)

### `ndslive.math.wgs84`

`Wgs84` is the only public symbol. Class-level constants
(`EARTH_RADIUS_IN_METERS`, `LON_NDS_DELTA`, `LAT_NDS_DELTA`) appear under the
class itself, not as separate module-level entries. All useful methods
(`to_nds_coordinates`, `from_nds_coordinates`, `degrees_to_meters`,
`nds_distance_to_meters`, `to_degree_minutes_seconds`, `distance_to`,
`bearing_from`, `normalize`, plus arithmetic dunders) live on the class.

### `ndslive.math.tileid`

`PackedTileId` plus the two free functions, all already at top level. Internal
helpers (`_validate`, `_deinterleave_morton`, `_interleave_coords`) are already
underscore-prefixed.

### `ndslive.math.morton`

`MortonCode` only. Methods `from_nds_coordinates`, `to_nds_coordinates`,
`value`, `__str__`. Nothing unique.

### `ndslive.math.bounding_box`

`NdsBoundingBox` only (a `@dataclass`). Methods `intersects`, `contains`,
class-methods `from_tile`, `from_wgs84_corners`. Nothing unique.

---

## Summary: what to render

A single top-level `ndslive.math` page driven by `__all__`. 6 classes / functions
visible at module scope, with class methods documented under each class. No
submodule pages — the toctree under "Submodules" is empty (or hidden).

Estimated visible surface: 6 entries at module scope (down from ~50+ if every
method/dunder were a separate nav node).
