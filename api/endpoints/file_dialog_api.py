"""
File API endpoint for the NFS Resources Converter.
This module handles all file-related operations.
"""

from typing import Optional, List

from api.bridge import bridge


class FileDialogAPI:
    """
    API endpoints for file dialogs
    """

    def __init__(self, api):
        """
        Initialize the FileAPI endpoint.

        Args:
            api: The main API instance
        """
        self.api = api

    def open_file_dialog(self, multiple: bool = False) -> List[str]:
        """
        Open a file dialog and return the selected file paths.

        Args:
            multiple: Whether to allow selecting multiple files

        Returns:
            The list of selected file paths
        """
        window = bridge.get_window()
        if window is None:
            # No native web view (Linux/Eel): fall back to a Tk file dialog,
            # as the app did before the pywebview migration.
            from tkinter import Tk
            from tkinter.filedialog import askopenfilename, askopenfilenames
            root = Tk()
            root.withdraw()
            root.update()
            root.lift()
            root.attributes('-topmost', True)
            root.after_idle(root.attributes, '-topmost', False)
            filenames = []
            if multiple:
                selection = askopenfilenames()
                if selection:
                    filenames = list(selection)
            else:
                filename = askopenfilename()
                if filename:
                    filenames = [filename]
            root.destroy()
            return filenames
        import webview
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

        window = bridge.get_window()
        if window is None:
            # No native web view (Linux/Eel): fall back to a Tk save dialog.
            from tkinter import Tk
            from tkinter.filedialog import asksaveasfilename
            root = Tk()
            root.withdraw()
            root.update()
            root.lift()
            root.attributes('-topmost', True)
            root.after_idle(root.attributes, '-topmost', False)
            tk_initialdir = None
            tk_initialfile = None
            if file_name:
                if os.path.isdir(file_name):
                    tk_initialdir = file_name
                else:
                    dir_part = os.path.dirname(file_name)
                    file_part = os.path.basename(file_name)
                    if dir_part and os.path.isdir(dir_part):
                        tk_initialdir = dir_part
                        tk_initialfile = file_part
                    elif dir_part:
                        tk_initialfile = file_name
                    else:
                        tk_initialfile = file_name
            filename = asksaveasfilename(
                initialdir=tk_initialdir,
                initialfile=tk_initialfile,
            )
            root.destroy()
            if not filename:
                return None
            return filename
        import webview

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

    def select_directory_dialog(self) -> str:
        window = bridge.get_window()
        if window is None:
            # No native web view (Linux/Eel): fall back to a Tk directory dialog.
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            directory = filedialog.askdirectory()
            root.destroy()
            return directory or ''
        import webview
        selection = window.create_file_dialog(webview.FOLDER_DIALOG)
        if not selection:
            return ''
        if isinstance(selection, (list, tuple)):
            return selection[0]
        return selection
