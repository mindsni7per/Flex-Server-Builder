import json
import os

CONFIG_FILE = "sniper_config.json"
BACKUP_FILE = "server_backups.json"


def load_data(filename: str) -> dict:
    """Load JSON data safely with fallback to an empty dict."""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return {}
    return {}


def save_data(filename: str, data: dict) -> bool:
    """Save JSON data to a file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")
        return False


def get_guild_config(guild_id: int) -> dict:
    """Retrieve settings for a specific guild."""
    config = load_data(CONFIG_FILE)
    return config.get(str(guild_id), {})


def update_guild_config(guild_id: int, key: str, value) -> dict:
    """Update a specific setting for a guild."""
    config = load_data(CONFIG_FILE)
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {}
    config[gid][key] = value
    save_data(CONFIG_FILE, config)
    return config[gid]
