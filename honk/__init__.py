from interactions import Client, Extension, listen
from interactions.client.utils import get
from interactions.api.events import MessageCreate
from shared import configuration
import random

configuration.DEFAULTS.update(
    {
        "honk_emoji": [],
        "honk_channel": 629101374147133460,
    }
)


class Honk(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot

    @listen()
    async def on_message(self, e: MessageCreate) -> None:
        if e.message.author.bot:
            return
        if e.message.channel.id == configuration.get(
            "honk_channel"
        ) and e.message.content in ["Y", "�"]:
            await self.honk(e.message.channel)

    async def honk(self, channel):
        emojis = configuration.get("honk_emoji")
        if not emojis:
            return
        chosen = random.choice(emojis)
        if not self.bot.cache.emoji_cache:
            for guild in self.bot.guilds:
                await guild.fetch_all_custom_emojis()
        emoji = get(self.bot.cache.emoji_cache.values(), name=chosen)
        await channel.send(str(emoji))


def setup(bot: Client) -> None:
    Honk(bot)
