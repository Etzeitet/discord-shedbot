################
Discord Shed Bot
################

The Shed Bot is a simple Discord Bot for managing user's availability for an
activity. Designed originall for allowing a group of friends to work out
who was available for online gaming.

Commands
########

tonight command
===============

``/tonight``

The base command for this bot. When run by itself it will show the current
availiability:

.. code-block::

    /tonight

    ShedBot: On tonight:

        Alice: ✅
        Bob: ✅
        Charlie: ❌

-----

``/tonight yes``

Set yourself as available tonight.

.. code-block::

    /tonight yes

    ShedBot: Hi Alice. You've set yourself as on tonight 😎

-----

``/tonight no``

Set yourself as unavailable tonight.

.. code-block::

    /tonight no

    ShedBot: Hi Bob. You have set yourself as **not** available tonight.

-----

``/tonight dunno``

Set yourself as undecided or waiting for confirmation.

.. code-block::

    /tonight dunno

    ShedBot: Hi Charlie. You dunno what you're doing tonight...

-----

``/tonight clear``

Clear your availability.

.. code-block::

    /tonight clear

    ShedBot: Hi Debbie. Availability cleared.

-----

``/tonight clearall``

This is an Admin command and clears availability for everyone.
Only Guild/Server owners can run this command.

.. code-block::

    /tonight clear

     ShedBot: Schedule has been cleared!

Installation
############

This Python-based bot can be run from anywhere that can communicate with the
Discord API. These instructions are for a Docker-based installation and assumes
you have Docker installed on your server.

*Note: For a standalone installation, you can checkout the* ``Dockerfile`` *for steps
on how to install.*

1. Clone this repo to your Docker server
2. ``cd`` to the root directory of this repo
3. Build the Docker image:

.. code-block:: bash

    docker build -t shedbot:latest .

4. Run the Docker container

.. code-block:: bash

    docker run -d --env SHEDBOT_BOT_TOKEN="s3cr3t" shedbot:latest

Configuration
#############

This bot can be configured either through Environment Variables or through
the ``settings.toml`` file. Configuration through Environment variables will
override any settings in the settings file.

=====================  =============================  ===================
Config Item            Environment Variable           Note
=====================  =============================  ===================
bot_token              SHEDBOT_BOT_TOKEN
bot_datastore_channel  SHEDBOT_BOT_DATASTORE_CHANNEL
bot_listen_channel     SHEDBOT_LISTEN_CHANNEL
bot_ignore_channel     SHEDBOT_IGNORE_CHANNEL         Not yet implemented
bot_admin_role         SHEDBOT_ADMIN_ROLE             Not yet implemented
=====================  =============================  ===================


``bot_token``

Required. The Discord bot token - visit Discord developer site for how to create a bot.

``bot_datastore_channel``

Defaults to ``bot-data``. Channel must exist prior to connecting the bot.

This is the channel where the bot stores it's data (in case of restarts).

``bot_listen_channel``

The channel(s) the bot will listen on for commands. Can be set to a single channel
or a list:

.. code-block:: toml

    # single channel
    bot_listen_channel = "general"

    # multiple channels
    bot_listen_channel = "['general', 'news']"

Leaving this option empty/unset or set to ``ALL`` will cause the bot to listen to all
channels it has access to.

Accepts single value (``my_channel``, ``ALL``, etc) or a list (``"['my_channel', 'another_channel']"``)

This is the channel(s) where the bot will listen for commands. If set to ``ALL``
the bot will respond to commands in all channels it can access in your Guild.

``bot_ignore_channel``

Not implemented, yet.

As with ``bot_listen_channel``, can accept single channel names
or lists. The bot will not respond to any commands from these channels.

Overrides ``bot_listen_channel``, so any channel listed there will be ignored if also
listed in this config item.

``bot_admin_role``

If you want others to use the Admin commands of this bot, specify
the role name that will allow access. The Guild Owner will always
be able to run Admin commands.

Not implemented, yet.

Environments
============

The configuration of this bot supports environments when using the ``settings.toml``
file. This allows multiple instances of this bot to share the same config file without
the need for redefining environment variables or rebuilding with a new config file.

To set up different environments, create a new block in the ``settings.toml`` file:

.. code-block:: toml

    [production]
    bot_listen_channel = "my_channel"
    bot_guild = "my guild"
    bot_token = "s3cr3t1"

    [development]
    bot_listen_channel = "my_dev_channel"
    bot_guild = "my dev guild"
    bot_token = "dev_s3cr3t"

For config items that don't need to change between environments, add the ``default`` block.

.. code-block:: toml

    [default]
    bot_listen_channel = "my_channel"

    [personal_server]
    bot_token = "1234"

    [work_server]
    bot_token = "abcde"

This would configure the bot to use a different token for each server but listen
on the same channel in both.

Note: Discord bots can join multiple servers/guilds using the same token. However,
it is useful if you want to run multiple instances of the bot (development and production versions
for example).
