"""每只猫咪的独立运行时状态"""

from . import constants


class CatState:
    """每只猫的独立状态"""
    def __init__(self):
        self.current_probability = constants.BASE_SWITCH_PROBABILITY
        self.is_moving = False
        self.move_dx = 0
        self.move_dy = 0
        self.move_timer = None

    def reset_probability(self):
        self.current_probability = constants.BASE_SWITCH_PROBABILITY

    def increase_probability(self):
        self.current_probability += constants.PROBABILITY_INCREMENT
        if self.current_probability > constants.MAX_PROBABILITY:
            self.current_probability = constants.MAX_PROBABILITY
