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
        role = await self.get_or_create_colour_role(colour, ctx.guild)
        await ctx.author.add_roles(role)
        await ctx.send("Done!")

    # @setcolour.error
    # async def colour_error(self, ctx, error):
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         await ctx.send('You need to give me a color')
    #         return

    #     if isinstance(error, commands.UserInputError):
    #         await ctx.send("That's not a colour I recognise")
    #         return
    #     await ctx.send("An unknown error occured")

    async def remove_colour(self, member: Member) -> None:
        for role in member.roles:
            if role.name.startswith("Colour: "):
                await member.remove_roles(role)
                if not role.members:
                    await role.delete()

    async def get_or_create_colour_role(self, colour: Color, guild: Guild) -> Role:
        name = f"Colour: {str(colour)}"
        for role in guild.roles:
            if role.name == name:
                return role
        else:
            return await guild.create_role(name=name, colour=colour)
