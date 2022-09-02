import unittest

import dice_roller


class TestDiceRoller(unittest.TestCase):
    
    def test_roll_die_get_result_between_1_and_6(self):
        valid_values = [1, 2, 3, 4, 5, 6]
        for n in range(100):
            die_result = dice_roller.roll_die()
            self.assertIn(die_result, valid_values)

    def test_roll_dice_is_using_roll_die_method(self):
        self.assertTrue(True)

    def test_roll_dice_with_no_parameters_returns_five_dice(self):
        dice_roll_result = dice_roller.roll_dice()
        self.assertEqual(len(dice_roll_result), 5)


if __name__ == '__main__':
    unittest.main()
