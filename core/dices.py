import random
from typing import ( Callable, Literal, overload )


class Dice:

    @staticmethod
    def roll_D4() -> int:
        return random.randint(1, 4)
    
    @staticmethod
    def roll_D6() -> int:
        return random.randint(1, 6)
    
    @staticmethod
    def roll_D8() -> int:
        return random.randint(1, 8)
    
    @staticmethod
    def roll_D10() -> int:
        return random.randint(1, 10)
    
    @staticmethod
    def roll_D12() -> int:
        return random.randint(1, 12)
    
    @staticmethod
    def roll_D20() -> int:
        return random.randint(1, 20)
    
    @staticmethod
    def roll_D100() -> int:
        return random.randint(1, 100)
    

    @staticmethod
    def roll_custom(sides: int) -> int:
        if sides < 1:
            raise ValueError("Number of sides must be at least 1.")
        return random.randint(1, sides)
    

    @overload
    @staticmethod
    def roll_multiple(D: Callable[..., int], rolls: int, sum_rolls: Literal[False], **kwargs) -> list[int]: ...
    @overload
    @staticmethod
    def roll_multiple(D: Callable[..., int], rolls: int, sum_rolls: Literal[True], **kwargs) -> int: ...

    @staticmethod
    def roll_multiple(D: Callable[..., int], rolls: int, sum_rolls: bool = False, **kwargs) -> list[int] | int:
        results: list[int] = [D(**kwargs) for _ in range(rolls)]
        return sum(results) if sum_rolls else results