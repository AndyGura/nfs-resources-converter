import unittest
from unittest import mock

from library.utils import executable_detection


class TestFirstWorkingCandidate(unittest.TestCase):
    def test_bare_command_resolved_via_path(self):
        with mock.patch.object(executable_detection.shutil, "which", return_value="/usr/bin/ffmpeg") as which:
            result = executable_detection._first_working_candidate(["ffmpeg"])
        which.assert_called_once_with("ffmpeg")
        self.assertEqual(result, "/usr/bin/ffmpeg")

    def test_bare_command_not_on_path_falls_through_to_next_candidate(self):
        with mock.patch.object(executable_detection.shutil, "which", return_value=None), \
                mock.patch("os.path.isfile", return_value=True), mock.patch("os.access", return_value=True):
            result = executable_detection._first_working_candidate(["ffmpeg", "/opt/homebrew/bin/ffmpeg"])
        self.assertEqual(result, "/opt/homebrew/bin/ffmpeg")

    def test_absolute_path_candidate(self):
        with mock.patch("os.path.isfile", return_value=True), mock.patch("os.access", return_value=True):
            result = executable_detection._first_working_candidate(["/usr/local/bin/ffmpeg"])
        self.assertEqual(result, "/usr/local/bin/ffmpeg")

    def test_absolute_path_candidate_not_executable_is_skipped(self):
        with mock.patch("os.path.isfile", return_value=True), mock.patch("os.access", return_value=False):
            result = executable_detection._first_working_candidate(["/usr/local/bin/ffmpeg"])
        self.assertIsNone(result)

    def test_glob_candidate_prefers_highest_match(self):
        with mock.patch.object(executable_detection.glob, "glob",
                                return_value=["/Applications/Blender 3.6.app/Contents/MacOS/Blender",
                                              "/Applications/Blender 4.2.app/Contents/MacOS/Blender"]), \
                mock.patch("os.path.isfile", return_value=True), mock.patch("os.access", return_value=True):
            result = executable_detection._first_working_candidate(["/Applications/Blender *.app/Contents/MacOS/Blender"])
        self.assertEqual(result, "/Applications/Blender 4.2.app/Contents/MacOS/Blender")

    def test_no_candidates_found_returns_none(self):
        with mock.patch.object(executable_detection.shutil, "which", return_value=None), \
                mock.patch("os.path.isfile", return_value=False):
            result = executable_detection._first_working_candidate(["ffmpeg", "/usr/local/bin/ffmpeg"])
        self.assertIsNone(result)


class TestDetectFfmpegAndBlenderPath(unittest.TestCase):
    def test_detect_ffmpeg_path_uses_ffmpeg_candidates(self):
        with mock.patch.object(executable_detection, "_first_working_candidate",
                                return_value="/usr/bin/ffmpeg") as patched:
            result = executable_detection.detect_ffmpeg_path()
        self.assertEqual(result, "/usr/bin/ffmpeg")
        candidates = patched.call_args[0][0]
        self.assertIn("ffmpeg", candidates)

    def test_detect_blender_path_uses_blender_candidates(self):
        with mock.patch.object(executable_detection, "_first_working_candidate",
                                return_value="/usr/bin/blender") as patched:
            result = executable_detection.detect_blender_path()
        self.assertEqual(result, "/usr/bin/blender")
        candidates = patched.call_args[0][0]
        self.assertIn("blender", candidates)

    def test_detect_returns_none_when_nothing_found(self):
        with mock.patch.object(executable_detection, "_first_working_candidate", return_value=None):
            self.assertIsNone(executable_detection.detect_ffmpeg_path())
            self.assertIsNone(executable_detection.detect_blender_path())


if __name__ == '__main__':
    unittest.main()
