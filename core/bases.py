import typing, time
from sqlite3 import Row
from discord.ext import commands

if typing.TYPE_CHECKING:
    from main import Dicefiend

class BaseMinigameCog(commands.Cog):
    
    def __init__(self, bot: "Dicefiend") -> None:
        self.bot: "Dicefiend" = bot


    def current_timestamp(self) -> int:
        return int(time.time())

    

    # user data management
    async def get_user(self, user_id: int, lock: bool = False) -> Row | None:
        user: Row | None = await self.bot.execute(f"SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))

        if not user and not lock:
            async with self.bot.acquire_cursor() as cur:
                await cur.execute(f"INSERT INTO users (id) VALUES (?)", (user_id,))
                await cur.connection.commit()

            return await self.get_user(user_id, lock=True)  # setting lock to prevent infinite recursion

        return user
    
    async def give_xp(self, user_id: int, xp: int) -> bool:
        try:
            async with self.bot.acquire_cursor() as cur:
                await cur.execute(f"UPDATE users SET xp = xp + ? WHERE id = ?", (xp, user_id))
                await cur.connection.commit()

                return cur.get_cursor().rowcount > 0
        
        except Exception as e:
            print(f"Failed to add XP to user {user_id}: {e}")
            return False


    # per-user command timeout management
    async def is_timed_out(self, id: int) -> bool:
        current_timestamp: int = self.current_timestamp()
        ret: Row | None = await self.bot.execute(
            "SELECT 1 FROM command_timeouts WHERE id = ? AND timeout_until > ? LIMIT 1", (id, current_timestamp)
        )
        return ret is None
    
    async def set_timeout(self, id: int, unix: int) -> bool:
        try:
            async with self.bot.acquire_cursor() as cur:
                await cur.execute(f"INSERT OR REPLACE INTO command_timeouts (id, timeout_until) VALUES (?, ?)", (id, unix))
                await cur.connection.commit()

                return cur.get_cursor().rowcount > 0
    
        except Exception as e:
            print(f"Failed to set timeout for {id}: {e}")
            return False


    # Multiplayer minigame timeout listener
    async def on_game_timeout(self, id: int) -> None:
        raise NotImplementedError("This method should be implemented in the subclass.")