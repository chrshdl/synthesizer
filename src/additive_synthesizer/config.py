import json
import os
from dataclasses import asdict, dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Optional

from .logger import Logger

LOGGER = Logger("config.py").get()


@dataclass
class Config:
    width: int = field(default=1280)
    height: int = field(default=720)
    brightness: int = 50
    presets: dict = field(default_factory=dict)
    master_volume: float = 0.5
    show_waveform: bool = False
    show_keys: int = 0

    @classmethod
    def parse_config(cls, path: Path) -> "Config":
        config: dict = {}
        LOGGER.debug(
            f"Config path {path} exists: {path.exists()} is file: {path.is_file()}"
        )
        if path.exists() and path.is_file():
            try:
                with open(path, "r") as f:
                    config = json.load(f)
            except (JSONDecodeError, OSError) as e:
                # handle empy or corrupt config.json
                LOGGER.warning(
                    f"Config file {path} is invalid or corrupted, using defaults.",
                    exc_info=e,
                )
                config = {}

        result = Config(**config)
        LOGGER.info(f"Config: {result}")

        if not path.exists() or not config:
            result.write_to_file(path)

        return result

    def write_to_file(self, path: Path) -> None:
        LOGGER.debug(f"Write config to {path}")
        config_dict = asdict(self)
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = path.with_suffix(path.suffix + ".tmp")

        # Write to temporary file
        with tmp_path.open("w") as f:
            json.dump(config_dict, f, indent=4)
            f.flush()
            os.fsync(f.fileno())

        # Atomically replace the original
        os.replace(tmp_path, path)


class ConfigManager:
    path = Path(
        os.environ.get(
            "SYNTHESIZER_CONFIG_PATH",
            Path.home() / ".config" / "synthesizer" / "config.json",
        )
    )
    _config: Optional[Config] = None

    @classmethod
    def set_path(cls, path: Path) -> None:
        cls.path = path

    @classmethod
    def get_config(cls) -> Config:
        if cls._config is None:
            cls._config = Config.parse_config(cls.path)
        return cls._config

    @classmethod
    def set_brightness_percent(cls, brightness: int) -> None:
        cfg = cls.get_config()
        cfg.brightness = int(brightness)
        cfg.write_to_file(cls.path)
