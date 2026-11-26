#!/usr/bin/env python3
"""Independent structural validator for the deployed broadsheet PNG.

Usage:  python3 verify_png.py [path]      (default: ./entry.png)

Checks, in order:
  1. PNG signature and chunk walk — every chunk's CRC32 is verified, so a
     single flipped byte anywhere in the file is caught, not just the header.
  2. Exactly one IHDR, width == height == 1024, bit depth 8, colour type 6
     (truecolour+alpha) or 2 (truecolour).
  3. IDAT stream inflates cleanly and yields exactly
     height * (1 + width * channels) bytes — i.e. every scanline is present.
  4. Every scanline's leading filter byte is in 0..4.
  5. IEND is present and is the last chunk; no trailing garbage.
  6. File size <= 1,048,576 bytes.
  7. Prints the SHA-256 of the file.

Standard library only, so it runs with or without the render venv.
Exit code 0 on success, 1 with a one-line reason on failure.
"""

import hashlib
import struct
import sys
import zlib

MAX_BYTES = 1_048_576
EXPECT_SIDE = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(msg):
    print("verify FAILED: " + msg, file=sys.stderr)
    sys.exit(1)


def validate(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        fail("cannot read %r: %s" % (path, e))

    size = len(data)
    if size > MAX_BYTES:
        fail("%d bytes exceeds the 1,048,576 byte ceiling" % size)
    if not data.startswith(PNG_MAGIC):
        fail("missing PNG signature")

    pos = 8
    chunks = []
    ihdr = None
    idat = []
    seen_iend = False
    while pos < size:
        if pos + 8 > size:
            fail("file ends mid-chunk header at offset %d" % pos)
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        body_start = pos + 8
        body_end = body_start + length
        crc_end = body_end + 4
        if crc_end > size:
            fail("chunk %r at offset %d runs past end of file"
                 % (ctype, pos))
        body = data[body_start:body_end]
        (stored_crc,) = struct.unpack(">I", data[body_end:crc_end])
        actual_crc = zlib.crc32(ctype + body) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            fail("CRC mismatch in chunk %r at offset %d (stored %08x, "
                 "computed %08x)" % (ctype, pos, stored_crc, actual_crc))
        chunks.append(ctype)
        if ctype == b"IHDR":
            if ihdr is not None:
                fail("more than one IHDR chunk")
            if length != 13:
                fail("IHDR length is %d, expected 13" % length)
            ihdr = body
        elif ctype == b"IDAT":
            idat.append(body)
        elif ctype == b"IEND":
            seen_iend = True
            pos = crc_end
            break
        pos = crc_end

    if ihdr is None:
        fail("no IHDR chunk")
    if not seen_iend:
        fail("no IEND chunk")
    if pos != size:
        fail("%d trailing bytes after IEND" % (size - pos))

    w, h, depth, ctype_, comp, filt, interlace = struct.unpack(
        ">IIBBBBB", ihdr)
    if (w, h) != (EXPECT_SIDE, EXPECT_SIDE):
        fail("image is %dx%d, expected %dx%d"
             % (w, h, EXPECT_SIDE, EXPECT_SIDE))
    if depth != 8:
        fail("bit depth is %d, expected 8" % depth)
    if ctype_ not in (2, 6):
        fail("colour type is %d, expected 2 or 6" % ctype_)
    if comp != 0:
        fail("compression method is %d, expected 0" % comp)
    if filt != 0:
        fail("filter method is %d, expected 0" % filt)
    if interlace != 0:
        fail("interlaced PNGs are not accepted here (interlace=%d)"
             % interlace)
    if not idat:
        fail("no IDAT chunk")

    channels = 3 if ctype_ == 2 else 4

    # Inflate in a streaming fashion so huge or corrupted streams cannot
    # balloon memory before we notice.
    row_bytes = 1 + w * channels
    expect_raw = h * row_bytes
    dec = zlib.decompressobj()
    raw = bytearray()
    try:
        for piece in idat:
            raw += dec.decompress(piece, expect_raw + 1 - len(raw))
            if len(raw) > expect_raw:
                fail("IDAT inflates to more than the %d bytes the header "
                     "allows" % expect_raw)
        raw += dec.flush()
    except zlib.error as e:
        fail("IDAT stream does not inflate: %s" % e)
    if len(raw) != expect_raw:
        fail("IDAT inflates to %d bytes, expected exactly %d for %dx%d"
             % (len(raw), expect_raw, w, h))

    for y in range(h):
        fbyte = raw[y * row_bytes]
        if fbyte > 4:
            fail("scanline %d has illegal filter byte %d" % (y, fbyte))

    digest = hashlib.sha256(data).hexdigest()
    print("verify OK: %s" % path)
    print("  %dx%d, %d bytes, %d chunks, colour type %d, bit depth 8"
          % (w, h, size, len(chunks), ctype_))
    print("  sha256 %s" % digest)
    return digest


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    validate(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
