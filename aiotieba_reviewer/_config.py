from aiotieba._config import CONFIG

required_keys = ['Database']
for required_key in required_keys:
    if required_key not in CONFIG or not isinstance(CONFIG[required_key], dict):
        CONFIG[required_key] = {}
