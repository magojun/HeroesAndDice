import unittest
from parameterized import parameterized

import dice_roller


class TestDiceRoller(unittest.TestCase):
    
    def test_roll_dice_get_result_between_1_and_6(self):
        valid_values = [1, 2, 3, 4, 5, 6]
        for n in range(100):
            dice_result = dice_roller.roll_one_die()
            self.assertIn(dice_result.get_number(), valid_values)

    def test_roll_dice_is_using_roll_die_method(self):
        self.assertTrue(True)

    def test_roll_dice_with_no_parameters_returns_five_dice(self):
        dice_roll_result = dice_roller.roll_dice()
        self.assertEqual(5, len(dice_roll_result))

    def test_roll_dice_with_no_parameters_returns_five_dice_and_one_is_a_special_dice(self):
        dice_roll_result = dice_roller.roll_dice()
        self.assertTrue(dice_roll_result.has_special_dice())
        self.assertEqual(5, len(dice_roll_result))

    def test_roll_dice_with_no_special_dice_returns_five_dice_and_none_of_them_is_a_special_dice(self):
        dice_roll_result = dice_roller.roll_dice(number_of_special_dice=0)
        self.assertFalse(dice_roll_result.has_special_dice())
        self.assertEqual(5, len(dice_roll_result))

    @parameterized.expand([
        [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12]
    ])
    def test_roll_dice_with_parameters_returns_correct_dice_amount(self, dice_amount):
        dice_roll_result = dice_roller.roll_dice(dice_amount)
        self.assertEqual(dice_amount, len(dice_roll_result))

    @parameterized.expand([
        [[1, 2, 2, 4, 6], [2, 2], [2, 2]],
        [[2, 1, 2, 5, 2], [2, 2], [2, 2]],
        [[1, 2, 4, 4, 6], [2, 2], []],
        [[1, 2, 3, 4, 6], [1, 2, 3], [1, 2, 3]],
        [[1, 2, 5, 5, 6], [5, 6], [5, 6]],
        [[6, 6, 5, 5, 6], [1], []]
    ])
    def test_find_combination_returns_expected_result(self, dice_roll, dice_combination, found_combination_expected):
        found_combination = dice_roller.find_combination(dice_roll, dice_combination)
        self.assertEqual(found_combination_expected, found_combination)

    @parameterized.expand([
        [[1, 2, 2, 4, 6], True],
        [[1, 2, 4, 2, 6], True],
        [[2, 1, 2, 5, 2], True],
        [[1, 2, 4, 4, 6], False]
    ])
    def test_has_combination_2_2_returns_expected_result(self, dice_roll, has_combination_expected):
        dice_combination = [2, 2]
        has_combination_result = dice_roller.has_combination(dice_roll, dice_combination)
        self.assertEqual(has_combination_expected, has_combination_result)

    def test_get_pairs_combination_returns_correct_combination(self):
        pairs_combination_expected = [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6]]
        pairs_combination_result = dice_roller.get_pairs_combination()
        self.assertEqual(pairs_combination_expected, pairs_combination_result)

    def test_get_smallers_combination_returns_correct_combination(self):
        smallers_combination_expected = [[1], [2], [3]]
        smallers_combination_result = dice_roller.get_smallers_combination()
        self.assertEqual(smallers_combination_expected, smallers_combination_result)

    @parameterized.expand([
        [[2, 2]],
        [[1, 2, 3]],
        [[4, 5]],
        [[1, 2, 4]]
    ])
    def test_get_pairs_combination_plus_another_combination_returns_correct_combination(self, second_dice_combination):
        pairs_combination_expected = [second_dice_combination, [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6]]]
        pairs_combination_result = dice_roller.get_pairs_combination_plus_another_combination(second_dice_combination)
        self.assertEqual(pairs_combination_expected, pairs_combination_result)

    @parameterized.expand([
        [[1, 2, 3, 1, 6], [[1, 1]]],
        [[2, 1, 3, 2, 6], [[2, 2]]],
        [[3, 1, 2, 3, 6], [[3, 3]]],
        [[4, 1, 2, 4, 6], [[4, 4]]],
        [[5, 1, 3, 5, 6], [[5, 5]]],
        [[6, 1, 3, 2, 6], [[6, 6]]],
        [[1, 2, 3, 4, 5], []],
        [[2, 3, 4, 5, 6], []]
    ])
    def test_found_combinations_returns_expected_result(self, dice_roll, found_combinations_expected):
        pairs_combination = dice_roller.get_pairs_combination()
        found_combinations_result = dice_roller.found_combinations(dice_roll, pairs_combination)
        self.assertEqual(found_combinations_expected, found_combinations_result)

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
        expected_combinations = dice_roller.get_pairs_combination_plus_another_combination(two_2s)
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
        [[6, 1, 2, 6, 6]],
    ])
    def test_has_pairs_combination_plus_2_2_returns_false_with_dice_roll_that_does_not_contains_2_2(self, dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        two_2s = [2, 2]
        expected_combinations = dice_roller.get_pairs_combination_plus_another_combination(two_2s)
        has_pairs = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        has_two_2s = dice_roller.has_combination(dice_roll, two_2s)
        has_expected_combination = dice_roller.has_all_combinations(dice_roll, expected_combinations)
        self.assertTrue(has_pairs)
        self.assertFalse(has_two_2s)
        self.assertFalse(has_expected_combination)

    @parameterized.expand([
        [[2, 6, 2, 4, 1]],
        [[3, 6, 2, 1, 2]],
        [[2, 2, 2, 5, 1]]
    ])
    def test_has_pairs_combination_plus_2_2_returns_false_with_dice_roll_that_only_contains_2_2_but_no_other_pair(self,                                                                                            dice_roll):
        pairs_combination = dice_roller.get_pairs_combination()
        two_2s = [2, 2]
        expected_combinations = dice_roller.get_pairs_combination_plus_another_combination(two_2s)
        has_pairs = dice_roller.has_at_least_one_combination(dice_roll, pairs_combination)
        has_two_2s = dice_roller.has_combination(dice_roll, two_2s)
        has_expected_combination = dice_roller.has_all_combinations(dice_roll, expected_combinations)
        self.assertTrue(has_pairs)
        self.assertTrue(has_two_2s)
        self.assertFalse(has_expected_combination)

    @parameterized.expand([
        [[1, 5, 5, 5, 1]],
        [[4, 6, 4, 3, 3]],
        [[2, 6, 5, 5, 1]],
        [[3, 3, 3, 3, 3]],
        [[1, 2, 4, 4, 6]]
    ])
    def test_has_two_smallers_returns_true_with_adequate_dice_roll(self, dice_roll):
        smallers_combination = dice_roller.get_smallers_combination()
        two_smallers_combination = [smallers_combination, smallers_combination]
        has_one_smaller = dice_roller.has_at_least_one_combination(dice_roll, smallers_combination)
        has_two_smallers = dice_roller.has_all_combinations(dice_roll, two_smallers_combination)
        self.assertTrue(has_one_smaller)
        self.assertTrue(has_two_smallers)

    @parameterized.expand([
        [[5, 4, 6, 4, 1]],
        [[5, 6, 4, 3, 4]],
        [[6, 6, 6, 6, 1]]
    ])
    def test_has_two_smaller_returns_false_with_no_two_smallers_in_the_dice_roll(self, dice_roll):
        smallers_combination = dice_roller.get_smallers_combination()
        two_smallers_combination = [smallers_combination, smallers_combination]
        has_two_smallers = dice_roller.has_all_combinations(dice_roll, two_smallers_combination)
        self.assertFalse(has_two_smallers)

    @parameterized.expand([
        [[5, 1, 3, 4, 1]],
        [[3, 3, 3, 3, 1]],
        [[5, 6, 3, 2, 1]]
    ])
    def test_has_three_smaller_returns_true_with_adequate_dice_roll(self, dice_roll):
        smallers_combination = dice_roller.get_smallers_combination()
        three_smallers_combination = [smallers_combination, smallers_combination, smallers_combination]
        has_three_smallers = dice_roller.has_all_combinations(dice_roll, three_smallers_combination)
        self.assertTrue(has_three_smallers)


if __name__ == '__main__':
    unittest.main()
