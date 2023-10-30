from redis import asyncio as aioredis
import interactions

from shared import configuration


class Bot(interactions.Client):
    def __init__(self) -> None:
        super().__init__(
            intents=interactions.Intents.DEFAULT | interactions.Intents.MESSAGE_CONTENT,
            enable_emoji_cache=True,
        )
        super().load_extension(
            "interactions.ext.sentry",
            token="https://83766626d7a64c1084fd140390175ea5@sentry.io/1757452",
        )
        super().load_extension("roles.colour")
        # super().load_extension('discordbot.updater')
        # super().load_extension('discordbot.botguild')
        super().load_extension("notices_channel")
        super().load_extension("honk")
        # super().load_extension('spoilerchan.spoilers')

    def init(self) -> None:
        self.start(configuration.get("token"))

    async def on_ready(self) -> None:
        self.redis = await aioredis.create_redis_pool(
            "redis://localhost", minsize=5, maxsize=10
        )
        print(
            "Logged in as {username} ({id})".format(
                username=self.user.name, id=self.user.id
            )
        )
        print(
            "Connected to {0}".format(
                ", ".join([server.name for server in self.guilds])
            )
        )
        print("--------")


def init() -> None:
    client = Bot()
    client.init()


if __name__ == "__main__":
    init()
