import unittest
from parameterized import parameterized

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

    def test_has_combination_2_2_returns_true_with_numbers_together_on_the_dice_roll(self):
        dice_roll = [1, 2, 2, 4, 6]
        dice_combination = [2, 2]
        has_combination_result = dice_roller.has_combination(dice_roll, dice_combination)
        self.assertTrue(has_combination_result)
        self.assertEqual([1, 2, 2, 4, 6], dice_roll)

    def test_has_combination_2_2_returns_true_with_numbers_apart_on_the_dice_roll(self):
        dice_roll = [1, 2, 4, 2, 6]
        dice_combination = [2, 2]
        has_combination_result = dice_roller.has_combination(dice_roll, dice_combination)
        self.assertTrue(has_combination_result)

    def test_has_combination_2_2_returns_true_with_three_2_on_the_dice_roll(self):
        dice_roll = [2, 1, 2, 5, 2]
        dice_combination = [2, 2]
        has_combination_result = dice_roller.has_combination(dice_roll, dice_combination)
        self.assertTrue(has_combination_result)

    def test_has_combination_2_2_returns_false_with_one_2_on_the_dice_roll(self):
        dice_roll = [1, 2, 4, 4, 6]
        dice_combination = [2, 2]
        has_combination_result = dice_roller.has_combination(dice_roll, dice_combination)
        self.assertFalse(has_combination_result)

    def test_get_pairs_combination_returns_correct_combination(self):
        pairs_combination_expected = [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6]]
        pairs_combination_result = dice_roller.get_pairs_combination()
        self.assertEqual(pairs_combination_expected, pairs_combination_result)

    def test_get_pairs_combination_plus_2_2_returns_correct_combination(self):
        pairs_combination_expected = [[2, 2], [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6]]]
        pairs_combination_result = dice_roller.get_pairs_combination_plus_2_2()
        self.assertEqual(pairs_combination_expected, pairs_combination_result)

    @parameterized.expand([
        [[1, 2, 3, 1, 6]],
        [[2, 1, 3, 2, 6]],
        [[3, 1, 2, 3, 6]],
        [[4, 1, 2, 4, 6]],
        [[5, 1, 3, 5, 6]],
        [[6, 1, 3, 2, 6]]
    ])
    def test_has_pairs_combination_returns_true_with_one_pair_on_the_dice_roll(self, dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        has_a_pair_combination_result = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        self.assertTrue(has_a_pair_combination_result)

    @parameterized.expand([
        [[1, 2, 3, 4, 6]],
        [[2, 3, 4, 5, 6]],
        [[2, 3, 4, 5, 6]],
        [[3, 4, 5, 6, 1]],
        [[4, 5, 6, 1, 2]],
        [[5, 6, 1, 2, 3]]
    ])
    def test_has_pairs_combination_returns_false_with_no_pairs_on_the_dice_roll(self, dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        has_a_pair_combination_result = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        self.assertFalse(has_a_pair_combination_result)

    @parameterized.expand([
        [[1, 2, 2, 1, 6]],
        [[2, 1, 3, 2, 3]],
        [[3, 4, 4, 3, 6]],
        [[4, 6, 2, 4, 6]],
        [[5, 5, 5, 5, 6]],
        [[6, 1, 3, 1, 6]]
    ])
    def test_has_pairs_combination_returns_true_with_two_pairs_on_the_dice_roll(self, dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        has_a_pair_combination_result = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        self.assertTrue(has_a_pair_combination_result)

    @parameterized.expand([
        [[1, 2, 2, 1, 6]],
        [[2, 2, 2, 2, 3]],
        [[3, 4, 4, 2, 2]],
        [[2, 6, 2, 4, 6]],
        [[2, 2, 5, 5, 2]],
        [[6, 2, 2, 6, 6]]
    ])
    def test_has_pairs_combination_plus_2_2_returns_true_with_adequate_dice_roll(self, dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        two_2s = [2, 2]
        expected_combinations = dice_roller.get_pairs_combination_plus_2_2()
        has_pairs = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        has_two_2s = dice_roller.has_combination(dice_roll, two_2s)
        has_expected_combination = dice_roller.has_all_combinations(dice_roll, expected_combinations)
        self.assertTrue(has_pairs)
        self.assertTrue(has_two_2s)
        self.assertTrue(has_expected_combination)

    @parameterized.expand([
        [[1, 1, 2, 1, 6]],
        [[2, 3, 1, 3, 3]],
        [[3, 4, 4, 6, 2]],
        [[2, 6, 4, 4, 6]],
        [[5, 5, 5, 5, 2]],
        [[6, 1, 2, 6, 6]]
    ])
    def test_has_pairs_combination_plus_2_2_returns_false_with_dice_roll_that_does_not_contains_2_2(self, dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        two_2s = [2, 2]
        expected_combinations = dice_roller.get_pairs_combination_plus_2_2()
        has_pairs = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        has_two_2s = dice_roller.has_combination(dice_roll, two_2s)
        has_expected_combination = dice_roller.has_all_combinations(dice_roll, expected_combinations)
        self.assertTrue(has_pairs)
        self.assertFalse(has_two_2s)
        self.assertFalse(has_expected_combination)


if __name__ == '__main__':
    unittest.main()
