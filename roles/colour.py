from interactions import (
    Client,
    Color,
    Extension,
    Guild,
    Member,
    OptionType,
    Role,
    SlashContext,
    slash_option,
)
from interactions.ext.hybrid_commands import hybrid_slash_command


class Roles(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self._last_result = None

    @hybrid_slash_command(aliases=["setcolor"])
    @slash_option("colour", "The colour to set", OptionType.STRING, required=True)
    async def setcolour(self, ctx: SlashContext, colour: Color) -> None:
        await self.remove_colour(ctx.author)
        try:
            role = await self.get_or_create_colour_role(colour, ctx.guild)
        except ValueError as e:
            await ctx.send(str(e))
            return
        await ctx.author.add_role(role)
        await ctx.send("Done!")

    @setcolour.error
    async def colour_error(self, error, ctx, colour):
        if isinstance(error, KeyError):
            await ctx.send("That's not a colour I recognise.  Hex codes are `#RRGGBB`.")
            return
        await ctx.send("An unknown error occured")

    async def remove_colour(self, member: Member) -> None:
        for role in member.roles:
            if role.name.startswith("Colour: "):
                await member.remove_role(role)
                if not role.members:
                    await role.delete()

    async def get_or_create_colour_role(self, colour: Color, guild: Guild) -> Role:
        if isinstance(colour, str):
            colour = Color(colour)
        name = f"Colour: {str(colour)}"
        highest_colour = 99999
        for role in guild.roles:
            if role.name == name:
                return role
            elif role.name.startswith("Colour: "):
                order = role.position
                if order < highest_colour:
                    highest_colour = order
        else:
            role = await guild.create_role(name=name, colour=colour)
            if highest_colour != 99999:
                await role.move(position=highest_colour)
            return role
