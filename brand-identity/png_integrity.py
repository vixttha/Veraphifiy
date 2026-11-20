"""Validate PNG chunks and scanlines using the Python standard library."""

import struct
import sys
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNEL_DEPTHS = {
    0: (1, (1, 2, 4, 8, 16)),
    2: (3, (8, 16)),
    3: (1, (1, 2, 4, 8)),
    4: (2, (8, 16)),
    6: (4, (8, 16)),
}
ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
         (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


def png_chunks(payload):
    if not payload.startswith(SIGNATURE):
        raise ValueError("missing PNG signature")
    offset = len(SIGNATURE)
    while offset < len(payload):
        if len(payload) - offset < 12:
            raise ValueError("truncated PNG chunk")
        size, kind = struct.unpack_from(">I4s", payload, offset)
        end = offset + 8 + size
        if size >= 2**31 or end + 4 > len(payload):
            raise ValueError("invalid PNG chunk length")
        data = payload[offset + 8:end]
        (checksum,) = struct.unpack_from(">I", payload, end)
        if zlib.crc32(data, zlib.crc32(kind)) != checksum:
            raise ValueError(f"{kind!r} chunk CRC mismatch")
        offset = end + 4
        yield kind, data
        if kind == b"IEND":
            if data or offset != len(payload):
                raise ValueError("invalid IEND or trailing PNG data")
            return
    raise ValueError("missing IEND chunk")


def paeth(left, above, upper_left):
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def unfilter_indexed_row(row, previous, filter_type):
    # Every indexed pixel is at most one byte, including packed samples.
    for index, value in enumerate(row):
        left = row[index - 1] if index else 0
        above = previous[index]
        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = above
        elif filter_type == 3:
            predictor = (left + above) // 2
        else:
            predictor = paeth(left, above, previous[index - 1] if index else 0)
        row[index] = (value + predictor) & 255


def validate_indexed_pass(pixels, offset, rows, columns, stride, depth, palette_entries):
    previous = bytes(stride - 1)
    samples_per_byte = 8 // depth
    mask = (1 << depth) - 1
    for start in range(offset, offset + rows * stride, stride):
        filter_type = pixels[start]
        row = bytearray(pixels[start + 1:start + stride])
        if filter_type:
            unfilter_indexed_row(row, previous, filter_type)
        # Packed samples occupy the high bits first. The last byte can have padding.
        for column in range(columns):
            byte, sample = divmod(column, samples_per_byte)
            index = (row[byte] >> (8 - (sample + 1) * depth)) & mask
            if index >= palette_entries:
                raise ValueError("indexed PNG pixel exceeds the palette")
        previous = row


def validate_scanlines(compressed, width, height, bits_per_pixel, interlace, palette_entries=None):
    passes = []
    for x, y, dx, dy in (ADAM7 if interlace else ((0, 0, 1, 1),)):
        columns = (width - x + dx - 1) // dx
        rows = (height - y + dy - 1) // dy
        if columns > 0 and rows > 0:
            passes.append((rows, columns, 1 + (columns * bits_per_pixel + 7) // 8))
    expected = sum(rows * stride for rows, _, stride in passes)
    decoder = zlib.decompressobj()
    try:
        pixels = decoder.decompress(compressed, min(expected + 1, sys.maxsize))
    except zlib.error as error:
        raise ValueError("invalid PNG compressed image data") from error
    if len(pixels) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError("PNG image data length does not match the dimensions")
    offset = 0
    sample_limit = 1 << bits_per_pixel
    for rows, columns, stride in passes:
        end = offset + rows * stride
        if any(filter_type > 4 for filter_type in memoryview(pixels)[offset:end:stride]):
            raise ValueError("invalid PNG scanline filter")
        if palette_entries is not None and palette_entries < sample_limit:
            validate_indexed_pass(pixels, offset, rows, columns, stride, bits_per_pixel, palette_entries)
        offset = end


def inspect_png(payload):
    chunks = png_chunks(payload)
    kind, header = next(chunks, (None, b""))
    if kind != b"IHDR" or len(header) != 13:
        raise ValueError("missing or invalid IHDR chunk")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", header)
    if color not in CHANNEL_DEPTHS or not (0 < width < 2**31 and 0 < height < 2**31):
        raise ValueError("invalid PNG dimensions or color type")
    channels, depths = CHANNEL_DEPTHS[color]
    if depth not in depths or compression or filtering or interlace not in (0, 1):
        raise ValueError("unsupported or invalid PNG header fields")

    image_data = bytearray()
    saw_idat = False
    ended_idat = False
    palette_entries = 0
    saw_transparency = False
    for kind, data in chunks:
        if kind == b"IDAT":
            if ended_idat or (color == 3 and not palette_entries):
                raise ValueError("invalid IDAT sequence or missing indexed palette")
            saw_idat = True
            image_data.extend(data)
            continue
        ended_idat = saw_idat
        if kind == b"PLTE":
            entries, remainder = divmod(len(data), 3)
            limit = 2**depth if color == 3 else 256
            if (palette_entries or saw_idat or saw_transparency or color in (0, 4)
                    or remainder or not 1 <= entries <= limit):
                raise ValueError("invalid PNG palette")
            palette_entries = entries
        elif kind == b"tRNS":
            if saw_transparency or saw_idat or color in (4, 6):
                raise ValueError("invalid PNG tRNS ordering or color type")
            if color == 3:
                if not 1 <= len(data) <= palette_entries:
                    raise ValueError("invalid indexed PNG tRNS length or missing palette")
            else:
                if len(data) != (2 if color == 0 else 6):
                    raise ValueError("invalid PNG tRNS sample length")
                if any(sample >= 2**depth for (sample,) in struct.iter_unpack(">H", data)):
                    raise ValueError("PNG tRNS sample exceeds bit depth")
            saw_transparency = True
        elif kind != b"IEND" and not kind[0] & 32:
            raise ValueError(f"unexpected critical PNG chunk: {kind!r}")
    if not saw_idat:
        raise ValueError("missing PNG image data")
    validate_scanlines(image_data, width, height, channels * depth, interlace,
                       palette_entries if color == 3 else None)
    return width, height, color in (4, 6)
