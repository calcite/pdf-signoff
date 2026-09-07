"""Application configuration loading and validation boundary."""

import os
from importlib.resources import files
from pathlib import Path
from typing import Any

from onacol import ConfigManager, OnacolException  # type: ignore[import-untyped]

APP_CONFIG_DIRECTORY = "pdf-signoff"
CONFIG_FILE_NAME = "config.yaml"
# Onacol appends one underscore; retain the documented double-underscore prefix.
ENV_VAR_PREFIX = "PDF_SIGNOFF_"
DEFAULT_CONFIG_FILE = str(files("pdf_signoff").joinpath("default_config.yaml"))


class CliConfigArgumentError(OnacolException):
    """A forwarded Click argument is not a valid Onacol override."""


def discover_config_file(explicit_config: Path | None = None) -> Path | None:
    """Select an explicit config or the first discovered user config."""
    if explicit_config is not None:
        return explicit_config

    candidates: list[Path] = []
    if xdg_config_home := os.environ.get("XDG_CONFIG_HOME"):
        candidates.append(
            Path(os.path.expandvars(os.path.expanduser(xdg_config_home)))
            / APP_CONFIG_DIRECTORY
            / CONFIG_FILE_NAME
        )
    candidates.append(Path.home() / ".config" / APP_CONFIG_DIRECTORY / CONFIG_FILE_NAME)

    return next((candidate for candidate in candidates if candidate.is_file()), None)


def load_config(
    explicit_config: Path | None,
    cli_args: list[str],
) -> ConfigManager:
    """Load defaults, user YAML, environment, and CLI layers in precedence order."""
    user_config = discover_config_file(explicit_config)
    config_manager = ConfigManager(
        DEFAULT_CONFIG_FILE,
        env_var_prefix=ENV_VAR_PREFIX,
        optional_files=[str(user_config)] if user_config else [],
    )
    config_manager.config_from_env_vars()
    _validate_cli_args(config_manager, cli_args)
    config_manager.config_from_cli_args(cli_args)
    config_manager.validate()
    _expand_configured_paths(config_manager.config)
    return config_manager


def _validate_cli_args(config_manager: ConfigManager, cli_args: list[str]) -> None:
    """Require every forwarded argument to form a schema-backed option pair."""
    for token in cli_args:
        if not token.startswith("--"):
            continue
        try:
            config_manager.get_cli_opt_conf_value(token.lstrip("-"))
        except OnacolException as exc:
            raise CliConfigArgumentError(f"Unrecognized option: {token}") from exc

    for index in range(0, len(cli_args), 2):
        option = cli_args[index]
        if not option.startswith("--"):
            raise CliConfigArgumentError(f"Unrecognized argument: {option}")
        if index + 1 == len(cli_args) or cli_args[index + 1].startswith("--"):
            raise CliConfigArgumentError(
                f"Configuration option {option} requires a value."
            )


def _expand_configured_paths(config: Any) -> None:
    """Expand shell-style variables and the user home in configured paths."""
    pkcs12_path = config["l1"]["pkcs12_path"]
    if pkcs12_path:
        config["l1"]["pkcs12_path"] = os.path.expanduser(
            os.path.expandvars(pkcs12_path)
        )
