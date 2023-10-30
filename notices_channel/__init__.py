from interactions import Client, GuildText, Member, User, Webhook
from interactions import Extension, listen
from interactions.api.events import MessageCreate


class Owo(Extension):
    @listen()
    async def on_message(self, e: MessageCreate) -> None:
        message = e.message
        if message.author.bot:
            return
        if message.channel.id == 648850150046826497:
            await impersonate(
                message.author, message.channel, translate_furry(message.content)
            )
            await message.delete()


def translate_furry(input: str) -> str:
    return (
        input.lower()
        .replace("r", "w")
        .replace("l", "w")
        .replace(",", "~")
        .replace(";", "~")
        .replace("!", " owo!")
        .replace("?", " uwu?")
    )


async def get_webhook(channel: GuildText) -> Webhook:
    for wh in await channel.webhooks():
        return wh
    return await channel.create_webhook(name="Proxy")


async def impersonate(user: User | Member, channel: GuildText, content: str) -> None:
    hook = await get_webhook(channel)
    await hook.send(
        content, username=user.display_name, avatar_url=str(user.avatar_url)
    )


def setup(bot: Client) -> None:
    Owo(bot)
