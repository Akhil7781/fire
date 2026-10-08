"""
Secure configuration management for FIRMS thermal anomaly research project.

CRITICAL SECURITY RULES:
- FIRMS_MAP_KEY must NEVER be hard-coded.
- FIRMS_MAP_KEY must NEVER be logged or printed to stdout/stderr.
- FIRMS_MAP_KEY must NEVER be written to disk in plain text outside the user's .env.
- Config string representations must mask all sensitive fields.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _load_env_file(env_path: Path) -> None:
    """
    Minimal standalone .env loader that does not require third-party libraries.
    If python-dotenv is installed, it can be used, but this ensures functionality
    even before requirements are installed.
    """
    if not env_path.is_file():
        return

    try:
        # If python-dotenv is available, prefer it
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=env_path, override=False)
        return
    except ImportError:
        pass

    # Fallback line-by-line parser
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Do not overwrite existing environment variables
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        # Fail silently on environment parsing to avoid leakage
        pass


# Automatically load from project root .env if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_load_env_file(PROJECT_ROOT / ".env")


def get_firms_map_key() -> str:
    """
    Securely retrieves the NASA FIRMS MAP_KEY from the environment.
    
    Returns:
        str: The FIRMS MAP_KEY.
        
    Raises:
        ValueError: If the key is not set or empty. (Value is never printed)
    """
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key or key == "your_firms_map_key_here":
        raise ValueError(
            "FIRMS_MAP_KEY is not configured or is set to placeholder. "
            "Please set FIRMS_MAP_KEY in your local .env file or environment."
        )
    return key


def is_firms_map_key_set() -> bool:
    """
    Checks if FIRMS_MAP_KEY is present and non-empty, without exposing the key value.
    
    Returns:
        bool: True if key exists and is non-empty, False otherwise.
    """
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    return bool(key and key != "your_firms_map_key_here")


@dataclass
class Config:
    """
    Project path and environment configuration.
    Sensitive credentials are never exposed in string representations.
    """
    project_root: Path = PROJECT_ROOT
    raw_data_dir: Path = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    raw_context_dir: Path = Path(os.getenv("RAW_CONTEXT_DIR", "data/raw_context"))
    interim_data_dir: Path = Path(os.getenv("INTERIM_DATA_DIR", "data/interim"))
    processed_data_dir: Path = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
    checkpoint_dir: Path = Path(os.getenv("CHECKPOINT_DIR", "checkpoints"))
    log_dir: Path = Path(os.getenv("LOG_DIR", "logs"))
    random_seed: int = int(os.getenv("RANDOM_SEED", "42"))

    def __post_init__(self) -> None:
        # Resolve relative paths against project root
        if not self.raw_data_dir.is_absolute():
            self.raw_data_dir = (self.project_root / self.raw_data_dir).resolve()
        if not self.raw_context_dir.is_absolute():
            self.raw_context_dir = (self.project_root / self.raw_context_dir).resolve()
        if not self.interim_data_dir.is_absolute():
            self.interim_data_dir = (self.project_root / self.interim_data_dir).resolve()
        if not self.processed_data_dir.is_absolute():
            self.processed_data_dir = (self.project_root / self.processed_data_dir).resolve()
        if not self.checkpoint_dir.is_absolute():
            self.checkpoint_dir = (self.project_root / self.checkpoint_dir).resolve()
        if not self.log_dir.is_absolute():
            self.log_dir = (self.project_root / self.log_dir).resolve()

    def __repr__(self) -> str:
        """
        Sanitized representation preventing any credential leaks.
        """
        key_status = "[SET]" if is_firms_map_key_set() else "[NOT SET]"
        return (
            f"Config(\n"
            f"  project_root={self.project_root},\n"
            f"  raw_data_dir={self.raw_data_dir},\n"
            f"  raw_context_dir={self.raw_context_dir},\n"
            f"  interim_data_dir={self.interim_data_dir},\n"
            f"  processed_data_dir={self.processed_data_dir},\n"
            f"  checkpoint_dir={self.checkpoint_dir},\n"
            f"  log_dir={self.log_dir},\n"
            f"  random_seed={self.random_seed},\n"
            f"  firms_map_key={key_status}\n"
            f")"
        )


def get_config() -> Config:
    """Factory function to get instantiated project configuration."""
    return Config()
