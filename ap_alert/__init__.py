import asyncio
import aiohttp
import datetime
import json
import os
import attrs
import cattrs
from bs4 import BeautifulSoup
from interactions import (
    Client,
    Extension,
    OptionType,
    SlashContext,
    User,
    listen,
    slash_option,
    slash_command,
)
from interactions.models.internal.tasks import Task, IntervalTrigger
import requests

session = aiohttp.ClientSession()

@attrs.define()
class TrackedGame:
    url: str  # /tracker/tracker_id/0/slot_id
    latest_item: int
    name: str = None
    game: str = None
    last_check: datetime.datetime = None
    last_update: datetime.datetime = None

    @property
    def tracker_id(self) -> str:
        return self.url.split("/")[2]

    @property
    def slot_id(self) -> str:
        return self.url.split("/")[4]

    def refresh(self) -> None:
        html = requests.get(self.url).content
        soup = BeautifulSoup(html, features="html.parser")
        recieved = soup.find(id="received-table")
        headers = [i.string for i in recieved.find_all("th")]
        rows = [
            [try_int(i.string) for i in r.find_all("td")]
            for r in recieved.find_all("tr")[1:]
        ]
        last_index = headers.index("Last Order Received")
        rows.sort(key=lambda r: r[last_index])
        if rows[-1][last_index] == self.latest_item:
            return []
        self.last_update = datetime.datetime.now()
        new_items = [r for r in rows if r[last_index] > self.latest_item]
        self.latest_item = rows[-1][last_index]
        return new_items

@attrs.define()
class Multiworld:
    url: str  # https://aptracker.chrishowie.com/api/tracker/room_id
    title: str = None
    games: dict[int, dict] = None
    last_check: datetime.datetime = None

    async def refresh(self) -> None:
        async with session.get(self.url) as response:
            data = await response.json()
            self.title = data.get("title")
            self.games = {g['position']: g for g in data.get("games")}

class APTracker(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot: Client = bot
        self.trackers: dict[int, list[TrackedGame]] = {}
        self.cheese: dict[str, Multiworld] = {}
        if os.path.exists("trackers.json"):
            with open("trackers.json") as f:
                self.trackers = cattrs.structure(
                    json.loads(f.read()), dict[int, list[TrackedGame]]
                )
        if os.path.exists("cheese.json"):
            with open("cheese.json") as f:
                self.cheese = cattrs.structure(
                    json.loads(f.read()), dict[str, Multiworld]
                )

    @listen()
    async def on_startup(self) -> None:
        self.refresh_all.start()
        self.refresh_all.trigger.last_call_time = (
            datetime.datetime.now() - datetime.timedelta(hours=1)
        )

    @slash_command("ap")
    async def ap(self, ctx: SlashContext) -> None:
        """Monitor for Archipelago games"""

    @ap.subcommand("track")
    @slash_option("url", "url", OptionType.STRING, required=True)
    async def ap_track(self, ctx: SlashContext, url: str) -> None:
        if ctx.author_id not in self.trackers:
            self.trackers[ctx.author_id] = []

        for t in self.trackers[ctx.author_id]:
            if t.url == url:
                tracker = t
                break
        else:
            tracker = TrackedGame(url, 0)
            self.trackers[ctx.author_id].append(tracker)
            self.save()

        new_items = tracker.refresh()
        names = [i[0] for i in new_items]
        await ctx.send(", ".join(names) or "No new items", ephemeral=False)

    @ap.subcommand("refresh")
    async def ap_refresh(self, ctx: SlashContext) -> None:
        if ctx.author_id not in self.trackers:
            await ctx.send(
                f"Track a game with {self.ap_track.mention()} first", ephemeral=True
            )
            return

        await ctx.defer()

        games = {}
        for tracker in self.trackers[ctx.author_id]:
            new_items = tracker.refresh()
            if new_items:
                games[tracker.url] = new_items

        if not games:
            await ctx.send("No new items", ephemeral=True)
            return

        for url, items in games.items():
            names = [i[0] for i in items]
            await ctx.send(f"{url}: {', '.join(names)}", ephemeral=False)

    @ap.subcommand("cheese")
    @slash_option("room", "room-id", OptionType.STRING, required=True)
    async def ap_cheese(self, ctx: SlashContext, room: str) -> None:
        multiworld = Multiworld(f"https://aptracker.chrishowie.com/api/tracker/{room}")
        await multiworld.refresh()
        self.cheese[room] = multiworld
        for game in multiworld.games.values():
            if game['effective_discord_username'] == ctx.author.username:
                game['url'] = f'https://archipelago.gg/tracker/{room}/0/{game["position"]}'
                for t in self.trackers[ctx.author_id]:
                    if t.url == game['url']:
                        tracker = t
                        break
                else:
                    tracker = TrackedGame(game['url'], 0)
                    self.trackers[ctx.author_id].append(tracker)
                    self.save()
                tracker.name = multiworld.title + f" - {game['name']}"
                tracker.game = game['game']

    @Task.create(IntervalTrigger(hours=1))
    async def refresh_all(self) -> None:
        for user, trackers in self.trackers.items():
            for tracker in trackers:
                new_items = tracker.refresh()
                if new_items:
                    names = [i[0] for i in new_items]
                    player = await self.bot.fetch_user(user)
                    if isinstance(player, User):
                        await player.send(f"{tracker.url}: {', '.join(names)}")
                    else:
                        print(f"{tracker.url}: {', '.join(names)}")
                await asyncio.sleep(120)

        self.save()

    def save(self):
        with open("trackers.json", "w") as f:
            f.write(json.dumps(cattrs.unstructure(self.trackers)))
        with open("cheese.json", "w") as f:
            f.write(json.dumps(cattrs.unstructure(self.cheese)))


def try_int(text: str) -> str | int:
    try:
        return int(text)
    except ValueError:
        return text
