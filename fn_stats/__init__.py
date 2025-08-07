import json
import os
import aiohttp
from interactions import Client, CronTrigger, Extension, Task, listen


class FnStats(Extension):
    def __init__(self, bot: "Client"):
        self.bot = bot
        self.active_songs: list[dict] = []

    @listen()
    async def on_startup(self):
        """Initialize the extension on bot startup."""
        self.load_songs()
        self.fetch_stats.start()
        await self.fetch_stats()

    @Task.create(CronTrigger("0 * * * *"))
    async def fetch_stats(self):
        """Fetch and update the statistics."""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.nitestats.com/v1/epic/modes-smart") as response:
                data = await response.json()
                self.data = data
        # self.dump_stats(data)

        songs = []
        ae = data["channels"]["client-events"]["states"][0]["activeEvents"]
        for event in ae:
            if event["eventType"].startswith("PilgrimSong."):
                songs.append(event)
            if event["eventType"].startswith("Sparks.Spotlight."):
                songs.append(event)
        old_songs = set(song["eventType"] for song in self.active_songs)
        new_songs = set(song["eventType"] for song in songs)
        if old_songs != new_songs:
            print("New songs detected:", new_songs - old_songs)
            if self.bot.owner:
                await self.bot.owner.send(f"New songs detected: {', '.join(new_songs - old_songs)}")
            self.active_songs = songs
            self.save_songs()

    def load_songs(self):
        """Load active songs from disk"""
        if os.path.exists("festival_songs.json"):
            with open("festival_songs.json", "r") as f:
                self.active_songs = json.load(f)

    def save_songs(self):
        """Save active songs to disk"""
        blob = json.dumps(self.active_songs, indent=4)
        with open("festival_songs.json", "w") as f:
            f.write(blob)

    def dump_stats(self, data):
        """Save the fetched statistics to a file."""
        with open("fn_stats.json", "w") as f:
            json.dump(data, f, indent=4)
