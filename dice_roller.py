import pandas as pd
from copy import copy
from dice import *

def get_pairs_combination_plus_another_combination(second_dice_combination):
    pairs_combination = get_pairs_combination()
    return [second_dice_combination, pairs_combination]


def roll_die():
    return RegularDice()


def roll_dice(number_of_dice=5, number_of_special_dice=1):
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


def get_smallers_combination():
    return [[1], [2], [3]]


def found_combinations(dice_roll, dice_combinations):
    combinations_found = []
    for combination in dice_combinations:
        result = find_combination(dice_roll, combination)
        if type(result) is list and len(result) > 0:
            combinations_found.append(result)
    return combinations_found


def has_at_least_one_combination(dice_roll, dice_combinations):
    return any([has_combination(dice_roll, combination)
                for combination in dice_combinations])


def has_all_combinations(dice_roll, dice_combinations):
    # TODO - some refactoring would improve this method.
    dice_roll = copy(dice_roll)  # Avoid updating the actual dictionary elements.
    combinations_found = []
    any_problem = False
    for combination in dice_combinations:
        if any(isinstance(combination_set, list) for combination_set in combination):
            result_found = found_combinations(dice_roll, combination)
            combinations_found.append(result_found)
            if has_at_least_one_combination(dice_roll, combination) is False:
                any_problem = True
            one_case_removed = False
            for one_result in result_found:
                if not one_case_removed and type(one_result) is list and len(one_result) > 0:
                    # TODO - take this to an external function.
                    for result in one_result:
                        for die in dice_roll:
                            if result == die:
                                dice_roll.remove(die)
                                one_case_removed = True
                                break
        else:
            result_found = find_combination(dice_roll, combination)
            combinations_found.append(result_found)
            if has_combination(dice_roll, combination) is False:
                any_problem = True
            if type(result_found) is list and len(result_found) > 0:
                # TODO - take this to an external function.
                for result in result_found:
                    for die in dice_roll:
                        if result == die:
                            dice_roll.remove(die)
                            break
    return True if any_problem is False else False

def find_combination(dice_roll, dice_combination):
    dice_roll = copy(dice_roll)  # Avoid updating the actual dictionary elements.
    combination_found = []
    for combination in dice_combination:
        for die in dice_roll:
            if combination == die:
                dice_roll.remove(die)
                combination_found.append(die)
                break
    return combination_found if combination_found == dice_combination else []

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


def get_statistics(dice_combinations, sample=False):
    # TODO Untested.
    max_range = 10000 if sample is True else 2000000
    results = []
    for i in range(max_range):
        print("Reached:", i) if i == 100000 else None
        print("Reached:", i) if i == 500000 else None
        print("Reached:", i) if i == 800000 else None
        print("Reached:", i) if i == 1000000 else None
        print("Reached:", i) if i == 1200000 else None
        print("Reached:", i) if i == 1500000 else None
        print("Reached:", i) if i == 1800000 else None
        dice = roll_dice()
        result = has_all_combinations(dice, dice_combinations)
        if result and i < 1000:
            print("Positive Case:", dice)
        if not result and 1000 < i < 2000:
            print("Negative Case:", dice)
        results.append(result)
    statistics_series = pd.Series(results)
    if i < 20:
        print(results)
    average = round(statistics_series.mean() * 100, 2)
    print("Average is: %s%%" % average)
    print("Number of iterations:", statistics_series.count())
    return statistics_series


if __name__ == '__main__':
    #get_statistics(get_pairs_combination_plus_another_combination([1, 2, 3]))
    get_statistics([get_smallers_combination(), get_smallers_combination(), [2, 2]])
