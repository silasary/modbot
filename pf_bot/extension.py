import json
import os
from typing import NamedTuple
from interactions import AutocompleteContext, Extension, IntervalTrigger, OptionType, Task, listen, slash_command, slash_option, SlashCommandChoice
from . import scraper


class Watch(NamedTuple):
    name: str
    user: int
    data_centre: str
    role: str
    flags: str


class PartyFinderWatcher(Extension):
    def __init__(self, bot):
        self.dirty = False
        self.watches: list[Watch] = []
        self.autocomplete: set[str] = set()
        self.load()

    @listen()
    async def on_startup(self):
        self.fetch_pf.start()
        await self.fetch_pf()

    @listen()
    async def on_shutdown(self):
        self.save()

    def load(self):
        if os.path.exists("duty_names.json"):
            with open("duty_names.json", "r") as f:
                self.autocomplete = set(json.load(f))

    def save(self):
        dump = json.dumps(list(self.autocomplete), indent=2)
        with open("duty_names.json", "w") as f:
            f.write(dump)

    @slash_command()
    @slash_option("duty", "The duty to watch for", opt_type=OptionType.STRING, required=True)
    @slash_option(
        "role",
        "The role to watch for",
        opt_type=OptionType.STRING,
        required=False,
        choices=[SlashCommandChoice("Tank", "tank"), SlashCommandChoice("Healer", "healer"), SlashCommandChoice("DPS", "dps"), SlashCommandChoice("Any", "any")],
    )
    async def watch_pf(self, ctx, duty: str, role: str):
        dc = "Materia"
        if role == "any":
            role = ""
        flags = ""
        self.watches.append(Watch(name=duty, user=ctx.author.id, data_centre=dc, role=role, flags=flags))
        await ctx.send(f"Watching for {duty}!", ephemeral=True)

    @watch_pf.autocomplete("duty")
    async def duty_autocomplete(self, ctx: AutocompleteContext):
        options = list(self.autocomplete)
        options.sort()
        if ctx.input_text:
            options = [duty for duty in options if duty.lower().startswith(ctx.input_text.lower())]
        await ctx.send(options[:24])

    @Task.create(IntervalTrigger(seconds=60))
    async def fetch_pf(self):
        if not self.watches and self.autocomplete:
            return
        listings = scraper.scrape()
        for listing in listings:
            if listing.duty not in self.autocomplete:
                self.autocomplete.add(listing.duty)
                self.dirty = True

            if listing.data_centre != "Materia":
                continue
            for watch in self.watches.copy():
                if listing.duty == watch.name:
                    user = await self.bot.fetch_user(watch.user)
                    if user is None:
                        continue
                    if watch.role and not any(slot.role in [watch.role, "empty"] for slot in listing.slots):
                        continue

                    await user.send(f"New party finder listing for {listing.duty}\n{repr(listing)}")
                    self.watches.remove(watch)

        if self.dirty:
            self.save()
            self.dirty = False
