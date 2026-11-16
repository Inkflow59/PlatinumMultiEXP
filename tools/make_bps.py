"""Create and apply BPS patches (byuu's format) for two files of the same size.

Usage: python tools/make_bps.py <original_rom.nds> <patched_rom.nds> <output.bps>
"""
import struct
import sys
import zlib

CHUNK = 4096


def _encode(n: int) -> bytes:
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _decode(data: bytes, pos: int):
    value, shift = 0, 1
    while True:
        x = data[pos]
        pos += 1
        value += (x & 0x7F) * shift
        if x & 0x80:
            return value, pos
        shift <<= 7
        value += shift


def create_bps(source: bytes, target: bytes) -> bytes:
    if len(source) != len(target):
        raise ValueError("create_bps only handles two files of the same size")
    body = bytearray()
    pos, n = 0, len(source)
    run_start = 0  # start of the current identical stretch
    while pos < n:
        end = min(pos + CHUNK, n)
        if source[pos:end] == target[pos:end]:
            pos = end
            continue
        # skip to the first differing byte
        while source[pos] == target[pos]:
            pos += 1
        diff_start = pos
        while pos < n and source[pos] != target[pos]:
            pos += 1
        # absorb small identical gaps (< 4 bytes) to keep the number of actions low
        while pos < n:
            gap = pos
            while gap < n and gap - pos < 4 and source[gap] == target[gap]:
                gap += 1
            if gap < n and gap - pos < 4 and source[gap] != target[gap]:
                while gap < n and source[gap] != target[gap]:
                    gap += 1
                pos = gap
            else:
                break
        if diff_start > run_start:  # SourceRead for the identical stretch before it
            body += _encode(((diff_start - run_start - 1) << 2) | 0)
        body += _encode(((pos - diff_start - 1) << 2) | 1)  # TargetRead
        body += target[diff_start:pos]
        run_start = pos
    if run_start < n:
        body += _encode(((n - run_start - 1) << 2) | 0)
    header = b"BPS1" + _encode(len(source)) + _encode(len(target)) + _encode(0)
    patch = bytes(header + body)
    patch += struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    return patch + struct.pack("<I", zlib.crc32(patch))


def apply_bps(source: bytes, patch: bytes) -> bytes:
    if patch[:4] != b"BPS1":
        raise ValueError("Not a BPS patch")
    if struct.unpack("<I", patch[-4:])[0] != zlib.crc32(patch[:-4]):
        raise ValueError("Corrupt patch (patch CRC mismatch)")
    src_crc, tgt_crc = struct.unpack("<II", patch[-12:-4])
    if zlib.crc32(source) != src_crc:
        raise ValueError("This patch does not match the provided ROM (source CRC mismatch)")
    pos = 4
    _src_size, pos = _decode(patch, pos)
    tgt_size, pos = _decode(patch, pos)
    meta, pos = _decode(patch, pos)
    pos += meta
    out = bytearray()
    end = len(patch) - 12
    while pos < end:
        data, pos = _decode(patch, pos)
        cmd, length = data & 3, (data >> 2) + 1
        if cmd == 0:
            out += source[len(out) : len(out) + length]
        elif cmd == 1:
            out += patch[pos : pos + length]
            pos += length
        else:
            raise ValueError("Unsupported BPS action (SourceCopy/TargetCopy)")
    if len(out) != tgt_size or zlib.crc32(bytes(out)) != tgt_crc:
        raise ValueError("Result does not match the expected CRC")
    return bytes(out)


if __name__ == "__main__":
    original, patched, out_path = sys.argv[1:4]
    with open(original, "rb") as f1, open(patched, "rb") as f2:
        bps = create_bps(f1.read(), f2.read())
    with open(out_path, "wb") as f:
        f.write(bps)
    print(f"BPS patch written: {out_path} ({len(bps)} bytes)")
