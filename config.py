import configparser
import os
import re
from typing import Any, Dict, List, Optional

from library.utils.class_dict import ClassDict

# Define configuration sections
SECTION_GENERAL = 'General'
SECTION_CONVERSION = 'Conversion'
# A user-defined conversion preset lives in its own section "[Conversion: <name>]" and holds the conversion settings
# with the input / output paths. "No preset" (the default one) is [Conversion] itself, which also keeps the preset
# selected in the GUI converter.
CONVERSION_PRESET_SECTION_PREFIX = 'Conversion: '
# [Conversion] keys that are not conversion settings, so presets don't have them
CONVERSION_NON_PRESET_KEYS = ('selected_preset',)
# Letters, digits, spaces, "-", "_" and ".", starting and ending with a letter or a digit: no quoting trouble in a
# shell besides the spaces (--preset "My Preset"), and a valid ini section name
CONVERSION_PRESET_NAME_PATTERN = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9 _.\-]*[A-Za-z0-9])?$')
CONVERSION_PRESET_NAME_MAX_LENGTH = 64
NO_PRESET_NAME = 'No preset'

# Define configuration file path
CONFIG_FILE_NAME = 'nfs-resources-converter-settings.ini'
CONFIG_FILE_PATH = os.path.join(os.path.expanduser('~'), CONFIG_FILE_NAME)

# Define log file path
LOG_FILE_NAME = 'nfs-resources-converter-logs.log'
LOG_FILE_PATH = os.path.join(os.path.expanduser('~'), LOG_FILE_NAME)


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
                'blender_executable': 'blender',
                'ffmpeg_executable': 'ffmpeg',
                'print_blender_log': False,
                'recent_files': [],
                'show_hidden_fields': False,
            },
            SECTION_CONVERSION: {
                'multiprocess_processes_count': 0,
                'input_path': '',
                'output_path': '',
                'images__save_image_positions': False,
                'images__save_palettes': False,
                'images__save_mipmaps': False,
                'images__save_embedded_palette': False,
                'images__save_texts': False,
                'maps__save_as_chunked': False,
                'maps__save_invisible_wall_collisions': False,
                'maps__save_terrain_collisions': False,
                'maps__save_spherical_skybox_texture': True,
                'maps__add_props_to_obj': True,
                'geometry__save_obj': True,
                'geometry__save_blend': True,
                'geometry__export_to_gg_web_engine': False,
                'selected_preset': '',
            },
        }

    def _defaults_section(self, section: str) -> str:
        if section.startswith(CONVERSION_PRESET_SECTION_PREFIX):
            return SECTION_CONVERSION
        return section

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
        return f'NFS_RESOURCES_CONVERTER_{section.upper()}_{key.upper()}'

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
        defaults_section = self._defaults_section(section)
        default = self._get_defaults().get(defaults_section, {}).get(key)
        # Check environment variable first (not for presets: their section names make no variable names)
        if defaults_section == section:
            env_var_name = self._get_env_var_name(section, key)
            env_value = os.environ.get(env_var_name)
            if env_value is not None:
                return self._convert_value(env_value, default)

        # Check config file
        try:
            if self._config.has_option(section, key):
                value = self._config.get(section, key)
                return self._convert_value(value, default)
        except configparser.NoSectionError, configparser.NoOptionError:
            pass

        # Check defaults
        if defaults_section in self._defaults and key in self._defaults[defaults_section]:
            return self._defaults[defaults_section][key]

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
            value = value.strip()
            # Tolerate the literal "[]" that older versions of this file could persist for an
            # empty list default (see create_default_config_file), so existing settings files
            # self-heal instead of surfacing a bogus single item.
            if value in ('', '[]'):
                return []
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
                    if isinstance(value, list):
                        # Store lists the same way `set()` does (comma-joined), so an empty list
                        # round-trips back to [] instead of the literal string "[]"
                        self._config.set(section, key, ','.join(value))
                    else:
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

        self._write()

    def _write(self):
        with open(CONFIG_FILE_PATH, 'w') as config_file:
            self._config.write(config_file)

    def sections(self) -> List[str]:
        return self._config.sections()

    def add_section(self, section: str, values: Dict[str, Any]) -> None:
        self._config.add_section(section)
        for key, value in values.items():
            self._config.set(section, key, str(value))
        self._write()

    def remove_section(self, section: str) -> None:
        self._config.remove_section(section)
        self._write()


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
        module_attr_name = f'{section.lower()}__{key}'

    if module_attr_name in globals():
        globals()[module_attr_name] = value


def general_config(patch: Dict = None) -> ClassDict:
    config = {
        'blender_executable': get_config(SECTION_GENERAL, 'blender_executable'),
        'ffmpeg_executable': get_config(SECTION_GENERAL, 'ffmpeg_executable'),
        'print_blender_log': get_config(SECTION_GENERAL, 'print_blender_log'),
        'recent_files': get_config(SECTION_GENERAL, 'recent_files'),
        'show_hidden_fields': get_config(SECTION_GENERAL, 'show_hidden_fields'),
    }
    if patch:
        config = {**config, **patch}
    return ClassDict.wrap(config)


def _conversion_preset_section(preset: str) -> str:
    return CONVERSION_PRESET_SECTION_PREFIX + preset


def list_conversion_presets() -> List[str]:
    """
    Names of the user-defined conversion presets, in settings file order.
    """
    return [
        section[len(CONVERSION_PRESET_SECTION_PREFIX) :]
        for section in _config_manager.sections()
        if section.startswith(CONVERSION_PRESET_SECTION_PREFIX)
    ]


def _require_conversion_preset(preset: str) -> str:
    if preset not in list_conversion_presets():
        available = ', '.join(f'"{x}"' for x in list_conversion_presets()) or 'none'
        raise ValueError(f'Conversion preset "{preset}" does not exist. Available presets: {available}')
    return _conversion_preset_section(preset)


def validate_conversion_preset_name(name: str) -> Optional[str]:
    """
    Check a name for a new conversion preset.

    Returns:
        The error message, or None if the name can be used
    """
    if not name:
        return 'Preset name is required'
    if len(name) > CONVERSION_PRESET_NAME_MAX_LENGTH:
        return f'Preset name must be at most {CONVERSION_PRESET_NAME_MAX_LENGTH} characters long'
    if not CONVERSION_PRESET_NAME_PATTERN.match(name):
        return (
            'Preset name can contain only letters, digits, spaces, "-", "_" and ".", '
            'and must start and end with a letter or a digit'
        )
    if name.lower() == NO_PRESET_NAME.lower():
        return f'"{NO_PRESET_NAME}" is reserved'
    if name.lower() in (x.lower() for x in list_conversion_presets()):
        return f'Preset "{name}" already exists'
    return None


def create_conversion_preset(name: str, copy_from: Optional[str] = None) -> None:
    """
    Create a conversion preset with the settings of another one.

    Args:
        name: New preset name
        copy_from: Preset to copy the settings from, None for the default settings (no preset)
    """
    error = validate_conversion_preset_name(name)
    if error:
        raise ValueError(error)
    values = conversion_preset_settings(copy_from)
    _config_manager.add_section(_conversion_preset_section(name), values)


def delete_conversion_preset(name: str) -> None:
    _config_manager.remove_section(_require_conversion_preset(name))
    if get_selected_conversion_preset() is None and get_config(SECTION_CONVERSION, 'selected_preset'):
        set_config(SECTION_CONVERSION, 'selected_preset', '')


def get_selected_conversion_preset() -> Optional[str]:
    """
    The preset selected in the GUI converter, None for no preset (or if the selected one no longer exists).
    """
    preset = get_config(SECTION_CONVERSION, 'selected_preset')
    return preset if preset in list_conversion_presets() else None


def set_selected_conversion_preset(preset: Optional[str]) -> None:
    if preset:
        _require_conversion_preset(preset)
    set_config(SECTION_CONVERSION, 'selected_preset', preset or '')


def conversion_preset_settings(preset: Optional[str] = None) -> Dict[str, Any]:
    """
    Conversion settings, with the input / output paths, of a preset.

    Args:
        preset: Preset name, None for the default settings ([Conversion] section). A preset misses no setting: the
            ones it has no value for take the built-in defaults, not the [Conversion] ones.
    """
    section = _require_conversion_preset(preset) if preset else SECTION_CONVERSION
    return {
        key: get_config(section, key)
        for key in _config_manager._get_defaults()[SECTION_CONVERSION]
        if key not in CONVERSION_NON_PRESET_KEYS
    }


def patch_conversion_preset_settings(values: Dict[str, Any], preset: Optional[str] = None) -> None:
    """
    Save conversion settings to a preset (None = default settings).
    """
    section = _require_conversion_preset(preset) if preset else SECTION_CONVERSION
    for key, value in values.items():
        if key in CONVERSION_NON_PRESET_KEYS:
            raise ValueError(f'"{key}" is not a conversion setting')
        set_config(section, key, value)


def conversion_config(patch: Dict = None, preset: Optional[str] = None) -> ClassDict:
    """
    Conversion settings with the input / output paths.

    Args:
        patch: Values overriding the stored ones
        preset: Conversion preset name, None for the default settings (no preset)
    """
    config = conversion_preset_settings(preset)
    if patch:
        config = {**config, **patch}
    return ClassDict.wrap(config)


# Whether this process is the very first run of the app (no settings file was found yet).
# Captured before the default config file gets created below, so it stays accurate for the
# rest of the process lifetime.
_IS_FIRST_RUN = not os.path.exists(CONFIG_FILE_PATH)


def is_first_run() -> bool:
    """
    Whether this is the first time the app has been run on this machine (no settings file existed
    yet at process startup).

    Returns:
        bool: True on the very first run only
    """
    return _IS_FIRST_RUN


# Create default config file if it doesn't exist. On this first run, try to auto-detect the
# blender/ffmpeg executable paths so the user doesn't have to configure them manually.
if _IS_FIRST_RUN:
    from library.utils.executable_detection import detect_blender_path, detect_ffmpeg_path

    detected_blender = detect_blender_path()
    if detected_blender:
        _config_manager._defaults[SECTION_GENERAL]['blender_executable'] = detected_blender

    detected_ffmpeg = detect_ffmpeg_path()
    if detected_ffmpeg:
        _config_manager._defaults[SECTION_GENERAL]['ffmpeg_executable'] = detected_ffmpeg

    _config_manager.create_default_config_file()
