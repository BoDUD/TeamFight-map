from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools import map_setting_round_trip


def pack_u64(value: int) -> bytes:
    return struct.pack("<Q", value)


def pack_chunked_binary_matrix(values: list[int], logical_size: int = 2) -> bytes:
    matrix_size = logical_size * logical_size
    if len(values) != matrix_size * matrix_size:
        raise ValueError("wrong matrix length")
    out = bytearray()
    out += pack_u64(logical_size)
    for group_y in range(logical_size):
        out += pack_u64(logical_size)
        for group_x in range(logical_size):
            out += pack_u64(logical_size)
            for local_y in range(logical_size):
                y = group_y * logical_size + local_y
                start = y * matrix_size + group_x * logical_size
                row = values[start : start + logical_size]
                out += pack_u64(logical_size)
                out += bytes(row)
    return bytes(out)


def pack_packed4(values: list[int]) -> bytes:
    if len(values) % 2:
        raise ValueError("packed4 values must have even length")
    blob = bytearray()
    for index in range(0, len(values), 2):
        blob.append(values[index] | (values[index + 1] << 4))
    return pack_u64(len(values)) + pack_u64(len(blob)) + bytes(blob)


def synthetic_map_setting() -> bytes:
    visibility = [
        0,
        1,
        1,
        0,
        1,
        0,
        0,
        1,
        1,
        0,
        0,
        1,
        0,
        1,
        1,
        0,
    ]
    packed0 = list(range(16))
    packed1 = [15, 0, 8, 7]
    return pack_chunked_binary_matrix(visibility) + pack_packed4(packed0) + pack_packed4(packed1)


class MapSettingRoundTripTests(unittest.TestCase):
    def test_decode_then_encode_preserves_bytes(self) -> None:
        data = synthetic_map_setting()
        document = map_setting_round_trip.decode_map_setting(data)

        encoded = map_setting_round_trip.encode_map_setting(document)

        self.assertEqual(data, encoded)
        self.assertEqual(2, len(document.packed4_layers))
        chunked = map_setting_round_trip.chunked_layer_summary(document.chunked_binary_layer)
        self.assertEqual([4, 4], chunked["composed_size"])
        self.assertTrue(chunked["uniform_shape"])
        self.assertEqual({"0": 8, "1": 8}, chunked["value_histogram"])
        self.assertEqual(
            {
                "0": 1,
                "1": 1,
                "2": 1,
                "3": 1,
                "4": 1,
                "5": 1,
                "6": 1,
                "7": 1,
                "8": 1,
                "9": 1,
                "10": 1,
                "11": 1,
                "12": 1,
                "13": 1,
                "14": 1,
                "15": 1,
            },
            map_setting_round_trip.packed4_layer_summary(document.packed4_layers[0])["value_histogram"],
        )

    def test_round_trip_file_writes_manifest_and_output_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "map_setting"
            evidence_dir = root / "evidence"
            source.write_bytes(synthetic_map_setting())

            manifest = map_setting_round_trip.round_trip_file(
                input_path=source,
                evidence_dir=evidence_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            output = evidence_dir / "map_setting.roundtrip.map_setting"
            manifest_path = evidence_dir / "map_setting_round_trip_manifest.json"
            self.assertTrue(output.exists())
            self.assertTrue(manifest_path.exists())
            self.assertEqual(source.read_bytes(), output.read_bytes())
            self.assertTrue(manifest["byte_identical"])
            self.assertFalse(manifest["safety"]["field_mutations"])
            self.assertEqual("pass", json.loads(manifest_path.read_text(encoding="utf-8"))["result"])

    def test_first_difference_reports_offset_and_context(self) -> None:
        diff = map_setting_round_trip.first_difference(b"abcdef", b"abcxef")

        self.assertIsNotNone(diff)
        assert diff is not None
        self.assertEqual(3, diff["offset"])
        self.assertEqual(6, diff["input_size"])
        self.assertEqual("61 62 63 64 65 66", diff["input_context_hex"])
        self.assertEqual("61 62 63 78 65 66", diff["output_context_hex"])

    def test_round_trip_refuses_repo_evidence_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "map_setting"
            source.write_bytes(synthetic_map_setting())

            with self.assertRaises(SystemExit) as raised:
                map_setting_round_trip.round_trip_file(
                    input_path=source,
                    evidence_dir=map_setting_round_trip.REPO_ROOT / "tmp_round_trip_evidence",
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("inside the repository", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
