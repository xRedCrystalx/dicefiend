import typing, discord

from discord import ui
from discord.ext import commands

from core.bases import BaseMinigameCog
from core.models import ( DicefiendUser, UserDataError )

if typing.TYPE_CHECKING:
    from main import Dicefiend


class ProfileCog(BaseMinigameCog):

    def __init__(self, bot: "Dicefiend") -> None:
        super().__init__(bot)

    @commands.guild_only()
    @commands.hybrid_command(name="profile", aliases=["p"], description="View your profile and stats.", with_app_command=True)
    async def view_profile(self, ctx: commands.Context) -> None:
        """
        View your profile and stats.
        """

        user: DicefiendUser | None = await self.get_user(ctx.author.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        await ctx.send(
            view=self.bot.to_container_view(
                ui.Section(
                    ui.TextDisplay((
                        f"## User Profile\n" 
                        f"> **Display name:** {discord.utils.escape_markdown(ctx.author.display_name)}\n"
                        f"> **Global name:** {discord.utils.escape_markdown(ctx.author.name)}\n"
                        f"> **Discord ID:** {ctx.author.id}\n"
                        f"> **Total XP:** `{user.xp:,}`"
                    )),
                    accessory=ui.Thumbnail(ctx.author.display_avatar.url)
                )
            )
        )


    def register_error_handlers(self) -> None:
        self.view_profile.error(BaseMinigameCog.command_error)


async def setup(bot: "Dicefiend") -> None:
    await bot.add_cog(ProfileCog(bot))

