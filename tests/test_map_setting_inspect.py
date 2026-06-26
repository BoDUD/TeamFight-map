from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import map_setting_inspect
from tools import map_setting_round_trip as round_trip
from test_map_setting_round_trip import synthetic_map_setting


class MapSettingInspectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = synthetic_map_setting()
        self.document = round_trip.decode_map_setting(self.data)

    def test_flatten_chunked_binary_layer(self) -> None:
        values, width, height = map_setting_inspect.flatten_chunked_binary_layer(self.document.chunked_binary_layer)

        self.assertEqual((4, 4), (width, height))
        self.assertEqual(16, len(values))
        self.assertEqual({"0": 8, "1": 8}, map_setting_inspect.histogram(values))
        self.assertEqual(
            {
                "0": {"count": 8, "bbox": [0, 0, 3, 3]},
                "1": {"count": 8, "bbox": [0, 0, 3, 3]},
            },
            map_setting_inspect.bounding_boxes_by_value(values, width, height),
        )

    def test_unpack_packed4_layer(self) -> None:
        values = map_setting_inspect.unpack_packed4_layer(self.document.packed4_layers[0])

        self.assertEqual(list(range(16)), values)

    def test_symmetry_counters(self) -> None:
        symmetric = [
            1,
            2,
            3,
            4,
            2,
            5,
            6,
            7,
            3,
            6,
            5,
            8,
            4,
            7,
            8,
            1,
        ]

        self.assertEqual(0, map_setting_inspect.matrix_transpose_mismatch_count(symmetric, 4))
        self.assertGreater(map_setting_inspect.rotational_symmetry_mismatch_count(symmetric, 4, 4), 0)

    def test_packed4_cell_location_reports_byte_and_nibble(self) -> None:
        layer = self.document.packed4_layers[0]

        low = map_setting_inspect.packed4_cell_location(layer, 0, 0, 4)
        high = map_setting_inspect.packed4_cell_location(layer, 1, 0, 4)

        self.assertEqual(layer.offset + 16, low["serialized_byte_offset"])
        self.assertEqual("low", low["nibble"])
        self.assertEqual(layer.offset + 16, high["serialized_byte_offset"])
        self.assertEqual("high", high["nibble"])

    def test_inspect_rejects_repository_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "map_setting"
            source.write_bytes(self.data)

            with self.assertRaises(SystemExit) as raised:
                map_setting_inspect.inspect_map_setting(
                    input_path=source,
                    output_dir=round_trip.REPO_ROOT / "tmp_layer_inspection",
                    expected_sha256=round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal output directory", str(raised.exception))

    def test_inspect_rejects_repository_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(SystemExit) as raised:
                map_setting_inspect.inspect_map_setting(
                    input_path=round_trip.REPO_ROOT / "README.md",
                    output_dir=Path(temp_dir) / "inspection",
                    expected_sha256=None,
                )

            self.assertIn("repository-internal input", str(raised.exception))

    def assert_inspect_rejects_without_changing_sources(
        self,
        source: Path,
        output_dir: Path,
        expected_message: str,
        bundle: Path | None = None,
    ) -> None:
        source_before = source.read_bytes()
        bundle_before = bundle.read_bytes() if bundle else None

        with self.assertRaises(SystemExit) as raised:
            map_setting_inspect.inspect_map_setting(
                input_path=source,
                output_dir=output_dir,
                bundle_path=bundle,
                expected_sha256=round_trip.sha256_file(source),
            )

        self.assertIn(expected_message, str(raised.exception))
        self.assertEqual(source_before, source.read_bytes())
        if bundle and bundle_before is not None:
            self.assertEqual(bundle_before, bundle.read_bytes())

    def test_inspect_rejects_input_at_generated_png_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "chunked_binary_values.png"
            source.write_bytes(self.data)

            self.assert_inspect_rejects_without_changing_sources(
                source=source,
                output_dir=root,
                expected_message="input inside the output directory",
            )

    def test_inspect_rejects_input_at_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "layer_inspection_manifest.json"
            source.write_bytes(self.data)

            self.assert_inspect_rejects_without_changing_sources(
                source=source,
                output_dir=root,
                expected_message="input inside the output directory",
            )

    def test_inspect_rejects_generated_output_hardlink_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "evidence"
            source_dir.mkdir()
            output_dir.mkdir()
            source = source_dir / "map_setting"
            hardlink = output_dir / "chunked_binary_values.png"
            source.write_bytes(self.data)
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")

            self.assert_inspect_rejects_without_changing_sources(
                source=source,
                output_dir=output_dir,
                expected_message="Refusing to overwrite input",
            )

    def test_inspect_rejects_bundle_inside_original_assets_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "map_setting"
            output_dir = root / "evidence"
            bundle = output_dir / "original_assets" / "background_5v5.png"
            source.parent.mkdir()
            bundle.parent.mkdir(parents=True)
            source.write_bytes(self.data)
            bundle.write_bytes(b"bundle bytes")

            self.assert_inspect_rejects_without_changing_sources(
                source=source,
                output_dir=output_dir,
                bundle=bundle,
                expected_message="bundle inside the output directory",
            )

    def test_read_bundle_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "bundle.game_data"
            asset_type = b"png"
            asset_key = b"asset/test/key"
            payload = b"payload"
            bundle.write_bytes(
                (1).to_bytes(4, "little")
                + len(asset_type).to_bytes(4, "little")
                + asset_type
                + len(asset_key).to_bytes(4, "little")
                + asset_key
                + len(payload).to_bytes(4, "little")
                + payload
            )

            found_type, found_payload = map_setting_inspect.read_bundle_entry(bundle, "asset/test/key")

            self.assertEqual("png", found_type)
            self.assertEqual(payload, found_payload)

    def make_png_payload(self) -> bytes:
        buffer = io.BytesIO()
        image = Image.new("RGBA", (8, 8), (16, 32, 48, 255))
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def make_bundle(self, path: Path, payload: bytes) -> None:
        asset_type = b"png"
        asset_key = map_setting_inspect.DEFAULT_ASSET_KEYS["background_5v5"].encode("utf-8")
        path.write_bytes(
            (1).to_bytes(4, "little")
            + len(asset_type).to_bytes(4, "little")
            + asset_type
            + len(asset_key).to_bytes(4, "little")
            + asset_key
            + len(payload).to_bytes(4, "little")
            + payload
        )

    def test_inspect_generates_synthetic_pngs_overlay_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "map_setting"
            output_dir = root / "evidence"
            bundle = root / "bundle.game_data"
            source.parent.mkdir()
            source.write_bytes(self.data)
            self.make_bundle(bundle, self.make_png_payload())

            manifest = map_setting_inspect.inspect_map_setting(
                input_path=source,
                output_dir=output_dir,
                bundle_path=bundle,
                layout_path=None,
                expected_sha256=round_trip.sha256_file(source),
            )

            expected_images = [
                output_dir / "chunked_binary_values.png",
                output_dir / "packed4_0_values.png",
                output_dir / "packed4_0_value_0_mask.png",
                output_dir / "overlays" / "background_5v5_chunked_binary_overlay.png",
            ]
            for image_path in expected_images:
                self.assertTrue(image_path.exists(), image_path)
                with Image.open(image_path) as image:
                    self.assertGreater(image.size[0], 0)
                    self.assertGreater(image.size[1], 0)
            manifest_path = output_dir / "layer_inspection_manifest.json"
            clearance_path = output_dir / "candidate_clearance_manifest.json"
            self.assertTrue(manifest_path.exists())
            self.assertTrue(clearance_path.exists())
            self.assertEqual("map_setting_layer_inspection", manifest["probe"])
            self.assertEqual("not_selected", manifest["candidate_mutation"]["status"])

    def test_stdout_summary_omits_large_histograms(self) -> None:
        manifest = {
            "probe": "map_setting_layer_inspection",
            "input_sha256": "abc",
            "output_dir": "D:\\evidence",
            "layers": {
                "chunked_binary": {"shape": [900, 900], "histogram": {"0": 1}},
                "packed4_0": {"shape": [900, 900], "histogram": {"15": 1}},
                "packed4_1": {"value_count": 27000, "histogram": {"0": 1}},
            },
            "candidate_mutation": {
                "status": "needs_world_grid_validation",
                "layer": "chunked_binary",
                "candidate_unit": "undirected_edge",
                "edge": {"source_node": 369, "target_node": 370},
                "risk_classification": "unverified",
            },
            "safety": {"read_only": True},
        }

        summary = map_setting_inspect.stdout_summary(manifest)

        self.assertNotIn("histogram", summary)
        self.assertEqual("needs_world_grid_validation", summary["candidate_status"])
        self.assertEqual("undirected_edge", summary["candidate_unit"])
        self.assertEqual("unverified", summary["risk_classification"])
        self.assertTrue(summary["read_only"])


if __name__ == "__main__":
    unittest.main()
