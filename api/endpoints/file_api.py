"""
File API endpoint for the NFS Resources Converter.
This module handles all file-related operations.
"""

import os
import traceback
from typing import Dict, Optional, Any, List

from api.bridge import bridge as eel

from config import general_config, set_config, SECTION_GENERAL
from library import require_file
from library.changes_service import ChangesService
from library.loader import clear_file_cache
from library.utils import path_join
from library.utils.file_utils import start_file
from serializers.misc.json_utils import convert_bytes, serialize_exceptions


class FileAPI:
    """
    API endpoint for file-related operations.
    """

    def __init__(self, api):
        """
        Initialize the FileAPI endpoint.

        Args:
            api: The main API instance
        """
        self.api = api
        self.current_file_name = None
        self.current_file_data = None
        self.current_file_block = None

    def render_data(self, data):
        """
        Render data for frontend consumption.

        Args:
            data: The data to render

        Returns:
            Rendered data
        """
        return convert_bytes(serialize_exceptions(data))

    def on_angular_ready(self):
        """
        Called when Angular is ready.
        Opens the initial file if one was specified.
        """
        if self.api.initial_file_path:
            eel.open_arg_file(self.api.initial_file_path)

    def open_file_dialog(self, multiple: bool = False) -> List[str]:
        """
        Open a file dialog and return the selected file paths.

        Args:
            multiple: Whether to allow selecting multiple files

        Returns:
            The list of selected file paths
        """
        import webview

        window = eel.get_window()
        if window is None:
            return []
        selection = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=multiple,
        )
        if not selection:
            return []
        return list(selection)

    def save_file_dialog(self, file_name: Optional[str] = None) -> Optional[str]:
        """
        Open a save file dialog and return the selected file path.
    
        Args:
            file_name: Optional default file name or directory path to use
    
        Returns:
            The selected file path or None if canceled
        """
        import os
        import webview

        window = eel.get_window()
        if window is None:
            return None

        # Determine initial directory and filename
        initialdir = ''
        initialfile = ''

        if file_name:
            if os.path.isdir(file_name):
                # If file_name is a directory, use it as initialdir
                initialdir = file_name
            else:
                # If file_name contains a path, split it
                dir_part = os.path.dirname(file_name)
                file_part = os.path.basename(file_name)

                if dir_part and os.path.isdir(dir_part):
                    initialdir = dir_part
                    initialfile = file_part
                elif dir_part:
                    # Directory doesn't exist, just use the filename
                    initialfile = file_name
                else:
                    # No directory component, just a filename
                    initialfile = file_name

        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=initialdir,
            save_filename=initialfile,
        )
        if not result:
            return None
        # pywebview may return either a string or a one-element sequence.
        if isinstance(result, (list, tuple)):
            return result[0]
        return result

    def open_file(self, path: str, force_reload: bool = False, update_recent_files: bool = True) -> Dict[str, Any]:
        """
        Open a file and return its data.

        Args:
            path: Path to the file
            force_reload: Whether to force reload the file from disk
            update_recent_files: Whether to update the recent files list

        Returns:
            File data
        """
        if not path or not isinstance(path, str):
            return {
                'name': None,
                'schema': None,
                'data': None
            }
        try:
            if update_recent_files:
                # Update recent files
                abs_path = os.path.abspath(path)
                recent_files = general_config().recent_files
                if not isinstance(recent_files, list):
                    recent_files = []
                if abs_path in recent_files:
                    recent_files.remove(abs_path)
                recent_files.insert(0, abs_path)
                recent_files = recent_files[:10]
                set_config(SECTION_GENERAL, 'recent_files', ','.join(recent_files))
            if force_reload:
                clear_file_cache(path)
            (name, block, data) = require_file(path)
            self.current_file_name = name
            self.current_file_data = data
            self.current_file_block = block
        except Exception as ex:
            if general_config().print_errors:
                traceback.print_exc()
            self.current_file_data = {
                'error_class': ex.__class__.__name__,
                'error_text': str(ex),
            }
            self.current_file_name = path
            self.current_file_block = None
        finally:
            ChangesService.clear()

        return {
            'name': self.current_file_name,
            'schema': self.current_file_block.schema if self.current_file_block else None,
            'data': self.render_data(self.current_file_data)
        }

    def open_file_with_system_app(self, path: str):
        if os.path.isabs(path):
            start_file(path)
        else:
            if path.startswith('/') or path.startswith('\\'):
                path = path[1:]
            start_file(path_join(self.api.static_path, path))

    def close_file(self) -> Dict[str, Any]:
        """
        Close the current file and dispose it from cache.

        Returns:
            Dict with operation status
        """
        if self.current_file_name:
            clear_file_cache(self.current_file_name)
            file_name = self.current_file_name
            self.current_file_name = None
            self.current_file_data = None
            self.current_file_block = None
            ChangesService.clear()
            return {"success": True, "message": f"File {file_name} closed and removed from cache"}
        else:
            return {"success": False, "message": "No file is currently open"}

    def save_file(self, path: str) -> Dict:
        """
        Save changes to a file.

        Args:
            path: Path to the file

        Returns:
            Updated file data
        """
        bts = self.current_file_block.pack(self.current_file_data)
        with open(path, 'wb') as file:
            file.write(bts)
        ChangesService.on_file_saved()
        clear_file_cache(path)
        return self.render_data(self.current_file_data)

    def create_new_file(self, path: str, format_name: str):
        """
        Create a new empty file of given format.

        Args:
            path: Path where to save the file
            format_name: Name of the format (e.g. 'ffn')

        Returns:
            Result of open_file
        """
        if format_name.lower() == 'ffn':
            from resources.eac.fonts import FfnFont
            block = FfnFont()
            data = block.new_data()
        else:
            raise Exception(f'Unsupported format: {format_name}')

        bts = block.pack(data)
        with open(path, 'wb') as file:
            file.write(bts)