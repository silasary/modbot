import aiohttp
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
import urllib.parse

import sentry_sdk


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
        return self.format_message(item, item.links[0].href, None)

    def format_message(self, item, page_url, img_url):
        post = "post"
        title = item.title

        if img_url and page_url:
            post = f"[post](<{page_url}>)"
            title = f"[{item.title}]({img_url})"
        elif img_url:
            title = f"[{item.title}]({img_url})"
        elif page_url:
            post = f"[post]({page_url})"

        msg = f"New {post} in {self.channel_title}: {title}"
        return msg

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
            return self.format_message(item, item.links[0].href, image)
        return self.format_message(item, item.links[0].href, None)


class ComicRocketSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str:
        content = await self.fetch_link(item)
        if not self.url.startswith("https://www.comic-rocket.com/"):
            # Not a comic rocket page
            return self.format_message(item, self.url, None)

        soup = BeautifulSoup(content, "html.parser")
        body = soup.find("div", id="serialpagebody")
        iframe = body.find("iframe")
        self.url = iframe["src"]

        return self.format_message(item, self.url, None)


class FreefallSolver(ComicRocketSolver):
    async def solve(self, item: FeedParserDict) -> str:
        await super().solve(item)
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                data = await resp.text()
        soup = BeautifulSoup(data, "html.parser")
        img = soup.find("img")

        url = urllib.parse.urljoin(self.url, img["src"])

        return self.format_message(item, self.url, url)


class ImgIdSolver(ComicRocketSolver):
    async def solve(self, item: FeedParserDict) -> str:
        fallback = await super().solve(item)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as resp:
                    content = await resp.text()
            soup = BeautifulSoup(content, "html.parser")
            img = soup.find("img", id=self.feed["img_id"])
            url = urllib.parse.urljoin(self.url, img["src"])

            return self.format_message(item, self.url, url)
        except UnicodeDecodeError as e:
            sentry_sdk.capture_exception(e)
            return fallback
