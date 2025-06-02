"""
File API endpoint for the NFS Resources Converter.
This module handles all file-related operations.
"""

import eel
import traceback
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from typing import Dict, Optional, Tuple, Any

import settings
from library import require_file
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
            eel.open_file(self.api.initial_file_path)

    def open_file_dialog(self) -> Optional[str]:
        """
        Open a file dialog and return the selected file path.

        Returns:
            The selected file path or None if canceled
        """
        root = Tk()
        root.withdraw()
        root.update()
        # Bring the dialog to front on macOS
        root.lift()
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        filename = askopenfilename()
        root.destroy()
        return filename

    def open_file(self, path: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Open a file and return its data.

        Args:
            path: Path to the file
            force_reload: Whether to force reload the file from disk

        Returns:
            File data
        """
        try:
            if force_reload:
                clear_file_cache(path)
            (name, block, data) = require_file(path)
            self.current_file_name = name
            self.current_file_data = data
            self.current_file_block = block
        except Exception as ex:
            if settings.print_errors:
                traceback.print_exc()
            self.current_file_data = {
                'error_class': ex.__class__.__name__,
                'error_text': str(ex),
            }
            self.current_file_name = path
            self.current_file_block = None

        return {
            'name': self.current_file_name,
            'schema': self.current_file_block.schema if self.current_file_block else None,
            'data': self.render_data(self.current_file_data)
        }

    def start_file(self, path: str) -> Dict[str, Any]:
        try:
            start_file(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_file_with_system_app(self, path: str):
        if path.startswith('/') or path.startswith('\\'):
            path = path[1:]
        start_file(path_join(self.api.static_path, path))

    def save_file(self, path: str, changes: Dict) -> Dict:
        """
        Save changes to a file.

        Args:
            path: Path to the file
            changes: Changes to apply

        Returns:
            Updated file data
        """
        from api.utils import apply_delta_to_resource

        apply_delta_to_resource(self.current_file_name, self.current_file_data, changes)
        bts = self.current_file_block.pack(self.current_file_data)
        with open(path, 'wb') as file:
            file.write(bts)
        clear_file_cache(path)
        return self.render_data(self.current_file_data)
