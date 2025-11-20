import asyncio
import os
import re
import subprocess
import sys
from interactions import Client, Extension, integration_types, listen
from interactions.models import ContextMenuContext, message_context_menu
from interactions.models.internal.tasks import Task, IntervalTrigger
from shared import configuration

configuration.DEFAULTS.update(
    {
        "apworlds_repo": os.path.expanduser("~/apworlds_repo"),
    })

REPO_REGEX = r'(https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)'

async def git(args: list[str], cwd: str) -> int:
    """Run a git command."""
    return await run(['git', *args], cwd)

async def run(args: list[str], cwd: str) -> int:
    print(f"Running {' '.join(args)} in {cwd}")
    if sys.platform == "win32":
        try:
            subprocess.run(args, cwd=cwd, check=True)
            return 0
        except subprocess.CalledProcessError as e:
            return e.returncode
    else:
        process = await asyncio.subprocess.create_subprocess_exec(*args, cwd=cwd)
        code = await process.wait()
        return code

async def run_output(args: list[str], cwd: str) -> str:
    print(f"Running {' '.join(args)} in {cwd}")
    if sys.platform == "win32":
        try:
            out = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout
            return out
        except subprocess.CalledProcessError as e:
            return str(e.returncode)
    else:
        process = await asyncio.subprocess.create_subprocess_exec(*args, cwd=cwd)
        code = await process.wait()
        return code


class APTools(Extension):
    def __init__(self, bot: Client) -> None:
        super().__init__()
        self.bot = bot

    @listen()
    async def on_startup(self) -> None:
        self.process_queued_repos.start()
        await self.process_queued_repos()


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

    @Task.create(IntervalTrigger(hours=12))
    async def process_queued_repos(self) -> None:
        queue_file = os.path.join(configuration.get("apworlds_repo"), "queue.txt")
        if not os.path.exists(queue_file):
            return

        with open(queue_file, "r") as f:
            repos = f.readlines()

        if not repos:
            return

        python = sys.executable
        await git(["pull"], cwd=configuration.get("apworlds_repo"))
        scripts = os.path.join(configuration.get("apworlds_repo"), "scripts")
        await run([python, "-m", "pip", "install", "-r", "requirements.txt"], cwd=scripts)
        output = await run_output([python, "add_worlds.py"], cwd=scripts)
        await git(["add", "index"], cwd=configuration.get("apworlds_repo"))
        await git(["commit", "-m", "Add worlds"], cwd=configuration.get("apworlds_repo"))
        await git(["push"], cwd=configuration.get("apworlds_repo"))

        await self.bot.owner.send(f'```{output}```')
