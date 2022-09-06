import random
from copy import copy


def roll_die():
    return random.randint(1, 6)


def roll_dice(number_of_dice=5):
    dice_roll = []
    for i in range(number_of_dice):
        dice_roll.append(roll_die())
    return dice_roll


def get_pairs_combination():
    pairs_combination = []
    one_pairs = [1, 1]
    two_pairs = [2, 2]
    three_pairs = [3, 3]
    four_pairs = [4, 4]
    five_pairs = [5, 5]
    six_pairs = [6, 6]

    pairs_combination.append(one_pairs)
    pairs_combination.append(two_pairs)
    pairs_combination.append(three_pairs)
    pairs_combination.append(four_pairs)
    pairs_combination.append(five_pairs)
    pairs_combination.append(six_pairs)
    return pairs_combination


def has_at_least_one_combination(dice_roll, dice_combinations):
    return any([has_combination(dice_roll, combination)
                for combination in dice_combinations])


def has_all_combinations(dice_roll, dice_combinations):
    return all([has_at_least_one_combination(dice_roll, combination)
                if any(isinstance(combination_set, list) for combination_set in combination)
                else has_combination(dice_roll, combination)
                for combination in dice_combinations])


def has_combination(dice_roll, dice_combination):
    # TODO if it's a list of lists fail -> if any(isinstance(combination, list) for combination in dice_combination): throw error
    dice_roll = copy(dice_roll)  # Avoid updating the actual dictionary elements.
    combination_found = []
    for combination in dice_combination:
        for die in dice_roll:
            if combination == die:
                dice_roll.remove(die)
                combination_found.append(die)
                break
    return True if combination_found == dice_combination else False


if __name__ == '__main__':
    for n in range(10):
        roll_dice()
