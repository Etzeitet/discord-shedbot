import json
import logging
import re
from json.decoder import JSONDecodeError
from typing import Dict, Union

import discord
from discord.ext import commands, tasks
from dynaconf import LazySettings
from pendulum import Date, DateTime, Duration, Time, now, parse, today
from pendulum.parsing.exceptions import ParserError

from shedbot.config.config import settings

log = logging.getLogger("shedbot.schedule-cog")
log.setLevel(logging.DEBUG)

PendulumObject = Union[Date, Time, DateTime, Duration]
ScheduleDict = Dict[discord.Member, Union[str, PendulumObject]]


def json_default(o):
    """
    Encoder for pendulum DateTime
    """
    if isinstance(o, DateTime):
        return str(o)
    else:
        return o


def json_object_hook(o):
    """
    Decoder for pendulum DateTime
    """
    d = {}
    for k, v in o.items():
        if len(v) > 10:
            try:
                v = parse(v)
                log.debug(f"json_object_hook: {v}")
            except ParserError as e:
                log.exception(e)

        d[k] = v

    return d


def is_guild_owner(**perms):
    """
    Command Check for ensuring current user is the Guild/Server
    owner. Useful for protecting admin functions of the bot.

    Used as a decorator for commands.
    """

    def predicate(ctx):
        if ctx.guild is None:
            return False
        return ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)


def is_owner_or_admin_role(**perms):
    role = settings.bot_admin_role
    original = commands.has_role(role).predicate

    async def extended_check(ctx):
        if ctx.guild is None:
            return False

        return ctx.guild.owner_id == ctx.author.id or await original(ctx)

    return commands.check(extended_check)


def is_tonight_channel(**perms):
    """
    Command Check for ensuring commands are being run in the
    correct channel. This is to help keep spam to a minimum
    and restricted to one place.

    Used as a decorator for commands.
    """

    def predicate(ctx):
        return ctx.channel.name == settings.bot_listen_channel

    return commands.check(predicate)


def is_in_listen_channels(**perms):
    """
    Command Check for ensuring the bot only responds to commands
    in the specified channels.

    Used as a decorator for commands.
    """

    def predicate(ctx):
        channels = settings.bot_listen_channel
        return channels == "ALL" or ctx.channel.name in channels

    return commands.check(predicate)


class Schedule(commands.Cog):
    """
    Cog class for Schedule functions of ShedBot.

    Handles the following commands:

    /tonight:
        Main command. If run without subcommand will display schedule.

    /tonight yes:
        Sets current user to available

    /tonight no:
        Sets current user to unavailable

    /tonight clear
        Clears current user from schedule

    /tonight clearall
        Clears all users from schedule. This is an Admin command.
    """

    def __init__(self, bot: commands.Bot, settings: LazySettings):
        log.debug("Initialising Schedule Cog")

        self.bot = bot
        self.schedule: ScheduleDict = {}

        self.settings = settings
        self.default_start = parse(self.settings.bot_default_start)
        self.last_day = today()

        self.time_pattern = re.compile(r"^\d\d(:?)\d\d$")

        self.guild: discord.Guild = None
        self.datastore_channel = None
        self.listen_channel = None
        self.schedule_manager.start()

    @commands.Cog.listener()
    async def on_ready(self):
        log.debug("on_ready event")
        log.debug(f"{self.bot.guilds[0].name}")
        log.debug(f"{self.settings.bot_guild}")
        self.guild = discord.utils.get(self.bot.guilds, name=self.settings.bot_guild)
        self.datastore_channel = discord.utils.get(
            self.guild.channels, name=self.settings.bot_datastore_channel
        )
        self.listen_channel = discord.utils.get(
            self.guild.channels, name=self.settings.bot_listen_channel
        )

        log.debug(f"on_ready event: {self.datastore_channel=}")
        log.debug(f"on_ready event: {self.listen_channel=}")
        log.debug(f"on_ready event: {self.guild=}")

        await self.load_schedule()

    def format_schedule(self):
        """
        Formats the shedule and returns string ready for sending
        to channel.

        This function will use the user's Nickname if set, otherwise
        just their name.
        """
        online_icons = {"yes": "✅", "no": "❌", "dunno": "❓"}
        members_online = 0

        if not self.schedule:
            return "No one appears to be on tonight! :("

        message = "\n\n```"
        for member, online in self.schedule.items():
            log.debug(f"{member=}")

            if member:
                name = member.display_name

                if isinstance(online, DateTime):
                    start_time = online.format("HH:mm")
                    status = f"{online_icons['yes']} ({start_time})"
                    members_online += 1
                else:
                    icon = online_icons.get(online, online_icons["dunno"])
                    status = icon

                message += f"{name+':':<15} {status}\n"

        if members_online >= 2:
            start_status = f"Starting at {self.get_start_time().format('HH:mm')}"
        else:
            start_status = "Sorry, looks like you're on your own tonight! 💩"

        message = f"{message}\n\n{start_status}"
        return f"{message}\n```"

    def get_start_time(self):
        """
        Gets the earliest start time all members are available
        based on their status. If a start time is not set (i.e.,
        the user didn't use /tonight at <time>)

        Returns
        =======
        pendulum.DateTime of earliest suitable start time.
        """
        start = today()
        default_start = self.default_start

        for _, status in self.schedule.items():
            if status not in ["no", "dunno"]:
                if status == "yes":
                    status = default_start

                if status > start:
                    start = status

        return start

    def to_json(self, data):
        """
        Serialises the schedule to a JSON string.

        The Member instances that make up the keys are
        not suitable for serialising, so the key is replaced
        by the Member or User ID.

        Args
        ====
        data:
            dict, the schedule (single level dict of <member>: <status> key values)

        Returns
        =======
            JSON formatted string
        """
        log.debug(f"serialising to JSON: {data}")
        schedule = {k.id: v for k, v in data.items()}

        try:
            text = json.dumps(schedule, default=json_default)
        except (TypeError, OverflowError):
            text = None

        log.debug(f"JSON: {text}")
        return text

    def from_json(self, text):
        """
        Deserialises a schedule from a JSON string.

        After converting the JSON back into a Python object
        (a dict, specifically), this method replaces the
        integer keys with full Member objects from the cache.

        Args
        ====

        text:
            str, JSON formatted string

        Returns
        =======
            dict
        """
        log.debug(f"deserialising from JSON: {text}")

        try:
            data = self.hydrate_members(json.loads(text, object_hook=json_object_hook))
        except JSONDecodeError:
            data = None

        log.debug(f"data: {data}")

        return data

    def hydrate_members(self, data):
        """
        Takes a dictionary of member IDs as keys and
        converts them to full member objects.

        Used by the from_dict() method.

        Args
        ====
        data:
            A dict of member IDs as keys (str or int)

        Returns
        =======
            A dict of members and status
        """
        log.debug("Hydrating!")

        return {self.guild.get_member(int(k)): v for k, v in data.items()}

    async def store_schedule(self):
        """
        Takes the current schedule and stores it within a Guild/Server
        channel as a JSON string.

        Since messages are all text-based, it is a fairly simple way to
        store state of the Bot within the Server itself.
        """
        log.info(f"Storing schedule to channel {self.datastore_channel}")
        text = self.to_json(self.schedule)
        await self.datastore_channel.send(text)

    async def load_schedule(self):
        """
        Loads a schedule saved within a Guild/Server channel.

        This method will grab the latest message from a specific channel and
        load the JSON object back into a schedule. If there are no messages
        or it is not valid JSON, the schedule is not updated.

        TODO: Ignore last message if from previous day

        Returns
        =======
        A dictionary representing the schedule.
        """
        log.info(f"Loading schedule from channel {self.datastore_channel}")

        messages = await self.datastore_channel.history(limit=1).flatten()
        log.debug(f"Messages found in {self.datastore_channel}")

        if messages:
            content = messages[0].content
            log.debug(f"Message content: {content}")

            if data := self.from_json(content):
                self.schedule = data

    async def update_schedule(
        self, member: discord.Member, value: Union[str, PendulumObject]
    ) -> None:
        """
        Update the schedule and store in Guild/Server.

        Args
        ====
        member:
            Member or User instance, the user to be updated

        value:
            The value to assign to the user. Any str or DateTime. If
            value is CLEAR, removes member from schedule.
        """
        log.debug(f"update_schedule: {member.name} set to {value}")

        if value == "CLEAR":
            del self.schedule[member]
        else:
            self.schedule[member] = value

        await self.store_schedule()

    async def clear_schedule(self):
        """
        Clears the schedule and store in Guild/Server.
        """
        log.info("Clearing schedule")
        self.schedule = {}
        await self.store_schedule()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send(f"Welcome {member.mention}")

    @commands.group(invoke_without_command=False, aliases=["to"])
    @is_in_listen_channels()
    async def tonight(self, ctx: commands.Context):
        """
        The tonight command.

        If invoked by itself, will show a list of users'
        status for this evening.
        """
        log.debug(f"tonight: {ctx.invoked_subcommand=}")
        log.debug(f"tonight: {ctx.subcommand_passed=}")

        if not ctx.invoked_subcommand:

            if ctx.subcommand_passed and self.time_pattern.search(
                ctx.subcommand_passed
            ):
                await self.at(ctx, ctx.subcommand_passed)

            else:
                await ctx.send(self.format_schedule())

    @tonight.command(hidden=True)
    @is_owner_or_admin_role()
    @is_in_listen_channels()
    async def clearall(self, ctx):
        await self.clear_schedule()
        await ctx.send("Schedule has been cleared!")

    @tonight.command(aliases=["yep", "y", "ok"])
    @is_in_listen_channels()
    async def yes(self, ctx):
        """
        Sets your status as being online tonight.

        Updates the schedule for invoking member to say they
        are available. This is just a convenience function for
        at(). It sets the start time to the default value in
        the config.
        """
        await self.at(ctx, self.settings.bot_default_start)

    @tonight.command()
    @is_in_listen_channels()
    async def at(self, ctx, time: str):
        if len(time) == 4 and time.isnumeric:
            time = f"{time[:2]}:{time[-2:]}"

        start_time = parse(time)
        member = self.guild.get_member(ctx.author.id)
        await self.update_schedule(member, start_time)
        await ctx.send(
            (
                f"Hi {member.display_name}. "
                f"You've set yourself as on tonight at {time} :sunglasses:"
            )
        )

    @tonight.command(aliases=["nope", "n", "nah"])
    @is_in_listen_channels()
    async def no(self, ctx):
        """
        Sets your status as not being online tonight.

        Updates the schedule for invoking member to say they
        are not available.
        """
        member = self.guild.get_member(ctx.author.id)
        await self.update_schedule(member, "no")
        await ctx.send(
            f"Hi {member.display_name}. You've set yourself as **not** on tonight."
        )

    @tonight.command(aliases=["eh", "meh", "maybe"])
    @is_in_listen_channels()
    async def dunno(self, ctx):
        """
        Sets your status as dunno. You are undecided!

        Updates the schedule for invoking member to say they may or may not
        be available.
        """
        member = self.guild.get_member(ctx.author.id)
        await self.update_schedule(member, "dunno")
        await ctx.send(
            f"Hi {member.display_name}. You dunno what you're doing tonight..."
        )

    @tonight.command(aliases=["delete", "nuke"])
    @is_in_listen_channels()
    async def clear(self, ctx):
        """
        Clears any status.

        Updates the schedule for invoking member and clears availability.
        """
        member = self.guild.get_member(ctx.author.id)
        await self.update_schedule(member, "CLEAR")
        await ctx.send(f"Hi {member.display_name}. Availability cleared.")

    @tasks.loop(seconds=60)
    async def schedule_manager(self):
        _now = now(tz="Europe/London")

        log.debug(f"now: {_now}")
        log.debug(f"clear: {self.last_day}")

        if _now.day != self.last_day:
            log.info("schedule_manager: end of day clearing")
            await self.clear_schedule()
            self.last_day = _now.day
        else:
            log.info("schedule_manager: nothing to do")

    @schedule_manager.before_loop
    async def before_printer(self):
        print("waiting for bot")
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Schedule(bot, settings))
