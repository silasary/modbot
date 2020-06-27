import os
import discord
from discord.ext import commands
from shared import configuration

configuration.DEFAULTS.update({
    'selfguild': None
})

class SelfGuild(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_server(self) -> discord.Guild:
        for guild in self.bot.guilds:
            if guild.name == self.bot.user.name:
                configuration.write('selfguild', guild.id)
                return guild
        if configuration.get('selfguild') is None:
            guild = await self.bot.create_guild(self.bot.user.name)
            configuration.write('selfguild', guild.id)
            return guild
        return self.bot.get_guild(configuration.get('selfguild'))
        
    async def get_emoji(self, name: str) -> discord.Emoji:
        for emoji in self.bot.emojis:
            if emoji.name == name:
                return emoji
        path = os.path.join('emoji_images', name + '.png')
        if os.path.exists(path):
            guild = await self.get_server()
            print(f'Uploading {name} to {guild.name}')
            with open(path, 'rb') as f:
                emoji = await guild.create_custom_emoji(name=name, image=f.read())
            return emoji
        return None

def setup(bot: commands.Bot) -> None:
    bot.add_cog(SelfGuild(bot))