"""
tool_list.py - Multiple master list support
Each list is a JSON file in lib/lists/
Active list tracked in lib/config.json
"""
import json
import os

_LIB_DIR = os.path.dirname(os.path.realpath(__file__))
_LISTS_DIR = os.path.join(_LIB_DIR, 'lists')
_CONFIG_PATH = os.path.join(_LIB_DIR, 'config.json')


def _ensure_lists_dir():
    if not os.path.exists(_LISTS_DIR):
        os.makedirs(_LISTS_DIR)


def _normalize(description: str) -> str:
    return ' '.join(description.lower().split())


# ── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not os.path.exists(_CONFIG_PATH):
        return {'activeList': 'shopToolList.json'}
    with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict):
    with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_active_list_name() -> str:
    return load_config().get('activeList', 'shopToolList.json')


def set_active_list_name(filename: str):
    config = load_config()
    config['activeList'] = filename
    save_config(config)


# ── List file operations ──────────────────────────────────────────────────────

def list_all() -> list:
    _ensure_lists_dir()
    return sorted(f for f in os.listdir(_LISTS_DIR) if f.endswith('.json'))


def list_path(filename: str) -> str:
    return os.path.join(_LISTS_DIR, filename)


def active_list_path() -> str:
    _ensure_lists_dir()
    return list_path(get_active_list_name())


def load(filename: str = None) -> list:
    _ensure_lists_dir()
    path = list_path(filename) if filename else active_list_path()
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save(tool_list: list, filename: str = None):
    _ensure_lists_dir()
    path = list_path(filename) if filename else active_list_path()

    def sort_key(item):
        try:
            return (0, int(item.get('toolNumber', 0)))
        except (TypeError, ValueError):
            return (1, 0)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorted(tool_list, key=sort_key), f, indent=2)


def create_list(filename: str) -> bool:
    _ensure_lists_dir()
    path = list_path(filename)
    if os.path.exists(path):
        return False
    with open(path, 'w', encoding='utf-8') as f:
        json.dump([], f, indent=2)
    return True


def delete_list(filename: str) -> bool:
    path = list_path(filename)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


def rename_list(old_filename: str, new_filename: str) -> bool:
    old_path = list_path(old_filename)
    new_path = list_path(new_filename)
    if not os.path.exists(old_path) or os.path.exists(new_path):
        return False
    os.rename(old_path, new_path)
    if get_active_list_name() == old_filename:
        set_active_list_name(new_filename)
    return True


# ── Matching helpers ──────────────────────────────────────────────────────────

def build_lookup(tool_list: list) -> dict:
    lookup = {}
    for item in tool_list:
        desc = item.get('description', '')
        num = item.get('toolNumber')
        if desc and num is not None:
            try:
                lookup[_normalize(desc)] = int(num)
            except (TypeError, ValueError):
                pass
    return lookup


def sync_missing(tool_list: list, new_descriptions: list) -> list:
    existing = {_normalize(i.get('description', '')) for i in tool_list}
    result = list(tool_list)
    for desc in new_descriptions:
        if _normalize(desc) not in existing:
            result.append({'description': desc, 'toolNumber': 0})
            existing.add(_normalize(desc))
    return result


def merge_into(base: list, incoming: list) -> tuple:
    """Merge incoming into base. Returns (merged, added_count, updated_count)."""
    index = {_normalize(i['description']): idx for idx, i in enumerate(base)}
    result = list(base)
    added = updated = 0
    for item in incoming:
        key = _normalize(item.get('description', ''))
        if not key:
            continue
        new_num = item.get('toolNumber', 0)
        if key in index:
            if new_num and new_num != result[index[key]].get('toolNumber'):
                result[index[key]]['toolNumber'] = new_num
                updated += 1
        else:
            result.append({'description': item['description'], 'toolNumber': new_num})
            index[key] = len(result) - 1
            added += 1
    return result, added, updated


def normalize(description: str) -> str:
    return _normalize(description)
