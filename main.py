#!/usr/bin/env python3
"""Deploy the bundled broadsheet image to the platform output directory.

Contract (Python 3.13, standard library only):
  * reads the bundled entry.png that sits next to this script
  * validates it is a real PNG of 1024x1024 and no larger than 1 MiB
  * stages a copy inside $MAKEFUN_OUTPUT_DIR, chmods it 0644, then renames
    it atomically to <output>/entry.png
  * validates the deployed bytes too, and exits non-zero with a clear
    message if anything is wrong

Why stage inside the output directory rather than /tmp: os.replace() is only
atomic within one filesystem. A temp file in /tmp renamed into /output can
fail with EXDEV (cross-device link) or, worse, silently degrade to a copy.

Why chmod before the rename: mkstemp() creates files at mode 0600. If we
renamed first and chmodded second, there would be a window in which the
deployed image exists but is unreadable to the web server. We set 0644 on
the staging file, then swap it into place, so the file appears complete and
world-readable in a single atomic step.
"""

import os
import stat
import struct
import sys
import tempfile
import zlib

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
EXPECT_SIDE = 1024
MAX_BYTES = 1_048_576  # 1 MiB

BUNDLED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")


def die(msg):
    print("entry.png deploy FAILED: " + msg, file=sys.stderr)
    sys.exit(1)


def _mkstemp(out_dir):
    """Create the staging file inside out_dir, with a clear error if we can't.

    It has to live in the output directory: os.replace() is only atomic on a
    single filesystem, and a /tmp staging file renamed into /output can fail
    with EXDEV.
    """
    try:
        return tempfile.mkstemp(prefix=".entry.", suffix=".tmp", dir=out_dir)
    except OSError as e:
        die("cannot create a staging file in output directory %r: %s "
            "(is it writable?)" % (out_dir, e))


def check_png_bytes(data, where):
    """Fully validate raw PNG bytes; return the size.

    A header check is not enough. A file truncated mid-stream still carries a
    valid signature and a valid IHDR, so it would sail through a
    magic-plus-dimensions test and get published as a corrupt image. Here we
    walk every chunk and verify its CRC32, require IEND as the final chunk,
    and inflate the IDAT stream to confirm it yields exactly the number of
    scanline bytes the header promises. Anything short of a complete,
    intact file is rejected.
    """
    size = len(data)
    if size > MAX_BYTES:
        die("%s is %d bytes, over the %d byte (1 MiB) ceiling"
            % (where, size, MAX_BYTES))
    if size < 8 or data[:8] != PNG_MAGIC:
        die("%s does not start with the PNG signature (first bytes %r)"
            % (where, data[:8]))

    pos = 8
    ihdr = None
    idat = []
    saw_iend = False
    while pos < size:
        if pos + 8 > size:
            die("%s is truncated: file ends mid-chunk header at offset %d "
                "(this file looks cut off)" % (where, pos))
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        body_start = pos + 8
        body_end = body_start + length
        crc_end = body_end + 4
        if crc_end > size:
            die("%s is truncated: chunk %r at offset %d declares %d bytes "
                "but the file ends early" % (where, ctype, pos, length))
        body = data[body_start:body_end]
        (stored_crc,) = struct.unpack(">I", data[body_end:crc_end])
        if (zlib.crc32(ctype + body) & 0xFFFFFFFF) != stored_crc:
            die("%s is corrupt: CRC mismatch in chunk %r at offset %d"
                % (where, ctype, pos))
        if ctype == b"IHDR":
            if ihdr is not None:
                die("%s has more than one IHDR chunk" % where)
            ihdr = body
        elif ctype == b"IDAT":
            idat.append(body)
        elif ctype == b"IEND":
            saw_iend = True
            pos = crc_end
            break
        pos = crc_end

    if ihdr is None or len(ihdr) != 13:
        die("%s has no valid IHDR chunk" % where)
    if not saw_iend:
        die("%s is truncated: no IEND chunk (this file looks cut off)" % where)
    if pos != size:
        die("%s has %d trailing bytes after IEND" % (where, size - pos))

    w, h, depth, colour, comp, filt, interlace = struct.unpack(">IIBBBBB", ihdr)
    if (w, h) != (EXPECT_SIDE, EXPECT_SIDE):
        die("%s is %dx%d but the contest requires %dx%d"
            % (where, w, h, EXPECT_SIDE, EXPECT_SIDE))
    if depth != 8 or colour not in (2, 6) or comp or filt or interlace:
        die("%s has unsupported PNG parameters (depth %d, colour %d, "
            "compression %d, filter %d, interlace %d)"
            % (where, depth, colour, comp, filt, interlace))
    if not idat:
        die("%s has no IDAT chunk" % where)

    channels = 3 if colour == 2 else 4
    row_bytes = 1 + w * channels
    expect_raw = h * row_bytes
    dec = zlib.decompressobj()
    raw = bytearray()
    try:
        for piece in idat:
            raw += dec.decompress(piece, expect_raw + 1 - len(raw))
            if len(raw) > expect_raw:
                die("%s is corrupt: image data longer than the header allows"
                    % where)
        raw += dec.flush()
    except zlib.error as e:
        die("%s is corrupt: image data does not decompress (%s)" % (where, e))
    if len(raw) != expect_raw:
        die("%s is incomplete: image data is %d bytes, expected %d for %dx%d "
            "(the file is likely truncated)"
            % (where, len(raw), expect_raw, w, h))
    for y in range(h):
        if raw[y * row_bytes] > 4:
            die("%s is corrupt: scanline %d has illegal filter byte %d"
                % (where, y, raw[y * row_bytes]))
    return size


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        die("cannot create output directory %r: %s" % (out_dir, e))

    try:
        with open(BUNDLED, "rb") as f:
            data = f.read()
    except OSError as e:
        die("cannot read bundled image %r: %s" % (BUNDLED, e))

    # Fail fast on the source, before we touch the output directory at all.
    n_src = check_png_bytes(data, "bundled entry.png")

    fd, staged = _mkstemp(out_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # 0644 BEFORE the rename: the deployed name must never appear at 0600.
        os.chmod(staged, stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP | stat.S_IROTH)

        # Prove the bytes we are about to publish are intact on disk.
        with open(staged, "rb") as f:
            back = f.read()
        n_staged = check_png_bytes(back, "staged copy")
        if back != data:
            die("staged copy differs from the bundled image — refusing to "
                "publish a corrupted file")

        dest = os.path.join(out_dir, "entry.png")
        os.replace(staged, dest)  # atomic: same filesystem, by construction
    except BaseException:
        # Only unlink the staging file if it still exists (rename removes it).
        try:
            os.unlink(staged)
        except OSError:
            pass
        raise

    # Verify what actually landed at the destination.
    try:
        st = os.stat(dest)
        with open(dest, "rb") as f:
            final = f.read()
    except OSError as e:
        die("cannot read back deployed %r: %s" % (dest, e))
    n_final = check_png_bytes(final, "deployed entry.png")
    if n_final != n_src:
        die("deployed size %d differs from bundled size %d"
            % (n_final, n_src))
    mode = stat.S_IMODE(st.st_mode)
    if mode != 0o644:
        die("deployed file mode is %04o, expected 0644" % mode)

    print("deployed %s (%d bytes, mode 0644, %dx%d) -> %s"
          % (os.path.basename(BUNDLED), n_final, EXPECT_SIDE, EXPECT_SIDE, dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
