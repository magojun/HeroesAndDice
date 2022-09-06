import random
import pandas as pd
from copy import copy


def get_pairs_combination_plus_another_combination(second_dice_combination):
    pairs_combination = get_pairs_combination()
    return [second_dice_combination, pairs_combination]


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

def found_combinations(dice_roll, dice_combinations):
    return any([has_combination(dice_roll, combination)
                for combination in dice_combinations])

def has_at_least_one_combination(dice_roll, dice_combinations):
    return any([has_combination(dice_roll, combination)
                for combination in dice_combinations])


def has_all_combinations(dice_roll, dice_combinations):
    #dice_roll = copy(dice_roll)  # Avoid updating the actual dictionary elements.
    #for combination in dice_combinations:
    #    if any(isinstance(element, list) for element in combination):
    #        result = has_at_least_one_combination(dice_roll, combination)
    #    else:
    #        result = has_combination(dice_roll, combination)
    #    if result:
    #        dice_roll.remove(combination)
    #return result
    return all([has_at_least_one_combination(dice_roll, combination)
                if any(isinstance(combination_set, list) for combination_set in combination)
                else has_combination(dice_roll, combination)
                for combination in dice_combinations])

def find_combination(dice_roll, dice_combination):
    dice_roll = copy(dice_roll)  # Avoid updating the actual dictionary elements.
    combination_found = []
    for combination in dice_combination:
        for die in dice_roll:
            if combination == die:
                dice_roll.remove(die)
                combination_found.append(die)
                break
    return combination_found

def has_combination(dice_roll, dice_combination):
    """
    Receives a dice roll list and a list with a dice combination.
    I you require a list of lists with several dice combinations,
    use :meth:has_all_combinations or :meth:has_at_least_one_combination
    :param dice_roll:
    :param dice_combination:
    :return: Returns true if the dice combination is present in the dice roll.
    """
    # TODO if it's a list of lists fail -> if any(isinstance(combination, list) for combination in dice_combination): throw error
    return True if find_combination(dice_roll, dice_combination) == dice_combination else False


def get_statistics(dice_combinations):
    # TODO Untested.
    results = []
    for i in range(5):
        print("Reached:", i) if i == 100000 else None
        print("Reached:", i) if i == 500000 else None
        print("Reached:", i) if i == 800000 else None
        print("Reached:", i) if i == 1000000 else None
        print("Reached:", i) if i == 1200000 else None
        print("Reached:", i) if i == 1500000 else None
        print("Reached:", i) if i == 1800000 else None
        dice = roll_dice()
        results.append(has_all_combinations(dice, dice_combinations))
        print(dice)
    statistics_series = pd.Series(results)
    if i < 20:
        print(results)
    average = round(statistics_series.mean() * 100, 2)
    print("Average is: %s%%" % average)
    print("Number of iterations:", statistics_series.count())
    return statistics_series


if __name__ == '__main__':
    get_statistics(get_pairs_combination_plus_another_combination([2, 2]))


# 2, 2, plus pairs -> 19%
#1, 2, 3 + pairs -> 11.19%
