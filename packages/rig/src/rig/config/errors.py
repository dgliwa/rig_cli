class ConfigError(Exception):
    """Base for all config loading errors."""


class FileNotFoundError_(ConfigError):
    """Required config file is missing."""


class ParseError(ConfigError):
    """YAML could not be parsed."""


class ValidationError(ConfigError):
    """Config content fails validation."""


class MissingReferenceError(ValidationError):
    """A cross-reference (pedal, preset, scene) is broken."""
