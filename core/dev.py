from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Dicefiend


class DevCommands(commands.Cog):
    def __init__(self, bot: "Dicefiend") -> None:
        self.bot: "Dicefiend" = bot

    @commands.guild_only()
    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context) -> None:
        if not ctx.author.guild_permissions.administrator:  # pyright: ignore[reportAttributeAccessIssue]
            await ctx.send("You don't have permission to use this command.")
            return

        try:
            await self.bot.tree.sync()
            await ctx.send("Commands synced successfully.")
        
        except Exception as e:
            await ctx.send(f"Failed to sync commands: {e}")


    @commands.guild_only()
    @commands.command(name="ping")
    async def server_status(self, ctx: commands.Context) -> None:
        if not ctx.author.guild_permissions.administrator:  # pyright: ignore[reportAttributeAccessIssue]
            await ctx.send("You don't have permission to use this command.")
            return

        await ctx.send(f"Latency: {self.bot.latency * 1000:.2f} ms")


async def setup(bot: "Dicefiend") -> None:
    await bot.add_cog(DevCommands(bot))
