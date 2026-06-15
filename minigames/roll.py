import typing, discord
from discord import app_commands

from core.dices import Dice
from core.bases import BaseMinigameCog, Row
from core.models import DicefiendUser, UserTimedOut, SaveDataError, UserDataError

if typing.TYPE_CHECKING:
    from main import Dicefiend


class RollCog(BaseMinigameCog):
    roll_group = app_commands.Group(name="roll", description="Let's roll the bloody dice!")

    # highroll
    @roll_group.command(name="highroll", description="Roll a dice and try to get the highest number possible!")    
    async def highroll(self, interaction: discord.Interaction) -> None:
        """
        - **Mechanic:** Roll 1d20. Any roll earns the standard reward.
        - **Base XP Reward:** +10 XP (If rolled 20 = +25 XP)
        - **Cooldown:** Once per 2 hours
        """

        user: DicefiendUser | None = await self.get_user(interaction.user.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        if user.is_timed_out():
            raise UserTimedOut("You are throwing the dice too much! Please wait before trying again.")


        roll_result: int = Dice.roll_D20()        
        xp_added: bool = await user.add_xp(25 if roll_result == 20 else 10)
        if not xp_added:
            raise SaveDataError("Failed to add XP to your account. Please try again later.")


        # 2 hours cooldown
        timed_out: bool = await user.set_timeout("highroll", self.bot.current_timestamp() + 2 * 60 * 60)
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")
        
        await interaction.response.send_message(f"You rolled a {roll_result}!  +{"25" if roll_result == 20 else "10"} XP has been added to your account.")


    # ladder
    @roll_group.command(name="ladder", description="Roll a series of dice and climb the ladder for bigger rewards!")
    async def dice_ladder(self, interaction: discord.Interaction) -> None:
        """
        - **Mechanic:** Roll d4 -> d6 -> d8 -> d10 -> d12 -> d20. Each roll must beat the prior to advance a tier..
        - **Base XP Reward:** +5 XP per tier, +30 bonus for full clear (max +60 XP)
        - **Cooldown:** Once per 4 hours
        """

        user: DicefiendUser | None = await self.get_user(interaction.user.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        if user.is_timed_out():
            raise UserTimedOut("You are throwing the dice too much! Please wait before trying again.")

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

        # 1 hour cooldown
        timed_out: bool = await user.set_timeout("ladder", self.bot.current_timestamp() + 4 * 60 * 60)
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")
        
        
        await interaction.response.send_message(f"You rolled: {', '.join(str(r) for r in dice_rolls)}!  +{xp_reward} XP has been added to your account.")


    @roll_group.command(name="lucky", description="")
    async def lucky_roll(self, interaction: discord.Interaction) -> None:
        """
        - **Mechanic:** A target number (1-20) is announced daily. Roll 1d20, exact match wins jackpot.
        - **Base XP Reward:** +5 XP for rolling within +/-2 of target, +50 XP for exact match
        - **Cooldown:** 3 per day
        """

        user: DicefiendUser | None = await self.get_user(interaction.user.id)
        if user is None:
            raise UserDataError(f"Failed to retrieve user data. Please try again later.")

        if user.is_timed_out():
            raise UserTimedOut("You are throwing the dice too much! Please wait before trying again.")

        target_number: int = 15
        roll_result: int = Dice.roll_D20()

        if roll_result == target_number:
            xp_reward: int = 50
        elif abs(roll_result - target_number) <= 2:
            xp_reward: int = 5
        else:
            xp_reward: int = 0

        xp_added: bool = await user.add_xp(xp_reward)
        if not xp_added:
            raise SaveDataError("Failed to add XP to your account. Please try again later.")
        
        
        ### TODO: better implementation for daily cooldowns
        timed_out: bool = await user.set_timeout("lucky", self.bot.current_timestamp() + 8 * 60 * 60) # 8h cooldown
        if not timed_out:
            raise SaveDataError("An unexpected error occurred. Please try again later.")
        ###
        
        await interaction.response.send_message(f"You rolled a {roll_result}!  +{xp_reward} XP has been added to your account.")



async def setup(bot: "Dicefiend") -> None:
    await bot.add_cog(RollCog(bot))