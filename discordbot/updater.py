import subprocess
from interactions import Client, Extension, Task, IntervalTrigger, listen


class Updater(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.commit_id = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        self.branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip().decode()
        try:
            upstream = subprocess.check_output(["git", "rev-parse", f"origin/{self.branch}"]).decode().strip()
        except subprocess.CalledProcessError:
            return
        if upstream == self.commit_id:
            print(f"Currently running {self.commit_id} on {self.branch}")

    @listen()
    async def on_startup(self) -> None:
        self.update.start()

    @Task.create(IntervalTrigger(minutes=5.0))
    async def update(self) -> None:
        subprocess.check_output(["git", "fetch"]).decode()
        commit_id = subprocess.check_output(["git", "rev-parse", f"origin/{self.branch}"]).decode().strip()
        if commit_id != self.commit_id:
            print(f"origin/{self.branch} at {commit_id}")
            print("Update found, shutting down")
            await self.bot.stop()
