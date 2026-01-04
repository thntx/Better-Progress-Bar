import json
import os

def _load_defaults():
    addon_dir = os.path.dirname(__file__)
    config_path = os.path.join(addon_dir, "config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

DEFAULT_CONFIG = _load_defaults()

def reload_defaults():
    global DEFAULT_CONFIG
    DEFAULT_CONFIG = _load_defaults()
    return DEFAULT_CONFIG

def get_config_val(config, default_config, *keys):
    """
    Helper to get a value from nested config with automatic fallback to default_config.
    Accepts multiple keys for nested lookup (e.g. get_config_val(conf, def_conf, "timer", "style", "color")).
    """
    curr_conf = config
    curr_def = default_config
    
    for key in keys:
        # Traverse config
        if isinstance(curr_conf, dict):
            curr_conf = curr_conf.get(key)
        elif isinstance(curr_conf, list) and isinstance(key, int):
            try:
                curr_conf = curr_conf[key]
            except IndexError:
                curr_conf = None
        else:
            curr_conf = None
            
        # Traverse default_config
        if isinstance(curr_def, dict):
            curr_def = curr_def.get(key)
        elif isinstance(curr_def, list) and isinstance(key, int):
            try:
                curr_def = curr_def[key]
            except IndexError:
                curr_def = None
        else:
            curr_def = None
            
    # Return config value if set, else fallback to default
    return curr_conf if curr_conf is not None else curr_def
