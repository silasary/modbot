import os
import re
from interactions import Client, Extension, integration_types
from interactions.models import ContextMenuContext, message_context_menu
from shared import configuration

configuration.DEFAULTS.update(
    {
        "apworlds_repo": os.path.expanduser("~/apworlds_repo"),
    })

REPO_REGEX = r'(https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)'

class APTools(Extension):
    def __init__(self, bot: Client) -> None:
        super().__init__()
        self.bot = bot

    @message_context_menu(name="Scan for APWorld Repos")
    @integration_types(guild=False, user=True)
    async def scan_for_apworld_repos(self, ctx: ContextMenuContext) -> None:
        content = ctx.target.content
        matches = re.findall(REPO_REGEX, content)
        repos = set()
        if not matches:
            await ctx.send("No APWorld repositories found.", ephemeral=True)
            return

        for match in matches:
            repos.add(match)

        with open(os.path.join(configuration.get("apworlds_repo"), "queue.txt"), "a") as f:
            for repo in repos:
                f.write(f"{repo}\n")

        await ctx.send(f"Queued {len(repos)} repositories for processing.", ephemeral=True)
