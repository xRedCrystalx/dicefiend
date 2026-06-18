from sqlite3 import Row
from typing import Any, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from main import Dicefiend

class MinigameIDs:
    HIGHROLL: str = "highroll"
    LOWROLL: str = "lowroll"
    LADDER: str = "ladder"
    LUCKY: str = "lucky"
    BET: str = "bet"
    DUEL: str = "duel"
    HEIST: str = "heist"
    RAID: str = "raid"
    TOURNAMENT: str = "tournament"

class Cooldowns:
    MINUTE: int = 60
    MINUTE15: int = 15 * MINUTE
    MINUTE30: int = 30 * MINUTE
    MINUTE45: int = 45 * MINUTE
    HOUR: int = 60 * MINUTE
    HOUR2: int = 2 * HOUR
    HOUR4: int = 4 * HOUR
    HOUR6: int = 6 * HOUR
    HOUR8: int = 8 * HOUR
    HOUR12: int = 12 * HOUR
    DAY: int = 24 * HOUR


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


    async def timed_out_until(self, cmd: str) -> int:
        current_timestamp: int = self.bot.current_timestamp()
        ret: Row | None = await self.bot.execute(
            "SELECT timeout_until FROM command_timeouts WHERE id = ? AND cmd = ? AND timeout_until > ? LIMIT 1", (self.id, current_timestamp, cmd)
        )

        return ret["timeout_until"] if ret else 0
    
    async def set_timeout(self, cmd: str, unix: int) -> bool:
        return await self._save(
            "INSERT OR REPLACE INTO command_timeouts (id, cmd, timeout_until) VALUES (?, ?)", (self.id, cmd, unix)    
        )


class ExposableException(Exception):
    """Base class for exceptions that can be exposed to the user."""
    pass


class UserTimedOut(ExposableException):
    """Raised when a user is timed out from using a command."""
    pass

class UserDataError(ExposableException):
    """Raised when there is an error retrieving or managing user data."""
    pass

class SaveDataError(ExposableException):
    """Raised when there is an error saving data to the database."""
    pass
