import aiohttp
from bs4 import BeautifulSoup
from interactions import Client, CronTrigger, Embed, Extension, OptionType, SlashContext, Task, listen, slash_command, slash_option
import feedparser

import json
import os

import sentry_sdk

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
        if rss.bozo == 1:
            rss = await self.find_rss_feed(feed, rss)
        if rss.bozo:
            return False
        solver = create_solver(feed, rss.feed, rss.entries)

        items = rss.entries
        if hasattr(items[0], "published_parsed"):
            items.sort(key=lambda x: x.published_parsed, reverse=False)
        else:
            # We want oldest first, and feeds are usually newest first
            items.reverse()
        count = 0
        for item in items:
            try:
                guid = item.get("guid", item.get("id", item.get("link")))
                if guid in seen:
                    continue
                content = await solver.solve(item)
                if isinstance(content, str):
                    await user.send(content)
                elif isinstance(content, Embed):
                    await user.send(embed=content)
                elif isinstance(content, (list, tuple)):
                    body = None
                    embeds = []
                    for c in content:
                        if isinstance(c, str):
                            body = c
                        elif isinstance(c, Embed):
                            embeds.append(c)
                    await user.send(body, embeds=embeds)
                seen.append(guid)
                if len(seen) > len(items) * 2:
                    seen.pop(0)
                count += 1
                updated = True
                if count > 4:
                    break
            except Exception as e:
                print(e)
                sentry_sdk.capture_exception(e)
        return updated

    async def find_rss_feed(self, feed, rss):
        async with aiohttp.ClientSession() as session:
            async with session.get(feed["url"]) as resp:
                data = await resp.text()
        soup = BeautifulSoup(data, "html.parser")
        links = soup.find_all("link", type="application/rss+xml")
        if links:
            link = links[0]["href"]
            if link.startswith("//"):
                link = "https:" + link
            feed["url"] = link
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as resp:
                    data = await resp.text()
            return feedparser.parse(data)
        if feed["url"].startswith("https://mangadex.org/title/"):
            uuid = feed["url"].split("/")[4]
            link = f"https://mdrss.tijlvdb.me/feed?q=manga:{uuid},tl:en"
            feed["url"] = link
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as resp:
                    data = await resp.text()
            return feedparser.parse(data)
        return rss
