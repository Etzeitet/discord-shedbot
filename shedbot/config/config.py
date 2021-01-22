from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="SHEDBOT",
    settings_files=['settings.toml', '.secrets.toml'],
    environments=True
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load this files in the order.

# if __name__ == "__main__":
#     # if "SHEDBOT_TOKEN" in settings:
#     #     print(f"{settings.SHEDBOT_TOKEN=}")

#     # if "DYNACONF_TOKEN" in settings:
#     #     print(f"{settings.DYNACONF_TOKEN=}")

#     print(settings.dynaconf_namespace)
#     print(settings.env_for_dynaconf)
#     for k, v in settings.items():
#         if k.startswith("BOT"):
#             print(f"{k}: {v}")
