#!/usr/bin/env python3
"""Builds a LayeredFS mod raising the engine's graphics quality settings, from your own game files.

The engine reads its scene graphics configuration (gsys.bgmsconf, an AAMP parameter file) from
/Common/Gfx/TurboAppPackage.Nin_NX_NVN.release.sarc. This script rewrites a copy of that archive:
  - shadow maps:       depth_shadow_tex_width/height x2 (race 1024 -> 2048, menus 1536 -> 3072)
  - ambient occlusion: ssao_width_scale x2, capped at 1.0 (half -> full resolution)
  - reflections:       cube_map_max_tex_width x2, capped at 256 (128 -> 256)

No game data ships with this script: it only edits the archive you dumped from your own copy.

Usage:
  python make_mod.py <TurboAppPackage.Nin_NX_NVN.release.sarc | dumped romfs folder> <output folder>
                     [--shadows hd|original] [--ssao hd|original] [--reflections hd|original]
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path

ARCHIVE = "Common/Gfx/TurboAppPackage.Nin_NX_NVN.release.sarc"
CONFIG = "gsys.bgmsconf"

INT, FLOAT = 2, 1  # AAMP parameter types


def crc32(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def patch_aamp(data, changes):
    """AAMP v2, little endian. Values may be shared between equal parameters (1024 is also used by
    unrelated counts), so each changed parameter gets its own value appended at the end of the file.
    Returns (new file, number of changed parameters)."""
    a = bytearray(data)
    if a[:4] != b"AAMP" or u32(a, 4) != 2:
        raise ValueError(f"{CONFIG} is not an AAMP v2 file")
    by_crc = {crc32(name): (name, kind, factor, cap) for name, kind, factor, cap in changes}
    done = []

    def param(p):
        crc, word = u32(a, p), u32(a, p + 4)
        kind, value_at = word >> 24, p + (word & 0xFFFFFF) * 4
        if crc not in by_crc or by_crc[crc][1] != kind or value_at + 4 > len(a):
            return
        name, _, factor, cap = by_crc[crc]
        if kind == INT:
            x = struct.unpack_from("<i", a, value_at)[0]
            if x <= 0 or x >= cap:
                return
            new = struct.pack("<i", min(int(x * factor), int(cap)))
        else:
            x = struct.unpack_from("<f", a, value_at)[0]
            if not x > 0 or x >= cap:
                return
            new = struct.pack("<f", min(x * factor, cap))
        while len(a) % 4:
            a.append(0)
        new_at = len(a)
        a.extend(new)
        struct.pack_into("<I", a, p + 4, ((new_at - p) // 4) | (kind << 24))
        done.append(name)

    lists = [0x30 + u32(a, 0x14)]
    i = 0
    while i < len(lists) and i < 4096:
        l = lists[i]
        i += 1
        sub_lists, objects = l + u16(a, l + 4) * 4, l + u16(a, l + 8) * 4
        lists += [sub_lists + 12 * k for k in range(u16(a, l + 6))]
        for k in range(u16(a, l + 10)):
            o = objects + 8 * k
            params = o + u16(a, o + 4) * 4
            for j in range(u16(a, o + 6)):
                param(params + 8 * j)
    struct.pack_into("<I", a, 0x0C, len(a))  # file size
    return bytes(a), len(done)


def patch_sarc(data, name, transform):
    """SARC, little endian: the transformed file is moved to the end of the archive."""
    s = bytearray(data)
    if s[:4] != b"SARC" or u16(s, 6) != 0xFEFF:
        raise ValueError("not a little endian SARC archive")
    sfat, data_start = u16(s, 4), u32(s, 0x0C)
    count = u16(s, sfat + 6)
    nodes = sfat + 12
    names = nodes + 16 * count + 8
    for i in range(count):
        e = nodes + 16 * i
        attr = u32(s, e + 4)
        if not attr & 0x01000000:
            continue
        n = names + (attr & 0xFFFF) * 4
        if s[n:s.index(0, n)].decode() != name:
            continue
        begin, end = u32(s, e + 8), u32(s, e + 12)
        new, changed = transform(bytes(s[data_start + begin:data_start + end]))
        pos = (len(s) + 0xFF) & ~0xFF
        s += bytes(pos - len(s)) + new
        struct.pack_into("<II", s, e + 8, pos - data_start, pos - data_start + len(new))
        struct.pack_into("<I", s, 8, len(s))
        return bytes(s), changed
    raise ValueError(f"{name} not found in the archive")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input", type=Path, help=f"{ARCHIVE.split('/')[-1]}, or a dumped romfs folder")
    ap.add_argument("output", type=Path, help="mod folder to create (a romfs/ folder is written in it)")
    ap.add_argument("--shadows", choices=["hd", "original"], default="hd")
    ap.add_argument("--ssao", choices=["hd", "original"], default="hd")
    ap.add_argument("--reflections", choices=["hd", "original"], default="hd")
    args = ap.parse_args()

    source = args.input / ARCHIVE if args.input.is_dir() else args.input
    changes = []
    if args.shadows == "hd":  # 4096 runs out of the game's graphics heap when a race loads
        changes += [("depth_shadow_tex_width", INT, 2.0, 4096), ("depth_shadow_tex_height", INT, 2.0, 4096)]
    if args.ssao == "hd":
        changes.append(("ssao_width_scale", FLOAT, 2.0, 1.0))
    if args.reflections == "hd":
        changes.append(("cube_map_max_tex_width", INT, 2.0, 256))
    if not changes:
        sys.exit("nothing to change")

    archive, changed = patch_sarc(source.read_bytes(), CONFIG, lambda f: patch_aamp(f, changes))
    if not changed:
        sys.exit("no parameter changed: unexpected game files")
    target = args.output / "romfs" / ARCHIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(archive)
    print(f"{changed} parameter(s) changed -> {target}")


if __name__ == "__main__":
    main()
