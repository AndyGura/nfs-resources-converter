"""
Main API class for the NFS Resources Converter.
This class initializes and manages all API endpoints.
"""

from api.bridge import bridge
from .endpoints.conversion_api import ConversionAPI
from .endpoints.file_api import FileAPI
from .endpoints.file_dialog_api import FileDialogAPI
from .endpoints.resource_api import ResourceAPI
from .endpoints.serialization_api import SerializationAPI
from .endpoints.changes_api import ChangesAPI
from version import __version__


class API:
    """
    Main API class that initializes and manages all API endpoints.
    This provides a clean boundary between the frontend and backend.
    """

    def __init__(self, static_path: str, initial_file_path: str = None):
        """
        Initialize the API with all endpoints.

        Args:
            static_path: Path to the static files directory
            initial_file_path: Optional path to a file to open when the GUI starts
        """
        self.static_path = static_path
        self.initial_file_path = initial_file_path

        # Initialize endpoints
        self.file_api = FileAPI(self)
        self.resource_api = ResourceAPI(self)
        self.serialization_api = SerializationAPI(self)
        self.conversion_api = ConversionAPI(self)
        self.changes_api = ChangesAPI(self)
        self.file_dialog_api = FileDialogAPI(self)

        # Register all API endpoints
        self._register_endpoints()

    def _register_endpoints(self):
        """Register all API endpoints with bridge."""
        # File API
        bridge.expose(self.file_api.on_angular_ready)
        bridge.expose(self.file_api.open_file)
        bridge.expose(self.file_api.open_file_with_system_app)
        bridge.expose(self.file_api.open_url)
        bridge.expose(self.file_api.save_file)
        bridge.expose(self.file_api.create_new_file)
        bridge.expose(self.file_api.close_file)

        # Resource API
        bridge.expose(self.resource_api.retrieve_value)
        bridge.expose(self.resource_api.run_custom_action)
        bridge.expose(self.resource_api.get_new_item_data)

        # Serialization API
        bridge.expose(self.serialization_api.serialize_resource)
        bridge.expose(self.serialization_api.deserialize_resource)

        # Conversion API
        bridge.expose(self.conversion_api.convert_files)
        bridge.expose(self.conversion_api.get_general_config)
        bridge.expose(self.conversion_api.get_conversion_config)
        bridge.expose(self.conversion_api.patch_general_config)
        bridge.expose(self.conversion_api.patch_conversion_config)
        bridge.expose(self.conversion_api.test_executable)

        # Changes API
        bridge.expose(self.changes_api.get_revisions)
        bridge.expose(self.changes_api.get_changes)
        bridge.expose(self.changes_api.on_fe_update)

        # Version API
        bridge.expose(self.get_version)

        # File dialog API
        bridge.expose(self.file_dialog_api.open_file_dialog)
        bridge.expose(self.file_dialog_api.save_file_dialog)
        bridge.expose(self.file_dialog_api.select_directory_dialog)

    def get_version(self) -> str:
        """Return the current application version."""
        return __version__
