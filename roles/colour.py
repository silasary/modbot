import hashlib
import os
import re
from typing import TYPE_CHECKING, List

import discord
import requests
from discord.ext import commands


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._last_result = None

    @commands.command(aliases=['setcolor'])
    async def setcolour(self, ctx: commands.Context, colour: discord.Color) -> None:
        await self.remove_colour(ctx.author)
        role = await self.get_or_create_colour_role(colour, ctx.guild)
        await ctx.author.add_roles(role)
        await ctx.send('Done!')

    @setcolour.error
    async def colour_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need to give me a color')
            return

        if isinstance(error, commands.UserInputError):
            await ctx.send("That's not a colour I recognise")
            return
        await ctx.send("An unknown error occured")

    async def remove_colour(self, member: discord.Member) -> None:
        for role in member.roles:
            if role.name.startswith('Colour: '):
                await member.remove_roles(role)
                if not role.members:
                    await role.delete()

    async def get_or_create_colour_role(self, colour: discord.Color, guild: discord.Guild) -> discord.Role:
        name = f'Colour: {str(colour)}'
        for role in guild.roles:
            if role.name == name:
                return role
        else:
            return await guild.create_role(name=name, colour=colour)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Roles(bot))
