import aiohttp
from bs4 import BeautifulSoup
from interactions import Client, CronTrigger, Embed, Extension, OptionType, SlashContext, Task, listen, slash_command, slash_option
from interactions.models.discord.components import Button, TextDisplayComponent, SectionComponent
import feedparser
import shortuuid

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

    @slash_command("rss")
    async def rss(self, ctx: SlashContext) -> None:
        """RSS feed commands"""

    @rss.subcommand("add_feed")
    @slash_option("url", "The URL of the RSS feed", opt_type=OptionType.STRING, required=True)
    async def add_feed(self, ctx: SlashContext, url: str):
        """Subscribe to an RSS feed"""
        new_feed = {"url": url, "seen": [], "user": ctx.author.id}
        self.feeds.append(new_feed)
        self.save()
        await ctx.send("Feed added!", ephemeral=True)
        await self.check_feed(new_feed)

    @rss.subcommand("dashboard")
    async def dashboard(self, ctx: SlashContext):
        """Show the RSS feed dashboard"""
        components = []
        for feed in self.feeds:
            if not feed.get("shortuuid"):
                feed["shortuuid"] = shortuuid.uuid()
            text = f"""
                    ## {feed.get('title') or feed.get('url')}
                    """
            if feed.get("latest"):
                text += f"""
                        * Latest post: [{feed['latest']['title']}]({feed['latest'].get('url', feed['latest'].get('guid'))})
                        * Published: {feed['latest']['published']}
                        """

            components.append(SectionComponent(components=[TextDisplayComponent(text)], accessory=Button(label="Unsubscribe", style=1, custom_id=f"ru:{feed['shortuuid']}")))
        for msg in chunk(components, 40 // 3):
            await ctx.send(components=msg, ephemeral=True)

    def save(self):
        dump = json.dumps(self.feeds, indent=2)
        with open("feeds.json", "w") as f:
            f.write(dump)

    @Task.create(CronTrigger("0 * * * *"))
    async def fetch_feeds(self):
        count = 0
        for feed in self.feeds:
            count = count + await self.check_feed(feed)
            if count >= 10:
                break
        if count > 0:
            self.save()

    async def check_feed(self, feed: dict) -> int:
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
        feed["title"] = rss.feed.title
        if "image" in rss.feed:
            feed["image"] = rss.feed.image.href
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
                published = item.get("published", rss.feed.get("updated"))
                feed["latest"] = {"guid": guid, "title": item.title, "published": published, "url": item.links[0].href}
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
                if solver.url and solver.url not in seen:
                    seen.append(solver.url)
                if len(seen) > len(items) * 4:
                    seen.pop(0)
                count += 1
                if count >= 10:
                    break
            except Exception as e:
                print(e)
                sentry_sdk.capture_exception(e)
        return count

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


def chunk(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
