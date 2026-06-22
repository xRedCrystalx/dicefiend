import typing
from datetime import ( time, timedelta, UTC )

from discord.ext import commands
from discord import ( ui, TextChannel )

from core.dices import Dice
from core.bases import BaseMinigameCog
from core.models import ( DicefiendUser, MinigameIDs, Cooldowns, UserTimedOut, SaveDataError, UserDataError )

if typing.TYPE_CHECKING:
    from main import Dicefiend


class RollCog(BaseMinigameCog):

    def __init__(self, bot: "Dicefiend") -> None:
        self.LUCKY_NUMBER: int = 0  # TODO: Preserve the lucky number across bot restarts

        super().__init__(bot)

    # roll command hybrid group init
    @commands.guild_only()
    @commands.hybrid_group(name="roll", description="Let's roll the bloody dice!", with_app_command=True)
    async def roll_group(self, ctx: commands.Context) -> None:
        await ctx.send("What are you trying to roll 🙃.")


    # highroll
    @commands.guild_only()
    @roll_group.command(name="highroll", aliases=["hr", "rh", "hroll", "h"], description="Roll a dice and try to get the highest number possible!")    
    async def highroll(self, ctx: commands.Context) -> None:
        """
        - **Mechanic:** Roll 1d20. Any roll earns the standard reward.
        - **Base XP Reward:** +10 XP (If rolled 20 = +25 XP)
        - **Cooldown:** Once per 2 hours
        """

        user: DicefiendUser | None = await self.get_user(ctx.author.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        timestamp: int = await user.timed_out_until(MinigameIDs.HIGHROLL)
        if timestamp:
            raise UserTimedOut(f"You are throwing the dice too much! You can throw again <t:{timestamp}:R>.")


        roll_result: int = Dice.roll_D20()        
        xp_added: bool = await user.add_xp(25 if roll_result == 20 else 10)
        if not xp_added:
            raise SaveDataError("Failed to add XP to your account. Please try again later.")


        timed_out: bool = await user.set_timeout(MinigameIDs.HIGHROLL, self.bot.current_timestamp() + Cooldowns.HOUR2)
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")
        
        await ctx.send(
            view=self.bot.to_container_view(
                ui.TextDisplay(f"🎲 You rolled `{roll_result}`!\n**+{"25" if roll_result == 20 else "10"} XP** has been added to your account.")
            )
        )

    # lowroll
    @commands.guild_only()
    @roll_group.command(name="lowroll", aliases=["lr", "rl", "lroll", "l"], description="Roll a dice and try to get the lowest number possible!")    
    async def lowroll(self, ctx: commands.Context) -> None:
        """
        - **Mechanic:** Roll 1d20. Any roll earns the standard reward.
        - **Base XP Reward:** +10 XP (If rolled 0 = +25 XP)
        - **Cooldown:** Once per 2 hours
        """

        user: DicefiendUser | None = await self.get_user(ctx.author.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        timestamp: int = await user.timed_out_until(MinigameIDs.LOWROLL)
        if timestamp:
            raise UserTimedOut(f"You are throwing the dice too much! You can throw again <t:{timestamp}:R>.")

        roll_result: int = Dice.roll_D20()        
        xp_added: bool = await user.add_xp(25 if roll_result == 0 else 10)
        if not xp_added:
            raise SaveDataError("Failed to add XP to your account. Please try again later.")
        

        timed_out: bool = await user.set_timeout(MinigameIDs.LOWROLL, self.bot.current_timestamp() + Cooldowns.HOUR2)
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")
        
        await ctx.send(
            view=self.bot.to_container_view(
                ui.TextDisplay(f"🎲 You rolled `{roll_result}`!\n**+{"25" if roll_result == 0 else "10"} XP** has been added to your account.")
            )
        )

    # ladder
    @commands.guild_only()
    @roll_group.command(name="ladder", aliases=["ld"], description="Roll a series of dice and climb the ladder for bigger rewards!")
    async def dice_ladder(self, ctx: commands.Context) -> None:
        """
        - **Mechanic:** Roll d4 -> d6 -> d8 -> d10 -> d12 -> d20. Each roll must beat the prior to advance a tier..
        - **Base XP Reward:** +5 XP per tier, +30 bonus for full clear (max +60 XP)
        - **Cooldown:** Once per 4 hours
        """

        user: DicefiendUser | None = await self.get_user(ctx.author.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        timestamp: int = await user.timed_out_until(MinigameIDs.LADDER)
        if timestamp:
            raise UserTimedOut(f"You are throwing the dice too much! You can throw again <t:{timestamp}:R>.")

        dice_sequence: list[int] = [4, 6, 8, 10, 12, 20]
        dice_rolls: list[int] = []

        current_roll: int = 0
        xp_reward: int = 0

        for sides in dice_sequence:
            roll_result: int = Dice.roll_custom(sides)
            dice_rolls.append(roll_result)
            
            if roll_result > current_roll:
                xp_reward += 5
                current_roll = roll_result
            else:
                break
        else:
            xp_reward += 30  # full clear bonus

        xp_added: bool = await user.add_xp(xp_reward)
        if not xp_added:
            raise SaveDataError("Failed to add XP to your account. Please try again later.")

        timed_out: bool = await user.set_timeout(MinigameIDs.LADDER, self.bot.current_timestamp() + Cooldowns.HOUR4)
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")
        
        await ctx.send(
                view=self.bot.to_container_view(
                    ui.TextDisplay(
                        "🎲 You rolled:"
                        + "".join(f"\n- **1d{seq}**: `{roll}`" for seq, roll in zip(dice_sequence, dice_rolls))
                        + ("\nPerfect ladder! **+30 XP**\n" if len(dice_rolls) == len(dice_sequence) else "")
                        + f"\n**+{xp_reward} XP** has been added to your account."
                    )
                )
            )

    # lucky number
    @commands.guild_only()
    @roll_group.command(name="lucky", aliases=["luck"], description="Roll a dice and try to hit the lucky number for a jackpot!")
    async def lucky_roll(self, ctx: commands.Context) -> None:
        """
        - **Mechanic:** A target number (1-20) is announced daily. Roll 1d20, exact match wins jackpot.
        - **Base XP Reward:** +5 XP for rolling within +/-2 of target, +50 XP for exact match
        - **Cooldown:** Once every 8 hours
        """

        user: DicefiendUser | None = await self.get_user(ctx.author.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        timestamp: int = await user.timed_out_until(MinigameIDs.LUCKY)
        if timestamp:
            raise UserTimedOut(f"You are throwing the dice too much! You can throw again <t:{timestamp}:R>.")

        roll_result: int = Dice.roll_D20()

        if roll_result == self.LUCKY_NUMBER:
            xp_reward: int = 50
        elif abs(roll_result - self.LUCKY_NUMBER) <= 2:
            xp_reward: int = 5
        else:
            xp_reward: int = 0

        xp_added: bool = await user.add_xp(xp_reward)
        if not xp_added:
            raise SaveDataError("Failed to add XP to your account. Please try again later.")
        
        timed_out: bool = await user.set_timeout(MinigameIDs.LUCKY, self.bot.current_timestamp() + Cooldowns.HOUR8)
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")

        await ctx.send(
            view=self.bot.to_container_view(
                ui.TextDisplay(f"You rolled a `{roll_result}`! The lucky number is **{self.LUCKY_NUMBER}**.\n**+{xp_reward} XP** has been added to your account.")
            )
        )


    # single text command aliasing hack
    @commands.guild_only()
    @commands.command(name="highroll", aliases=["hr", "rh", "hroll"])
    async def highroll_alias(self, ctx: commands.Context) -> None:
        return await self.highroll(ctx)

    @commands.guild_only()
    @commands.command(name="lowroll", aliases=["lr", "rl", "lroll"])
    async def lowroll_alias(self, ctx: commands.Context) -> None:
        return await self.lowroll(ctx)

    @commands.guild_only()
    @commands.command(name="ladder", aliases=["ld"])
    async def dice_ladder_alias(self, ctx: commands.Context) -> None:
        return await self.dice_ladder(ctx)

    @commands.guild_only()
    @commands.command(name="lucky", aliases=["luck"])
    async def lucky_roll_alias(self, ctx: commands.Context) -> None:
        return await self.lucky_roll(ctx)


    def register_error_handlers(self) -> None:
        commands_to_register: list[commands.Command | commands.HybridCommand] = [
            self.roll_group, self.highroll, self.lowroll, self.dice_ladder, self.lucky_roll,
            self.highroll_alias, self.lowroll_alias, self.dice_ladder_alias, self.lucky_roll_alias
        ]
        
        for command in commands_to_register:
            command.error(BaseMinigameCog.command_error)


    # Scheduled task to announce the lucky number of the day
    async def announce_lucky_number(self) -> None:
        """
        This method is intended to be called by a scheduled task to announce the lucky number of the day.
        """
        self.LUCKY_NUMBER: int = Dice.roll_D20()

        channel_id: int = 1517442673886101514
        channel: TextChannel | None = self.bot.get_channel(channel_id)  # pyright: ignore[reportAssignmentType]

        if channel:
            await channel.send(
                view=self.bot.to_container_view(
                    ui.TextDisplay(f"The lucky number of today is **{self.LUCKY_NUMBER}**. Good luck rollin'!")
                )
            )


async def setup(bot: "Dicefiend") -> None:
    cog: RollCog = RollCog(bot)
    
    await bot.SCHEDULER.run_every(
        id="roll:lucky_number", 
        _start=time(hour=00, tzinfo=UTC), interval=timedelta(days=1), 
        callable=cog.announce_lucky_number
    )

    await bot.add_cog(cog)


