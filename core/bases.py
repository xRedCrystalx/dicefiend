import typing, discord
from sqlite3 import Row
from discord.ext import commands

from core.models import DicefiendUser, ExposableException

if typing.TYPE_CHECKING:
    from main import Dicefiend

class BaseMinigameCog(commands.Cog):
    
    def __init__(self, bot: "Dicefiend") -> None:
        self.bot: "Dicefiend" = bot

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
    

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, ExposableException):
            await interaction.response.send_message(view=self.bot.to_container_view(discord.ui.TextDisplay(str(error))), ephemeral=True)
        else:
            await interaction.response.send_message("An unexpected error occurred. Please try again later.", ephemeral=True)