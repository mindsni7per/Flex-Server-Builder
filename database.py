"""
Persistent storage abstraction layer for Flex Utilities JSON databases.
"""

import json
import os
import threading

_lock = threading.Lock()

CONFIG_FILE = "sniper_config.json"
CASES_FILE = "moderation_cases.json"
BACKUP_FILE = "server_backups.json"


def _read_json(filepath: str) -> dict:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return {}
    return {}


def _write_json(filepath: str, data: dict) -> bool:
    with _lock:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
            return False


# --- Configuration Database ---
def get_guild_config(guild_id: int) -> dict:
    data = _read_json(CONFIG_FILE)
    return data.get(str(guild_id), {})


def update_guild_config(guild_id: int, key: str, value) -> bool:
    data = _read_json(CONFIG_FILE)
    g_id = str(guild_id)
    if g_id not in data:
        data[g_id] = {}
    data[g_id][key] = value
    return _write_json(CONFIG_FILE, data)


# --- Moderation Case Database ---
def get_guild_cases(guild_id: int) -> list:
    data = _read_json(CASES_FILE)
    return data.get(str(guild_id), [])


def add_moderation_case(guild_id: int, case_data: dict) -> int:
    data = _read_json(CASES_FILE)
    g_id = str(guild_id)
    if g_id not in data:
        data[g_id] = []
    
    case_number = len(data[g_id]) + 1
    case_data["case_number"] = case_number
    data[g_id].append(case_data)
    _write_json(CASES_FILE, data)
    return case_number


def void_moderation_case(guild_id: int, case_number: int, voided_by: str, reason: str) -> bool:
    data = _read_json(CASES_FILE)
    g_id = str(guild_id)
    if g_id in data:
        for case in data[g_id]:
            if case.get("case_number") == case_number:
                case["status"] = "voided"
                case["voided_by"] = voided_by
                case["void_reason"] = reason
                return _write_json(CASES_FILE, data)
    return False
