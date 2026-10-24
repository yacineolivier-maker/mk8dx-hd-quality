# MK8DX HD quality

A small script that builds a LayeredFS mod raising three graphics settings of the game's engine:

| Setting | Original | With the mod |
|---|---|---|
| Shadow maps (race / menus) | 1024 / 1536 | 2048 / 3072 |
| Ambient occlusion (SSAO) | half resolution | full resolution |
| Reflection cubemaps | 128 | 256 |

The settings live in the engine's scene configuration (`gsys.bgmsconf`, an AAMP file inside
`/Common/Gfx/TurboAppPackage.Nin_NX_NVN.release.sarc`). The script edits a copy of that archive
taken from **your own dump**; no game file is distributed here.

Shadow maps at 4096 are not offered: the game's graphics heap runs out when a race loads.

## Usage

1. Dump the RomFS of your game (Eden / Ryujinx: right-click the game, *Dump RomFS*), including the
   installed update.
2. Run (Python 3.8+, no dependencies):

   ```
   python make_mod.py <dumped romfs folder> <output folder>
   ```

   Options: `--shadows original`, `--ssao original`, `--reflections original` keep a setting as it is.
3. Copy the output folder into your mods folder:
   - Eden / Ryujinx: `load/0100152000022000/HD quality/` (the folder must contain `romfs/`).
   - Atmosphère: copy `romfs/` to `atmosphere/contents/0100152000022000/`.

## Status

- Tested on version 1.0.0 (in a PC port of the game): races and 2-player split screen run without
  memory errors. In 4-player split screen each view uses a quarter-size shadow map, so the total
  stays that of a single full map.
- Not yet tested on 3.0.x nor on console hardware (higher GPU cost: expect lower frame rates in
  split screen on the Switch).

## Notes for modders

- The parameters edited are `depth_shadow_tex_width` / `depth_shadow_tex_height`, `ssao_width_scale` and
  `cube_map_max_tex_width`, in the 8 scene objects of `gsys.bgmsconf` (race, menus, cutscenes...).
- AAMP values are shared between parameters (the same 1024 is also used by unrelated entries such as model
  counts), so the script appends a new value instead of editing the shared one in place.
- In split screen each view gets a shadow map scaled by its share of the 1280x720 virtual screen (floor 32),
  so 2-player split screen is the most demanding case.
- If the files of your version differ, the script stops with "no parameter changed" and writes nothing.

Reports for 3.0.x (works / crashes, docked or handheld) are welcome in the issues.

Written with AI assistance (Claude). Not affiliated with Nintendo.

## License

MIT.
