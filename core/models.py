from sqlite3 import Row
from typing import Any, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from main import Dicefiend


class DicefiendUser:
    """Represents a user in the Dicefiend system."""
    def __init__(self, id: int, xp: int, bot: "Dicefiend") -> None:
        self.id: int = id
        self.xp: int = xp

        self.bot: "Dicefiend" = bot

    async def _save(self, sql: str, params: tuple[Any, ...]) -> bool:
        try:
            async with self.bot.acquire_cursor() as cur:
                await cur.execute(sql, params)
                await cur.connection.commit()

                return cur.get_cursor().rowcount > 0
        
        except Exception as e:
            print(f"Failed to save user data for {self.id}: {e}")
            return False


    async def add_xp(self, amount: int) -> bool:
        new_xp: int = self.xp + amount
        _res: bool = await self._save("UPDATE users SET xp = ? WHERE id = ?", (new_xp, self.id))

        if _res:
            self.xp = new_xp

        return _res

    async def remove_xp(self, amount: int) -> bool:
        new_xp: int = self.xp - amount
        if new_xp < 0:
            return False
        
        _res: bool = await self._save("UPDATE users SET xp = ? WHERE id = ?", (new_xp, self.id))

        if _res:
            self.xp = new_xp

        return _res


    async def is_timed_out(self) -> bool:
        current_timestamp: int = self.bot.current_timestamp()
        ret: Row | None = await self.bot.execute(
            "SELECT 1 FROM command_timeouts WHERE id = ? AND timeout_until > ? LIMIT 1", (self.id, current_timestamp)
        )
        return ret is None
    
    async def set_timeout(self, cmd: str, unix: int) -> bool:
        return await self._save(
            "INSERT OR REPLACE INTO command_timeouts (id, cmd, timeout_until) VALUES (?, ?)", (self.id, cmd, unix)    
        )


class UserTimedOut(Exception):
    """Raised when a user is timed out from using a command."""
    pass

class UserDataError(Exception):
    """Raised when there is an error retrieving or managing user data."""
    pass

class SaveDataError(Exception):
    """Raised when there is an error saving data to the database."""
    pass
