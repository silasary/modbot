import copy
import io
import subprocess
import textwrap
import traceback
from contextlib import redirect_stdout
from importlib import reload as importlib_reload

import discord
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.config.owners

    @commands.command(name="load", hidden=True)
    async def load_cog(self, ctx, *, cog: str):
        """Command which Loads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name="unload", hidden=True)
    async def unload_cog(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name="reloadc", hidden=True)
    async def reload_cog(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name='reload', hidden=True)
    async def reload_all(self, ctx: commands.Context) -> None:
        extensions = list(self.bot.extensions.keys())
        for cog in extensions:
            try:
                self.bot.unload_extension(cog)
                self.bot.load_extension(cog)
            except Exception as e:
                await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
            else:
                await ctx.send(f"**`RELOADED {cog}`**")

    @commands.command(hidden=True)
    async def shutdown(self, ctx):
        embed = discord.Embed(color=0xFF0000)
        embed.add_field(name="Shutting down...",
                        value="Goodbye!", inline=False)
        await ctx.send(embed=embed)
        await self.bot.logout()

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip("` \n")

    @commands.command(hidden=True, name="eval")
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("✔")
            except discord.Forbidden:
                pass

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(description="[Owner only] Evaluates Bash Commands.", hidden=True)
    async def bash(self, ctx, *, command_to_run: str):
        output = subprocess.check_output(
            command_to_run.split(), stderr=subprocess.STDOUT
        ).decode("utf-8")
        await ctx.send(f"```py\n{output}\n```")

    @commands.command(hidden=True, description="[Owner Only] Execute SQL")
    async def sql(self, ctx, *, query: str):
        async with self.bot.pool.acquire() as conn:
            try:
                ret = await conn.fetch(query)
            except Exception:
                return await ctx.send(f"```py\n{traceback.format_exc()}```")
            if ret:
                await ctx.send(f"```{ret}```")
            else:
                await ctx.send("No results to fetch.")

    @commands.command(hidden=True, description="[Owner Only] Get an invite to a server")
    async def gimme(self, ctx, *, guildname: str):
        for guild in self.bot.guilds:
            if guild.name == guildname:
                try:
                    return await ctx.send((await guild.invites())[0])
                except IndexError:
                    try:
                        return await ctx.send(
                            await guild.text_channels[0].create_invite()
                        )
                    except discord.Forbidden:
                        return await ctx.send("Can't access invites.")
        await ctx.send("No guild found.")

    @commands.command(
        hidden=True, description="[Owner Only] Invoke a command as someone"
    )
    async def runas(self, ctx, member: discord.Member, *, command: str):
        fake_msg = copy.copy(ctx.message)
        fake_msg._update(ctx.message.channel, dict(
            content=ctx.prefix + command))
        fake_msg.author = member
        new_ctx = await ctx.bot.get_context(fake_msg)
        try:
            await ctx.bot.invoke(new_ctx)
        except Exception:
            await ctx.send(f"```py\n{traceback.format_exc()}```")

def setup(bot):
    bot.add_cog(Owner(bot))
