import aiohttp
from bs4 import BeautifulSoup, Tag
from feedparser import FeedParserDict
import urllib.parse
from markdownify import markdownify

from interactions import Embed
import sentry_sdk


def create_solver(feed: dict, channel: FeedParserDict, entries: list[FeedParserDict]) -> "DefaultSolver":
    if channel.get("generator") and channel["generator"].startswith("https://wordpress.org/"):
        feed["solver"] = "WordpressSolver"
    elif channel.link.startswith("https://www.comic-rocket.com/feeds/"):
        comic_name = entries[0].link.split("/")[-2]
        # if len(entries) == 1 and not entries[0].link.endswith('/1') and feed.get("upgradable", True):
        #     print(f'{comic_name} might be up to date')
        #     if comic_name == 'el-goonish-shive':
        #         feed['url'] = 'https://www.egscomics.com/comic/rss'
        #     elif comic_name == 'egs-np':
        #         feed['url'] = 'https://www.egscomics.com/egsnp/rss'
        #     else:
        #         feed['upgradable'] = True

        if comic_name == "freefall":
            feed["solver"] = "FreefallSolver"
        elif comic_name == "questionable-content":
            feed["solver"] = "ImgIdSolver"
            feed["img_id"] = "strip"
        elif comic_name in ["el-goonish-shive", "egs-np"]:
            feed["solver"] = "ImgIdSolver"
            feed["img_id"] = "cc-comic"

    if feed.get("solver") and feed["solver"] != "DefaultSolver":
        solver_class = globals().get(feed["solver"], None)
        if not solver_class:
            feed["solver"] = "DefaultSolver"
            return UnknownSolver(feed, channel)
        return solver_class(feed, channel)

    return UnknownSolver(feed, channel)


class DefaultSolver:
    def __init__(self, feed: dict, channel: FeedParserDict) -> None:
        self.feed = feed
        self.channel = channel

    async def solve(self, item: FeedParserDict) -> str | Embed | tuple[str, Embed]:
        await self.fetch_link(item)
        return self.format_message(item, self.url, None)

    def format_message(self, item: FeedParserDict, page_url: str, img_url: str) -> str:
        post = "post"
        title = item.title

        if img_url and page_url:
            img_url = img_url.replace(" ", "%20")
            post = f"[post](<{page_url}>)"
            title = f"[{item.title}]({img_url})"
        elif img_url:
            title = f"[{item.title}]({img_url})"
        elif page_url:
            post = f"[post]({page_url})"
        else:
            post = f"[post]({item.links[0].href})"

        msg = f"New {post} in {self.channel_title}: {title}"
        return msg

    def format_embed(self, item: FeedParserDict, page_url: str, img_url: str, alt_text: str) -> Embed:
        embed = Embed(title=item.title)
        embed.set_author(name=self.channel_title, url=page_url)
        embed.set_image(url=img_url.replace(" ", "%20"))
        if alt_text:
            embed.set_footer(alt_text)
        return embed

    @property
    def channel_title(self):
        return self.channel.title

    async def fetch_link(self, item: FeedParserDict) -> str:
        """Fetches the link of the item and returns the content."""
        self.url = item.links[0].href
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                data = await resp.text()

            if self.url.startswith("https://www.comic-rocket.com/"):
                soup = BeautifulSoup(data, "html.parser")
                body = soup.find("div", id="serialpagebody")
                iframe = body.find("iframe")
                self.url = iframe["src"]
                async with session.get(self.url) as resp:
                    data = (await resp.read()).decode("utf-8", errors="ignore")

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


class FreefallSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str:
        data = await self.fetch_link(item)
        soup = BeautifulSoup(data, "html.parser")
        img = soup.find("img")

        url = urllib.parse.urljoin(self.url, img["src"])

        return self.format_message(item, self.url, url)


class ImgIdSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str | list[Embed]:
        fallback = await super().solve(item)
        try:
            content = await self.fetch_link(item)
            soup = BeautifulSoup(content, "html.parser")
            img = soup.find("img", id=self.feed["img_id"])
            url = urllib.parse.urljoin(self.url, img["src"])
            title = img.get("title")
            storyline = soup.find("select", {"name": "comic-storyline"})
            if storyline:
                storyline = storyline.find("option", selected=True)
                if storyline:
                    title = f"{title} - {storyline.text.strip()}"
            newsbody = soup.find("div", class_="cc-newsbody")
            if not newsbody:
                newsbody = soup.find("div", id="newspost")
            embeds = []
            if title:
                embeds.append(self.format_embed(item, self.url, url, title))
            elif newsbody:
                embeds.append(self.format_embed(item, self.url, url, None))

            if newsbody:
                embeds.append(await self.parse_newsbody(newsbody))
            if embeds:
                return embeds
            return self.format_message(item, self.url, url)
        except UnicodeDecodeError as e:
            sentry_sdk.capture_exception(e)
            return fallback

    async def parse_newsbody(self, newsbody: Tag) -> Embed:
        links = newsbody.find_all("a")
        for link in links:
            if link["href"].startswith("/"):
                link["href"] = urllib.parse.urljoin(self.url, link["href"])
        md = markdownify(str(newsbody))
        if not md:
            return None
        if len(md) > 4096:
            return Embed(description=md[:4090] + "...")
        return Embed(description=md)


class UnknownSolver(DefaultSolver):
    async def solve(self, item: FeedParserDict) -> str:
        try:
            content = await self.fetch_link(item)
            soup = BeautifulSoup(content, "html.parser")
            comic = soup.find("img", id="cc-comic")
            if comic:
                self.feed["solver"] = "ImgIdSolver"
                self.feed["img_id"] = "cc-comic"
                return await ImgIdSolver(self.feed, self.channel).solve(item)
            comic = soup.find("img", id="comic-image")
            if comic:
                self.feed["solver"] = "ImgIdSolver"
                self.feed["img_id"] = "comic-image"
                return await ImgIdSolver(self.feed, self.channel).solve(item)
        except Exception as e:
            sentry_sdk.capture_exception(e)
        return await super().solve(item)
