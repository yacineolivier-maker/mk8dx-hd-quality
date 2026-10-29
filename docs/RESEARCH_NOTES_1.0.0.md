# Research notes — Mario Kart 8 Deluxe 1.0.0 (AArch32)

Findings from a personal PC port of version **1.0.0** (the only AArch32 build; 2.x and later are AArch64, so these
offsets do **not** apply to them as-is). Offsets are relative to the start of the `main` module as loaded
(text at +0). No game code or data is included here; only offsets and observed behaviour.

Status legend: **verified** = observed in a running game; **untested** = derived from static analysis only.

## Display size table (ultra-wide) — verified

- `main+0xBD2600` (read-only data): table `{1920x1080 (docked), 1280x720 (handheld)}` read through the GOT
  (`main+0xCD1434` / `+0xCD1438`) by the engine's graphics init (`main+0x2F7444`) to size the frame buffers.
- Widening only the docked entry gives a stretched image with the same field of view.
- The handheld entry 1280x720 doubles as the **virtual screen** used by the camera and UI: widening it too
  (e.g. 1680x720 for 21:9) gives a real wider field of view at full speed. The UI then stays stretched.

## Virtual screen constants (1280.0f literals) — untested

Literal pools read by code at run time (value `0x44A00000`):

| Literal | Used by |
|---|---|
| `main+0x6115A4` | 3D → 2D projection of each view (`main+0x611524`) |
| `main+0x61E680` | fraction of the screen covered by a view → its buffer sizes, including the shadow map (`main+0x61E2F8`, `+0x61E56C`) |
| `main+0x71D484` | virtual screen → normalised coordinates (`main+0x71D3C8`) |

Menu page slide offsets ±1280.0f (layout coordinates, function at `main+0x7F17B8`): `+0x7F17F4`, `+0x7F17F8`,
`+0x7F1964`, `+0x7F1968`. Touch constants (±640 / ±360) were left alone.

## Centred 16:9 UI on ultra-wide — untested

`nn::ui2d::Layout::Build` (`main+0x4C46B4`) reads the layout size from the BFLYT `lyt1` section into
`this+0x14` / `this+0x18` (1280x720; 640x720 or 640x360 per view in split screen). Scaling the width by
`docked width / 1920` after the call keeps the UI at 16:9 in the centre. Rewriting the BFLYT files instead is
impractical: they sit in Yaz0 archives that grow from 21 MB to 67 MB once decompressed and are loaded into the
game heap.

## Shadow maps in split screen — verified by analysis, 2-player tested

Each view gets a shadow map of `depth_shadow_tex` × max(width / 1280, height / 720), floor 32 (`main+0x61E568`).
Four views at 1024² cost the same as one 2048² map; the worst case is 2-player split screen (two full maps).
4096² shadows (`ultra`) exhaust the game's graphics heap when a course loads (null call), so 2048² is the
practical ceiling.
