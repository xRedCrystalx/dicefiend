import asqlite, asyncio


async def main() -> None:
    async with asqlite.connect("main.db") as conn:
        _ = await conn.execute((
            "CREATE TABLE users ( "
            "   id INTEGER PRIMARY KEY, "
            "   xp INTEGER NOT NULL DEFAULT 0 "
            ");"
        ))

        _ = await conn.execute((
            "CREATE TABLE statistics ( "
            "   id INTEGER NOT NULL, "
            # TODO
            "   FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE "
            ");"
        ))

        _ = await conn.execute((
            "CREATE TABLE command_timeouts ( "
            "   id INTEGER NOT NULL, "
            "   cmd VARCHAR(24) NOT NULL, "
            "   timeout_until INTEGER NOT NULL, "
            "   PRIMARY KEY (id, cmd) "
            ");"
        ))

        await conn.commit()


if __name__ == "__main__":
    asyncio.run(main())