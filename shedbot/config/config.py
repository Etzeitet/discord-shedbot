from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="SHEDBOT",
    settings_files=['settings.toml', '.secrets.toml'],
    environments=True
)

# Some sane defaults (and to keep ENV or settings files to a minimum)
defaults = {
    "bot_default_start": "21:00",
    "bot_admin_role": "none",
    "bot_listen_channel": "ALL",
    "bot_datastore_channel": "bot-data"
}

for item, value in defaults.items():
    if item not in settings:
        settings[item] = value
