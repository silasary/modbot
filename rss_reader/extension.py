import aiohttp
from interactions import Client, CronTrigger, Extension, OptionType, SlashContext, Task, listen, slash_command, slash_option
import feedparser

import json
import os

from rss_reader.solvers import create_solver


class RssReader(Extension):
    def __init__(self, bot: Client):
        self.feeds = []
        if os.path.exists("feeds.json"):
            with open("feeds.json", "r") as f:
                self.feeds = json.load(f)

    @listen()
    async def on_startup(self):
        self.fetch_feeds.start()
        await self.fetch_feeds()

    @slash_command("add_feed")
    @slash_option("url", "The URL of the RSS feed", opt_type=OptionType.STRING, required=True)
    async def add_feed(self, ctx: SlashContext, url: str):
        """Subscribe to an RSS feed"""
        new_feed = {"url": url, "seen": [], "user": ctx.author.id}
        self.feeds.append(new_feed)
        self.save()
        await ctx.send("Feed added!", ephemeral=True)
        await self.check_feed(new_feed)

    def save(self):
        dump = json.dumps(self.feeds, indent=2)
        with open("feeds.json", "w") as f:
            f.write(dump)

    @Task.create(CronTrigger("0 * * * *"))
    async def fetch_feeds(self):
        updated = False
        for feed in self.feeds:
            updated = await self.check_feed(feed) or updated
        if updated:
            self.save()

    async def check_feed(self, feed: dict) -> bool:
        updated = False
        url = feed["url"]
        user = await self.bot.fetch_user(feed["user"])
        seen = feed["seen"]
        if user is None:
            return False
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.text()

        rss = feedparser.parse(data)
        solver = create_solver(feed, rss.feed, rss.entries)

        items = rss.entries
        if hasattr(items[0], "published_parsed"):
            items.sort(key=lambda x: x.published_parsed, reverse=False)
        else:
            # We want oldest first, and feeds are usually newest first
            items.reverse()
        count = 0
        for item in items:
            if item.guid in seen:
                continue
            content = await solver.solve(item)
            await user.send(content)
            seen.append(item.guid)
            if len(seen) > 50:
                seen.pop(0)
            count += 1
            updated = True
            if count > 2:
                break
        return updated
