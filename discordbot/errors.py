import logging
import sys
import traceback

import sentry_sdk
import discord
from discord.ext import commands
from shared import configuration

configuration.DEFAULTS.update({
    'SENTRY_TOKEN': 'https://83766626d7a64c1084fd140390175ea5@sentry.io/1757452'
})

class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if hasattr(ctx.command, "on_error"):
            return  # Don't interfere with custom error handlers

        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return # Probably for another bot. We don't care

        sentry_sdk.capture_exception(error)

        if isinstance(error, commands.CommandError):
            return await ctx.send(f"Error executing command `{ctx.command.name}`: {str(error)}")

        await ctx.send(
            "An unexpected error occurred while running that command.")
        logging.warn("Ignoring exception in command {}:".format(ctx.command))
        logging.warn("\n" + "".join(
            traceback.format_exception(
                type(error), error, error.__traceback__)))

def setup(bot: commands.Bot) -> None:
    if configuration.get('SENTRY_TOKEN') is not None and (sentry_sdk.Hub.current is None or sentry_sdk.Hub.current.client is None):
        sentry_sdk.init(configuration.get('SENTRY_TOKEN'))
        with sentry_sdk.configure_scope() as scope:
            scope.user = {'username': str(bot.user)}
    bot.add_cog(CommandErrorHandler(bot))
