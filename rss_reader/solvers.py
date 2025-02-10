import aiohttp
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
import urllib.parse


def create_solver(feed: dict, channel: FeedParserDict, entries: list[FeedParserDict]) -> "DefaultSolver":
    if channel.get("generator") and channel["generator"].startswith("https://wordpress.org/"):
        feed["solver"] = "WordpressSolver"
    elif channel.link.startswith("https://www.comic-rocket.com/feeds/"):
        feed["solver"] = "ComicRocketSolver"
        comic_name = entries[0].link.split("/")[-2]
        if comic_name == "freefall":
            feed["solver"] = "FreefallSolver"
        elif comic_name == "questionable-content":
            feed["solver"] = "ImgIdSolver"
            feed["img_id"] = "strip"
        elif comic_name in ["el-goonish-shive", "egs-np"]:
            feed["solver"] = "ImgIdSolver"
            feed["img_id"] = "cc-comic"

    if feed["solver"] and feed["solver"] != "DefaultSolver":
        solver_class = globals().get(feed["solver"], None)
        if not solver_class:
            feed["solver"] = "DefaultSolver"
            return DefaultSolver(feed, channel)
        return solver_class(feed, channel)

    return DefaultSolver(feed, channel)


class DefaultSolver:
    def __init__(self, feed: dict, channel: FeedParserDict) -> None:
        self.feed = feed
        self.channel = channel

    async def solve(self, item: FeedParserDict) -> str:
        return f"New post in {self.channel_title}: [{item.title}]({item.links[0].href})"

    @property
    def channel_title(self):
        return self.channel.title

    async def fetch_link(self, item: FeedParserDict) -> str:
        self.url = item.links[0].href
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
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
        return f"New post in {self.channel_title}: [{item.title}]({item.links[0].href})"


class ComicRocketSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str:
        content = await self.fetch_link(item)
        if not self.url.startswith("https://www.comic-rocket.com/"):
            # Not a comic rocket page
            return f"New post in {self.channel_title}: [{item.title}]({self.url})"

        soup = BeautifulSoup(content, "html.parser")
        body = soup.find("div", id="serialpagebody")
        iframe = body.find("iframe")
        self.url = iframe["src"]

        return f"New post in {self.channel_title}: [{item.title}]({self.url})"


class FreefallSolver(ComicRocketSolver):
    async def solve(self, item: FeedParserDict) -> str:
        await super().solve(item)
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                data = await resp.text()
        soup = BeautifulSoup(data, "html.parser")
        img = soup.find("img")

        url = urllib.parse.urljoin(self.url, img["src"])

        return f"New post in {self.channel_title}: [{item.title}]({url})"


class ImgIdSolver(ComicRocketSolver):
    async def solve(self, item: FeedParserDict) -> str:
        await super().solve(item)
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                content = await resp.text()
        soup = BeautifulSoup(content, "html.parser")
        img = soup.find("img", id=self.feed["img_id"])
        url = img["src"]
        return f"New post in {self.channel_title}: [{item.title}]({url})"
