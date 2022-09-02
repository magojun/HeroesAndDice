import random

def roll_die():
    return random.randint(1, 6)

def roll_dice(number_of_dice = 5):
    dice_roll = []
    for n in range(number_of_dice):
        dice_roll.append(roll_die())
    print(dice_roll)
    print(combination_detected(dice_roll))
    return dice_roll

def combination_detected(dice_roll):
    detected = False
    if [2, 2] in dice_roll:
        detected = True
    return detected

if __name__ == '__main__':
    for n in range(10):
        roll_dice()

