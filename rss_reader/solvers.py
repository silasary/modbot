import aiohttp
from bs4 import BeautifulSoup
from feedparser import FeedParserDict


class DefaultSolver:
    def __init__(self, feed: dict, channel: FeedParserDict) -> None:
        self.feed = feed
        self.channel = channel
        feed["generator"] = getattr(channel, "generator", "")

    async def solve(self, item: FeedParserDict) -> str:
        if self.feed["generator"] and self.feed["generator"].startswith("https://wordpress.org/"):
            self.feed["solver"] = "WordpressSolver"
        elif self.channel.link.startswith("https://www.comic-rocket.com/feeds/"):
            self.feed["solver"] = "ComicRocketSolver"

        if self.feed["solver"] != "DefaultSolver":
            solver_class = globals()[self.feed["solver"]]
            solver_instance = solver_class(self.feed, self.channel)
            return await solver_instance.solve(item)

        return f"New post in {self.channel_title}: {item.title} - {item.links[0].href}"

    @property
    def channel_title(self):
        return self.channel.title

    async def fetch_link(self, item: FeedParserDict) -> str:
        url = item.links[0].href
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.text()
        return data


class WordpressSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str:
        content = await self.fetch_link(item)
        soup = BeautifulSoup(content, "html.parser")
        post = soup.find("div", class_="entry-content")
        image = post.find("img")
        if image:
            image = image["src"]
            return f"New post in {self.channel_title}: {item.title} - {image}"
        return f"New post in {self.channel_title}: {item.title} - {item.links[0].href}"


class ComicRocketSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str:
        content = await self.fetch_link(item)
        soup = BeautifulSoup(content, "html.parser")
        body = soup.find("div", id="serialpagebody")
        iframe = body.find("iframe")
        url = iframe["src"]

        return f"New post in {self.channel_title}: {item.title} - {url}"
