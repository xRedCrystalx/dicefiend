import typing

from discord.ext import commands
from discord import ( ui, app_commands, Interaction )

from core.models import ( DicefiendUser, ExposableException, Row )

if typing.TYPE_CHECKING:
    from main import Dicefiend


class BaseMinigameCog(commands.Cog):
    
    def __init__(self, bot: "Dicefiend") -> None:
        self.bot: "Dicefiend" = bot
        self.register_error_handlers()

    async def get_user(self, user_id: int, lock: bool = False) -> DicefiendUser | None:
        user: Row | None = await self.bot.execute(f"SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))

        # If user doesn't exist, create a new entry and retrieve it again
        if not user and not lock:
            async with self.bot.acquire_cursor() as cur:
                await cur.execute(f"INSERT INTO users (id) VALUES (?)", (user_id,))
                await cur.connection.commit()

            return await self.get_user(user_id, lock=True)  # setting lock to prevent infinite recursion

        return DicefiendUser(id=user["id"], xp=user["xp"], bot=self.bot)  # pyright: ignore[reportOptionalSubscript]


    # Multiplayer minigame timeout listener
    async def on_game_timeout(self, id: int) -> None:
        raise NotImplementedError("This method should be implemented in the subclass.")
    

    # Error handling for commands
    def register_error_handlers(self) -> None:
        """
        Registers error handlers for all commands in the cog.

        > command.on_error = self.command_error
        """
        pass


    def _unwrap_exposable(self, error: Exception) -> ExposableException | None:
        current: Exception = error
        
        while True:
            if isinstance(current, ExposableException):
                return current
            
            elif isinstance(current, commands.CommandInvokeError | app_commands.CommandInvokeError | commands.HybridCommandError):
                current = current.original
            
            else:
                return None

    async def command_error(self, ctx: commands.Context, error: commands.CommandError | commands.HybridCommandError) -> None:
        exposable: ExposableException | None = self._unwrap_exposable(error)

        if isinstance(exposable, ExposableException):
            await ctx.send(view=self.bot.to_container_view(ui.TextDisplay(str(exposable))), ephemeral=True)
        else:
            await ctx.send(view=self.bot.to_container_view(ui.TextDisplay("An unexpected error occurred. Please try again later.")), ephemeral=True)


    async def app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        exposable: ExposableException | None = self._unwrap_exposable(error)

        if isinstance(exposable, ExposableException):
            await interaction.response.send_message(view=self.bot.to_container_view(ui.TextDisplay(str(exposable))), ephemeral=True)
        else:
            await interaction.response.send_message(view=self.bot.to_container_view(ui.TextDisplay("An unexpected error occurred. Please try again later.")), ephemeral=True)   