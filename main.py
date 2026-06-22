import sys, os, discord, dotenv, aiohttp, asqlite, time
sys.dont_write_bytecode = True
from discord.ext import commands
from sqlite3 import Row

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, overload

from core.scheduler import TaskScheduler

dotenv.load_dotenv()

class Dicefiend(commands.Bot):
    def __init__(self) -> None:
        self.MAIN_POOL: asqlite.Pool
        self.SCHEDULER: TaskScheduler

        super().__init__(command_prefix=os.getenv("PREFIX", "!"), intents=discord.Intents.all(), help_command=None)

    async def setup_hook(self) -> None:
        print(rf"""
8888b.  88  dP""b8 888888 888888 88 888888 88b 88 8888b. 
 8I  Yb 88 dP   `" 88__   88__   88 88__   88Yb88  8I  Yb
 8I  dY 88 Yb      88""   88""   88 88""   88 Y88  8I  dY
8888Y"  88  YboodP 888888 88     88 888888 88  Y8 8888Y"

Loading... Please wait. 
──────────────────────────────────────────""")
        try:
            self.session: aiohttp.ClientSession = aiohttp.ClientSession()
            self.SCHEDULER = TaskScheduler()
            self.MAIN_POOL = await asqlite.create_pool("main.db", size=8)
        
            extensions: list[str] = [
                "core.dev",
                "core.profile",
                "minigames.bet",
                "minigames.duel",
                "minigames.heist",
                "minigames.raid",
                "minigames.roll",
                "minigames.tournament",
            ]

            for extension in extensions:
                try:
                    await self.load_extension(extension)
                    print(f"+ Loaded extension: {extension}")
                except Exception as extension_error:
                    print(f"- Failed to load extension {extension}: {extension_error}")

        except Exception as e:
            print(f"- Failed to load cogs: {e}")

    async def close(self) -> None:
        await self.session.close()
        await self.MAIN_POOL.close()

        return await super().close()

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if not isinstance(error, commands.CommandNotFound):
            await super().on_command_error(ctx, error)


    @asynccontextmanager
    async def acquire_cursor(self, pool: asqlite.Pool | None = None) -> AsyncGenerator[asqlite.Cursor, None]:
        pool = pool or self.MAIN_POOL

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                yield cur

    @overload
    async def execute(self, sql: str, params: tuple[Any, ...], pool: asqlite.Pool | None = None) -> Row | None: ...
    @overload
    async def execute(self, sql: str, params: tuple[Any, ...], pool: asqlite.Pool | None = None) -> list[Row]: ...

    async def execute(self, sql: str, params: tuple[Any, ...], pool: asqlite.Pool | None = None) -> Row | None | list[Row]:
        async with self.acquire_cursor(pool) as cur:
            _ret: asqlite.Cursor = await cur.execute(sql, params)

            if "LIMIT 1" in sql:
                return await _ret.fetchone()

            return await _ret.fetchall()

    
    def to_container_view(self, *items: discord.ui.Item) -> discord.ui.LayoutView:
        return discord.ui.LayoutView(timeout=None).add_item(discord.ui.Container(*items))
    
    def current_timestamp(self) -> int:
        return int(time.time())
    

if __name__ == "__main__":
    Dicefiend().run(os.getenv("TOKEN"), reconnect=True) # pyright: ignore[reportArgumentType]
