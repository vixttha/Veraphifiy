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


def png(image_data, interlace=0):
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, interlace))
            + chunk(b"IDAT", image_data) + chunk(b"IEND", b""))


class PngTests(unittest.TestCase):
    def verify_payload(self, payload):
        with TemporaryDirectory() as temporary, patch("verify.ASSETS", Path(temporary)):
            (Path(temporary) / "logo.png").write_bytes(payload)
            check_png({
                "file": "logo.png", "width": 1, "height": 1, "alpha": True,
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
