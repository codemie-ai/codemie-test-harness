# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import json
import os
from typing import Optional, Any
from .constants import CONFIG_DIR, CONFIG_FILE, KEY_ALIASES

# Variables set from .env, the secret store or the config file. The config file may
# still override these; only a variable that was already in the process environment
# when the harness started always wins.
OVERRIDABLE_KEYS: set[str] = set()


def canonical_key(key: str) -> str:
    """Current name of a setting; names used by earlier versions map through KEY_ALIASES."""
    return KEY_ALIASES.get(key, key)


def load_config() -> dict:
    """Saved settings, with old names renamed to the current ones (a current name wins)."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    cfg = {k: v for k, v in raw.items() if k not in KEY_ALIASES}
    for old, value in raw.items():
        if old in KEY_ALIASES:
            cfg.setdefault(KEY_ALIASES[old], value)
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    key = canonical_key(key)
    if key in os.environ:
        return os.environ[key]
    cfg = load_config()
    val = cfg.get(key)
    if val is None:
        return default
    return str(val)


def set_config_value(key: str, value: Any) -> None:
    key = canonical_key(key)
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    # Keep this process in step (interactive menu): an edit applies to the next run.
    if key in OVERRIDABLE_KEYS:
        os.environ[key] = str(value)


def ensure_env_from_config(keys: Optional[list[str]] = None) -> None:
    """
    Fill environment variables from the config file.
    Variables that were in the process environment at start win over config values.
    Variables that came from .env or the secret store (OVERRIDABLE_KEYS) do not:
    config wins over both.

    Args:
        keys: Optional list of specific keys to load. If None, loads all keys from config.
    """
    cfg = load_config()

    # If no specific keys provided, load all keys from config
    if keys is None:
        keys = list(cfg.keys())

    for k in keys:
        if k in cfg and (k not in os.environ or k in OVERRIDABLE_KEYS):
            os.environ[k] = str(cfg[k])
            OVERRIDABLE_KEYS.add(k)


def unset_config_key(key: str) -> bool:
    key = canonical_key(key)
    cfg = load_config()
    if key in cfg:
        del cfg[key]
        save_config(cfg)
        if key in OVERRIDABLE_KEYS:
            os.environ.pop(key, None)
            OVERRIDABLE_KEYS.discard(key)
        return True
    return False
