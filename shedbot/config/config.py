from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="SHEDBOT",
    settings_files=['settings.toml'],
    environments=True,
    load_dotenv=True
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

if "BOT_TOKEN_FILE" in settings:
    with open(settings.bot_token_file, "r") as f:
        token = f.readline().strip()

    settings.bot_token = token
