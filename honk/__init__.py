from discord import Message, TextChannel, User, Webhook
from discord.ext import commands
from shared import configuration
import random

configuration.DEFAULTS.update({
    'honk_emoji': [],
    'honk_channel': 629101374147133460,
})

class Honk(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return
        if message.channel.id == configuration.get('honk_channel') and message.content in ['Y', '�']:
            await self.honk(message.channel)
            

    async def honk(self, channel):
        emojis = configuration.get('honk_emoji')
        if not emojis:
            return
        chosen = random.choice(emojis)    
        emoji = await self.bot.get_cog('SelfGuild').get_emoji(chosen)
        await channel.send(str(emoji))

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Honk(bot))
