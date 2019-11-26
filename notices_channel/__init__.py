from discord.ext import commands
from discord import Message, TextChannel, User, Webhook

class Owo(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return
        if message.channel.id == 648850150046826497:
            await impersonate(message.author, message.channel, translate_furry(message.content))
            await message.delete()

def translate_furry(input: str) -> str:
    return input.lower().replace('r', 'w').replace('l', 'w').replace(",","~").replace(";","~").replace('!', ' owo!').replace('?', ' uwu?')

async def get_webhook(channel: TextChannel) -> Webhook:
    for wh in await channel.webhooks():
        return wh
    return await channel.create_webhook(name='Proxy')

async def impersonate(user: User, channel: TextChannel, content: str) -> None:
    hook = await get_webhook(channel)
    await hook.send(content, username=user.name, avatar_url=str(user.avatar_url))

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Owo(bot))
