import numpy as np
from math import log2
from scamp_filter.Item import Item as I
from termcolor import colored

def approx(target, depth=5, max_coeff=-1, silent=True):
    coeffs = {}

    total = 0.0

    current = 256

    for i in range(-8, depth):

        if total == target:
            break

        # if the error is smaller than half the current coefficient, we go further away from target
        if abs(total - target) > 1/2 * current:

            # decide which direction brings us closer to the target
            if abs((total-current)-target) > abs(total + current - target):
                coeffs[current] = 1
                total += current

            else:
                coeffs[current] = -1
                total -= current
        current /= 2

        if max_coeff > 0 and len(coeffs) >= max_coeff:
            break

    if not silent:
        print("Target: %.5f\n" % target)
        print("Error: %.5f\n" % (total-target))
        print(coeffs)

    return total, coeffs


def print_filter(filter):
    print('----------------------')
    for row in filter:
        for item in row:
            print('%5s'%str(item), end='  ')
        print('')
    print('----------------------')


def approx_filter(filter, depth=4, max_coeff=-1, verbose=0):
    if verbose>1:
        print(colored('>> Input filter', 'yellow'))
        print_filter(filter)

    if verbose>0:
        print(colored('>> Approximating Filter', 'magenta'))

    pre_goal = []
    h, w = filter.shape
    approximated_filter = np.zeros(filter.shape)
    for (y, x), val in np.ndenumerate(filter):
        a, coeffs = approx(val, depth, silent=True, max_coeff=max_coeff)
        approximated_filter[y, x] = a
        pre_goal = pre_goal + [I(int(-log2(c)), x-w//2, h//2-y) if weight == 1 else -I(int(-log2(c)), x-w//2, h//2-y) for c, weight in coeffs.items()]

    if verbose>1:
        print(colored('>> Approximated filter', 'yellow'))

        print_filter(approximated_filter)

    return pre_goal, approximated_filter

def filter_from_pre_goal(pre_goal):
    min_x = min(pre_goal, key=lambda item: item.x).x
    max_x = max(pre_goal, key=lambda item: item.x).x
    min_y = min(pre_goal, key=lambda item: item.y).y
    max_y = max(pre_goal, key=lambda item: item.y).y

    width = max_x - min_x + 1
    height = max_y - min_y + 1

    filter = np.zeros((height, width))

    for item in pre_goal:
        filter[height - 1 - (item.y - min_y), item.x - min_x] += (-1 if item.neg else 1) * (2**(-item.scale))
    return filter



