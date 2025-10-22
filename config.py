import configparser
import os
from typing import Any, Dict

from library.utils.class_dict import ClassDict

# Define configuration sections
SECTION_GENERAL = "General"
SECTION_CONVERSION = "Conversion"

# Define configuration file path
CONFIG_FILE_NAME = "nfs-resources-converter-settings.ini"
CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)

# Function to get the config file location
def get_config_file_location():
    """
    Get the location of the configuration file.

    Returns:
        str: The full path to the configuration file
    """
    return CONFIG_FILE_PATH


class ConfigManager:
    """
    Configuration manager for NFS Resources Converter.
    Handles loading configuration from different sources and provides
    a unified interface for accessing configuration values.
    """

    def __init__(self):
        self._config = configparser.ConfigParser()
        self._defaults = self._get_defaults()
        self._load_config()

    def _get_defaults(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default configuration values.

        Returns:
            Dict with default configuration values
        """
        return {
            SECTION_GENERAL: {
                "blender_executable": "blender",
                "ffmpeg_executable": "ffmpeg",
                "print_errors": False,
                "print_blender_log": False,
            },
            SECTION_CONVERSION: {
                "multiprocess_processes_count": 0,
                "input_path": "",
                "output_path": "",
                "images__save_images_only": False,
                "maps__save_as_chunked": False,
                "maps__save_invisible_wall_collisions": False,
                "maps__save_terrain_collisions": False,
                "maps__save_spherical_skybox_texture": True,
                "maps__add_props_to_obj": True,
                "geometry__save_obj": True,
                "geometry__save_blend": True,
                "geometry__export_to_gg_web_engine": False,
            },
        }

    def _load_config(self):
        """
        Load configuration from file if it exists.
        """
        # Create sections in config
        for section in self._defaults:
            if not self._config.has_section(section):
                self._config.add_section(section)

        # Load from config file if it exists
        if os.path.exists(CONFIG_FILE_PATH):
            self._config.read(CONFIG_FILE_PATH)

    def _get_env_var_name(self, section: str, key: str) -> str:
        """
        Get environment variable name for a configuration key.

        Args:
            section: Configuration section
            key: Configuration key

        Returns:
            Environment variable name
        """
        return f"NFS_RESOURCES_CONVERTER_{section.upper()}_{key.upper()}"

    def get(self, section: str, key: str) -> Any:
        """
        Get configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        default = self._get_defaults().get(section, {}).get(key)
        # Check environment variable first
        env_var_name = self._get_env_var_name(section, key)
        env_value = os.environ.get(env_var_name)
        if env_value is not None:
            return self._convert_value(env_value, default)

        # Check config file
        try:
            if self._config.has_option(section, key):
                value = self._config.get(section, key)
                return self._convert_value(value, default)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass

        # Check defaults
        if section in self._defaults and key in self._defaults[section]:
            return self._defaults[section][key]

        # Return provided default or None
        return default

    def _convert_value(self, value: str, default: Any) -> Any:
        """
        Convert string value to appropriate type based on default value.

        Args:
            value: String value to convert
            default: Default value used for type inference

        Returns:
            Converted value
        """
        if default is None:
            return value

        if isinstance(default, bool):
            return value.lower() in ('true', 'yes', '1', 'y', 't')
        elif isinstance(default, int):
            return int(value)
        elif isinstance(default, float):
            return float(value)
        elif isinstance(default, list):
            return value.split(',')
        elif isinstance(default, dict):
            # For dictionaries, we don't support conversion from string
            # They should be accessed directly from defaults
            return default
        else:
            return value

    def create_default_config_file(self):
        """
        Create a default configuration file.
        """
        for section, options in self._defaults.items():
            if not self._config.has_section(section):
                self._config.add_section(section)

            for key, value in options.items():
                if isinstance(value, dict):
                    # Skip dictionaries, they're handled specially
                    continue

                if not self._config.has_option(section, key):
                    self._config.set(section, key, str(value))

        with open(CONFIG_FILE_PATH, 'w') as config_file:
            self._config.write(config_file)

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set configuration value and update config.ini file.

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        # Ensure section exists
        if not self._config.has_section(section):
            self._config.add_section(section)

        # Set value in config
        self._config.set(section, key, str(value))

        # Write to config file
        with open(CONFIG_FILE_PATH, 'w') as config_file:
            self._config.write(config_file)


# Create a singleton instance
_config_manager = ConfigManager()


# Function to get configuration value
def get_config(section: str, key: str) -> Any:
    """
    Get configuration value.

    Args:
        section: Configuration section
        key: Configuration key

    Returns:
        Configuration value
    """
    return _config_manager.get(section, key)


# Function to set configuration value
def set_config(section: str, key: str, value: Any) -> None:
    """
    Set configuration value and update config.ini file.

    Args:
        section: Configuration section
        key: Configuration key
        value: Value to set
    """
    # Set value in config manager
    _config_manager.set(section, key, value)

    # Update module attribute if it exists
    module_attr_name = key
    if section != SECTION_GENERAL:
        module_attr_name = f"{section.lower()}__{key}"

    if module_attr_name in globals():
        globals()[module_attr_name] = value


def general_config(patch: Dict = None) -> ClassDict:
    config = {
        "blender_executable": get_config(SECTION_GENERAL, "blender_executable"),
        "ffmpeg_executable": get_config(SECTION_GENERAL, "ffmpeg_executable"),
        "print_errors": get_config(SECTION_GENERAL, "print_errors"),
        "print_blender_log": get_config(SECTION_GENERAL, "print_blender_log"),
    }
    if patch:
        config = {**config, **patch}
    return ClassDict.wrap(config)


def conversion_config(patch: Dict = None) -> ClassDict:
    config = {
        "multiprocess_processes_count": get_config(SECTION_CONVERSION, "multiprocess_processes_count"),
        "input_path": get_config(SECTION_CONVERSION, "input_path"),
        "output_path": get_config(SECTION_CONVERSION, "output_path"),
        "images__save_images_only": get_config(SECTION_CONVERSION, "images__save_images_only"),
        "maps__save_as_chunked": get_config(SECTION_CONVERSION, "maps__save_as_chunked"),
        "maps__save_invisible_wall_collisions": get_config(SECTION_CONVERSION, "maps__save_invisible_wall_collisions"),
        "maps__save_terrain_collisions": get_config(SECTION_CONVERSION, "maps__save_terrain_collisions"),
        "maps__save_spherical_skybox_texture": get_config(SECTION_CONVERSION, "maps__save_spherical_skybox_texture"),
        "maps__add_props_to_obj": get_config(SECTION_CONVERSION, "maps__add_props_to_obj"),
        "geometry__save_obj": get_config(SECTION_CONVERSION, "geometry__save_obj"),
        "geometry__save_blend": get_config(SECTION_CONVERSION, "geometry__save_blend"),
        "geometry__export_to_gg_web_engine": get_config(SECTION_CONVERSION, "geometry__export_to_gg_web_engine"),
    }
    if patch:
        config = {**config, **patch}
    return ClassDict.wrap(config)


# Create default config file if it doesn't exist
if not os.path.exists(CONFIG_FILE_PATH):
    _config_manager.create_default_config_file()
