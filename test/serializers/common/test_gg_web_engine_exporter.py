import os
import tempfile
import time
import unittest
from unittest.mock import patch

from serializers.common.three_d import gg_web_engine_exporter as sut


class TestGgWebEngineExporter(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        cache_dir = os.path.join(self._tmp_dir.name, "gg_web_engine_exporter")
        self._patchers = [
            patch.object(sut, "_CACHE_DIR", cache_dir),
            patch.object(sut, "_META_FILE", os.path.join(cache_dir, ".meta.json")),
            patch.object(sut, "_EXPORTER_FILE", os.path.join(cache_dir, "exporter.py")),
        ]
        for p in self._patchers:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._tmp_dir.cleanup)

    def _write_cached_copy(self, content: bytes, checked_at: float):
        os.makedirs(sut._CACHE_DIR, exist_ok=True)
        with open(sut._EXPORTER_FILE, "wb") as f:
            f.write(content)
        sut._write_meta({"checked_at": checked_at})

    def test_downloads_when_nothing_cached(self):
        with patch.object(sut, "_fetch", return_value=b"exporter v1") as mock_fetch:
            result_dir = sut.ensure_gg_web_engine_exporter_installed()

        mock_fetch.assert_called_once_with(sut._EXPORTER_URL)
        self.assertEqual(result_dir, sut._CACHE_DIR)
        with open(sut._EXPORTER_FILE, "rb") as f:
            self.assertEqual(f.read(), b"exporter v1")
        self.assertIn("checked_at", sut._read_meta())

    def test_raises_when_nothing_cached_and_fetch_fails(self):
        with patch.object(sut, "_fetch", side_effect=OSError("network down")):
            with self.assertRaises(RuntimeError):
                sut.ensure_gg_web_engine_exporter_installed()
        self.assertFalse(os.path.isfile(sut._EXPORTER_FILE))

    def test_skips_network_when_cache_is_fresh(self):
        self._write_cached_copy(b"exporter v1", checked_at=time.time())

        with patch.object(sut, "_fetch") as mock_fetch:
            result_dir = sut.ensure_gg_web_engine_exporter_installed()

        mock_fetch.assert_not_called()
        self.assertEqual(result_dir, sut._CACHE_DIR)

    def test_updates_stale_cache_with_new_content(self):
        stale_time = time.time() - sut._CHECK_TTL_SECONDS - 1
        self._write_cached_copy(b"exporter v1", checked_at=stale_time)

        with patch.object(sut, "_fetch", return_value=b"exporter v2") as mock_fetch:
            sut.ensure_gg_web_engine_exporter_installed()

        mock_fetch.assert_called_once()
        with open(sut._EXPORTER_FILE, "rb") as f:
            self.assertEqual(f.read(), b"exporter v2")
        self.assertGreater(sut._read_meta()["checked_at"], stale_time)

    def test_falls_back_to_cached_copy_when_stale_check_fails(self):
        stale_time = time.time() - sut._CHECK_TTL_SECONDS - 1
        self._write_cached_copy(b"exporter v1", checked_at=stale_time)

        with patch.object(sut, "_fetch", side_effect=OSError("network down")):
            result_dir = sut.ensure_gg_web_engine_exporter_installed()

        self.assertEqual(result_dir, sut._CACHE_DIR)
        with open(sut._EXPORTER_FILE, "rb") as f:
            self.assertEqual(f.read(), b"exporter v1")

    def test_touches_checked_at_without_rewriting_unchanged_content(self):
        stale_time = time.time() - sut._CHECK_TTL_SECONDS - 1
        self._write_cached_copy(b"exporter v1", checked_at=stale_time)

        with patch.object(sut, "_fetch", return_value=b"exporter v1"):
            sut.ensure_gg_web_engine_exporter_installed()

        self.assertGreater(sut._read_meta()["checked_at"], stale_time)
        with open(sut._EXPORTER_FILE, "rb") as f:
            self.assertEqual(f.read(), b"exporter v1")


if __name__ == "__main__":
    unittest.main()
