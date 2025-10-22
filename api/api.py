"""
Main API class for the NFS Resources Converter.
This class initializes and manages all API endpoints.
"""

import eel

from .endpoints.conversion_api import ConversionAPI
from .endpoints.file_api import FileAPI
from .endpoints.resource_api import ResourceAPI
from .endpoints.serialization_api import SerializationAPI


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

        # Register all API endpoints with Eel
        self._register_endpoints()

    def _register_endpoints(self):
        """Register all API endpoints with Eel."""
        # File API
        eel.expose(self.file_api.on_angular_ready)
        eel.expose(self.file_api.open_file_dialog)
        eel.expose(self.file_api.open_file)
        eel.expose(self.file_api.open_file_with_system_app)
        eel.expose(self.file_api.start_file)
        eel.expose(self.file_api.save_file)
        eel.expose(self.file_api.close_file)

        # Resource API
        eel.expose(self.resource_api.retrieve_value)
        eel.expose(self.resource_api.run_custom_action)

        # Serialization API
        eel.expose(self.serialization_api.serialize_resource)
        eel.expose(self.serialization_api.serialize_reversible)
        eel.expose(self.serialization_api.serialize_resource_tmp)
        eel.expose(self.serialization_api.deserialize_resource)

        # Conversion API
        eel.expose(self.conversion_api.select_directory_dialog)
        eel.expose(self.conversion_api.convert_files)
        eel.expose(self.conversion_api.get_general_config)
        eel.expose(self.conversion_api.get_conversion_config)
        eel.expose(self.conversion_api.patch_general_config)
        eel.expose(self.conversion_api.patch_conversion_config)
        eel.expose(self.conversion_api.test_executable)
