from discord.ext import commands
from discord import utils, TextChannel, CategoryChannel
import discord
import attr
from typing import Optional, Union

@attr.s(auto_attribs=True, hash=False)
class Spoilers(commands.Cog):
    bot: commands.Bot

    @commands.command(aliases=['spoiler', 'spoilers', 'spoilerchan'])
    async def spoilerchannel(self, ctx: commands.Context, channel: Union[TextChannel, str], *, description: Optional[str]) -> None:
        guild: discord.Guild = ctx.guild
        spoilercat = await get_spoilercat(ctx.guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        if isinstance(channel, str):
            channel_name = channel.strip('#')
            channel = utils.find(lambda chan: chan.name == channel_name, guild.channels) or await spoilercat.create_text_channel(channel, overwrites=overwrites)
        options = {'overwrites': overwrites}
        if description or not channel.topic:
            options['topic'] = '「AutoChannel」 ' + (description or '')
        await channel.edit(**options)
        signup = await get_signup_msg(channel)
        await signup.clear_reactions()
        await signup.add_reaction('🔒')

    @commands.Cog.listener('on_raw_reaction_remove')
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.emoji.name == '🔒':
            add = payload.event_type == 'REACTION_ADD'
            channel: TextChannel = self.bot.get_channel(payload.channel_id)
            msg: discord.Message = utils.get(self.bot.cached_messages, id=payload.message_id) or await channel.fetch_message(payload.message_id)
            if msg.author != self.bot.user or not msg.content.startswith('🔐<#'):
                return
            target_id = int(msg.content.split('~')[0].strip('🔐<#> '))
            target: discord.TextChannel = channel.guild.get_channel(target_id)
            overwrites = target.overwrites
            user = self.bot.get_user(payload.user_id)
            overwrites[user] = discord.PermissionOverwrite(read_messages=add)
            await target.edit(overwrites=overwrites)



async def get_spoilercat(guild: discord.Guild) -> CategoryChannel:
    spoilercat = utils.find(lambda chan: chan.name == 'Spoilers', guild.categories)
    if spoilercat is None:
        spoilercat = await guild.create_category('Spoilers')
    return spoilercat

async def get_signup_chan(guild: discord.Guild) -> TextChannel:
    spoilercat = await get_spoilercat(guild)
    overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False),
            guild.me: discord.PermissionOverwrite(send_messages=True)
        }
    return utils.get(spoilercat.channels, name='spoiler-channels') or await spoilercat.create_text_channel('spoiler-channels', topic='Get your spoilers here!', overwrites=overwrites)

async def get_signup_msg(channel: TextChannel) -> discord.Message:
    signups = await get_signup_chan(channel.guild)
    mention = f'<#{channel.id}>'
    content = f'🔐{mention} ~ {channel.topic[14:]}'
    msg = await signups.history().find(lambda m: mention in m.content) or await signups.send(content)
    if msg.content != content:
        await msg.edit(content=content)
    return msg

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Spoilers(bot))
