import os
import subprocess
import traceback
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from typing import Dict, Any

import eel

import config
from library import require_file
from library.utils import format_exception, path_join
from serializers import get_serializer


class ConversionAPI:

    def __init__(self, api):
        """Initialize the ConversionAPI."""
        self.api = api
        self.current_progress = 0
        self.total_files = 0

    def get_general_config(self) -> Dict[str, Any]:
        return config.general_config().to_dict()

    def get_conversion_config(self) -> Dict[str, Any]:
        return config.conversion_config().to_dict()

    def patch_general_config(self, config_obj: Dict) -> Dict[str, Any]:
        for (key, value) in config_obj.items():
            config.set_config(config.SECTION_GENERAL, key, value)
        return config.general_config().to_dict()

    def patch_conversion_config(self, config_obj: Dict) -> Dict[str, Any]:
        for (key, value) in config_obj.items():
            config.set_config(config.SECTION_CONVERSION, key, value)
        return config.conversion_config().to_dict()

    def test_executable(self, executable_path: str) -> Dict[str, Any]:
        """
        Test if an executable can be run.

        Args:
            executable_path: Path to the executable

        Returns:
            Dict with test result
        """
        try:
            # Try to run the executable with a simple command
            # For Blender, use --version
            # For FFmpeg, use -version
            if "blender" in executable_path.lower():
                cmd = [executable_path, "--version"]
            else:  # Assume FFmpeg
                cmd = [executable_path, "-version"]

            # Run the command with a timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            # Check if the command was successful
            if result.returncode == 0:
                return {"success": True, "message": "Executable test passed"}
            else:
                return {"success": False, "message": f"Executable test failed: {result.stderr}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Executable test timed out"}
        except Exception as e:
            return {"success": False, "message": f"Error testing executable: {str(e)}"}

    def select_directory_dialog(self) -> str:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        directory = filedialog.askdirectory()
        return directory

    def export_file(self, args):
        base_input_path, path, out_path, custom_settings = args
        try:
            (name, block, data) = require_file(path)
            serializer = get_serializer(block, data)
            serializer.patch_settings(custom_settings)
            rel_path = path[len(base_input_path):]
            if not rel_path:
                is_dir = serializer.is_dir
                # DelegateBlock
                if callable(is_dir):
                    is_dir = is_dir(block, data)
                if is_dir:
                    rel_path = path.split('/')[-1]
            serializer.serialize(data, f'{out_path}/{rel_path}', id=name, block=block)
            return None
        except Exception as ex:
            if config.general_config().print_errors:
                traceback.print_exc()
            return ex

    def convert_files(self, input_path: str, output_path: str, custom_settings: Dict[str, Any] = None) -> Dict[
        str, Any]:
        opened_file = self.api.file_api.current_file_name
        if opened_file:
            self.api.file_api.close_file()
        try:
            if not os.path.exists(input_path):
                return {"success": False, "error": f"Input path does not exist: {input_path}"}

            if not os.path.exists(output_path):
                os.makedirs(output_path, exist_ok=True)
            self.current_progress = 0
            base_input_path = str(input_path)
            files_to_open = []
            if os.path.isdir(input_path):
                for subdir, dirs, files in os.walk(input_path):
                    files_to_open += [path_join(subdir, f) for f in files]
            else:
                files_to_open = [str(input_path).replace('\\', '/')]

            self.total_files = len(files_to_open)

            eel.update_conversion_progress(0, self.total_files)

            def update_progress(result):
                self.current_progress += 1
                eel.update_conversion_progress(self.current_progress, self.total_files)

            conversion_config = config.conversion_config(custom_settings)
            processes = conversion_config.multiprocess_processes_count
            if processes == 0:
                processes = cpu_count()

            with Pool(processes=processes) as pool:
                args_list = [(base_input_path, f, output_path, custom_settings) for f in files_to_open]
                results = []
                for args in args_list:
                    result = pool.apply_async(self.export_file, (args,), callback=update_progress)
                    results.append(result)
                for result in results:
                    result.wait()
                results = [result.get() for result in results]

            skipped_resources = [(files_to_open[i], exc) for i, exc in enumerate(results) if isinstance(exc, Exception)]
            if skipped_resources:
                skipped_map = defaultdict(lambda: list())
                for name, ex in skipped_resources:
                    name = name.replace('\\', '/')
                    path, name = '/'.join(name.split('/')[:-1]), name.split('/')[-1]
                    skipped_map[path].append((name, format_exception(ex)))
                for path, skipped in skipped_map.items():
                    path_suffix = path[len(base_input_path):]
                    if path_suffix.startswith('/'):
                        path_suffix = path_suffix[1:]
                    skipped_txt_output_path = path_join(output_path, path_suffix, 'skipped.txt')
                    os.makedirs(os.path.dirname(skipped_txt_output_path), exist_ok=True)
                    skipped.sort(key=lambda x: x[0])
                    with open(skipped_txt_output_path, 'w') as f:
                        for item in skipped:
                            f.write("%s\t\t%s\n" % item)
            eel.update_conversion_progress(self.total_files, self.total_files)
            return {"success": True, "output_path": output_path}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        finally:
            if opened_file:
                self.api.file_api.open_file(opened_file)
