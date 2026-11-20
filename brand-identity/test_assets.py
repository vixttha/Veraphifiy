"""Regression checks for asset validation."""

import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zlib

from png_integrity import inspect_png
from verify import check_inventory, check_png


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(image_data, interlace=0, *, width=1, height=1, depth=8, palette_entries=None):
    color = 6 if palette_entries is None else 3
    palette = b"" if palette_entries is None else chunk(b"PLTE", b"\0" * (3 * palette_entries))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, color, 0, 0, interlace))
            + palette + chunk(b"IDAT", image_data) + chunk(b"IEND", b""))


class PngTests(unittest.TestCase):
    def verify_payload(self, payload, width=1, height=1, alpha=True):
        with TemporaryDirectory() as temporary, patch("verify.ASSETS", Path(temporary)):
            (Path(temporary) / "logo.png").write_bytes(payload)
            check_png({
                "file": "logo.png", "width": width, "height": height, "alpha": alpha,
                "sha256": hashlib.sha256(payload).hexdigest(), "generated_with": "@Images",
                "role": "logo", "alt": "Test logo", "source": "Synthetic fixture", "status": "draft",
            })

    def test_transparent_png(self):
        for interlace in (0, 1):
            with self.subTest(interlace=interlace):
                self.verify_payload(png(zlib.compress(b"\0" * 5), interlace))

    def test_corrupt_png_fails_even_with_matching_hash(self):
        for data, error in ((b"invalid", "compressed"), (zlib.compress(b"\0"), "length"),
                            (zlib.compress(b"\xff" + b"\0" * 4), "filter")):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.verify_payload(png(data))

    def test_bad_chunk_crc_fails_even_with_matching_hash(self):
        payload = png(zlib.compress(b"\0" * 5))
        bad_crc = payload[:-13] + bytes([payload[-13] ^ 1]) + payload[-12:]
        with self.assertRaisesRegex(ValueError, "CRC"):
            self.verify_payload(bad_crc)


    def test_keyed_transparency_checks_length_order_and_cardinality(self):
        header = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        data = chunk(b"IDAT", zlib.compress(b"\0" * 4))
        key = chunk(b"tRNS", b"\0" * 6)
        signature = b"\x89PNG\r\n\x1a\n"
        end = chunk(b"IEND", b"")
        self.assertEqual(inspect_png(signature + header + key + data + end), (1, 1, False))
        for parts in (
            chunk(b"tRNS", b"\0" * 5) + data,
            data + key,
            key + key + data,
            chunk(b"tRNS", b"\x01" + b"\0" * 5) + data,
        ):
            with self.assertRaisesRegex(ValueError, "tRNS"):
                inspect_png(signature + header + parts + end)


    def test_indexed_png_reverses_all_scanline_filters(self):
        first_row = bytes((0, 1, 2, 0))
        encoded = [(2, 1, 2), (2, 255, 1), (1, 255, 2), (2, 255, 2), (1, 255, 2)]
        for filter_type, (first, second, third) in enumerate(encoded):
            with self.subTest(filter=filter_type):
                valid = first_row + bytes((filter_type, first, second, third))
                invalid = first_row + bytes((filter_type, first, second, (third + 1) & 255))
                options = {"width": 3, "height": 2, "palette_entries": 3}
                self.verify_payload(png(zlib.compress(valid), **options), width=3, height=2, alpha=False)
                with self.assertRaisesRegex(ValueError, "pixel exceeds the palette"):
                    self.verify_payload(png(zlib.compress(invalid), **options), width=3, height=2, alpha=False)

    def test_indexed_png_ignores_unused_packed_bits(self):
        for depth, entries, valid, invalid in (
            (1, 1, b"\x1f", b"\x20"),
            (2, 2, b"\x13", b"\x1b"),
            (4, 2, b"\x01\x1f", b"\x01\x2f"),
        ):
            with self.subTest(depth=depth):
                options = {"width": 3, "depth": depth, "palette_entries": entries}
                ordinary = png(zlib.compress(b"\0" + valid), **options)
                self.assertEqual(inspect_png(ordinary), (3, 1, False))
                with self.assertRaisesRegex(ValueError, "pixel exceeds the palette"):
                    inspect_png(png(zlib.compress(b"\0" + invalid), **options))

    def test_indexed_adam7_resets_filter_history_per_pass(self):
        # A 3x3 image has one row in passes 1, 4, 5 and 7, and two in pass 6.
        # Pass 4 starts with Up and an empty history. Pass 6 uses its own prior row.
        valid_rows = bytes((0, 0x40, 2, 0x40, 0, 0x1F, 0, 0x40, 2, 0, 0, 0x47))
        invalid_rows = valid_rows[:9] + bytes((0x40,)) + valid_rows[10:]
        options = {"interlace": 1, "width": 3, "height": 3, "depth": 2, "palette_entries": 2}
        self.assertEqual(inspect_png(png(zlib.compress(valid_rows), **options)), (3, 3, False))
        with self.assertRaisesRegex(ValueError, "pixel exceeds the palette"):
            inspect_png(png(zlib.compress(invalid_rows), **options))


class InventoryTests(unittest.TestCase):
    def test_finds_unsupported_export_paths(self):
        for filename in ("extra.PNG", "drafts/extra.png"):
            with self.subTest(filename=filename), TemporaryDirectory() as temporary:
                directory = Path(temporary)
                asset = directory / filename
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.touch()
                with patch("verify.ASSETS", directory), self.assertRaisesRegex(ValueError, "export"):
                    check_inventory([])

    def test_finds_unregistered_png_at_asset_root(self):
        with TemporaryDirectory() as temporary, patch("verify.ASSETS", Path(temporary)):
            (Path(temporary) / "extra.png").touch()
            with self.assertRaisesRegex(ValueError, "unregistered.*extra.png"):
                check_inventory([])
