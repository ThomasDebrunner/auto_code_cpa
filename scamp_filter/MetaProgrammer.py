from math import log2
from collections import Counter

class MetaInstruction:
    def __init__(self, source, target):
        self.source = source
        self.target = target


class MoveMetaIntstruction(MetaInstruction):
    def __init__(self, source, target, scale, shift, neg=False):
        super().__init__(source, target)
        self.scale = scale
        self.shift = shift
        self.neg = neg

    def length(self):
        return abs(self.scale) + abs(self.shift[0]) + abs(self.shift[1]) + self.neg

    def cost(self):
        return self.length()

    def __str__(self):
        dirs = []
        if self.shift[0] < 0:
            dirs.append(('\u2192', abs(self.shift[0])))  # right
        if self.shift[0] > 0:
            dirs.append(('\u2190', abs(self.shift[0])))  # left
        if self.shift[1] < 0:
            dirs.append(('\u2191', abs(self.shift[1])))  # up
        if self.shift[1] > 0:
            dirs.append(('\u2193', abs(self.shift[1])))  # down
        if self.scale > 0:
            dirs.append(('+', abs(self.scale)))
        if self.scale < 0:
            dirs.append(('-', abs(self.scale)))

        s = ('m [%d]->[%d] || ' % (self.source, self.target)) + '  '.join(['%s (%d)' % (s, a) for s, a in dirs])
        if self.neg:
            s = s + '  ¬'
        return s

    def __repr__(self):
        return self.__str__()


class AddMetaInstruction(MetaInstruction):
    def __init__(self, source1, source2, s1neg, s2neg, target):
        super().__init__(source1, target)
        self.source2 = source2
        self.s1neg = s1neg
        self.s2neg = s2neg

    def cost(self):
        return 1

    def __str__(self):
        if self.s1neg:
            a, b, op = self.source2, self.source, '-'
        elif self.s2neg:
            a, b, op = self.source, self.source2, '-'
        else:
            a, b, op = self.source, self.source2, '+'

        return '+ [%d]%s[%d]->[%d]' % (a, op, b, self.target)

    def __repr__(self):
        return self.__str__()


def get_shift(pair):
    """Return the distance from goal 1 to goal 2, -1 if the goals are not similar"""
    down, up = pair
    ratio = len(down)/len(up)
    scale = int(log2(ratio))
    # identify the distinct values
    down, up = Counter([a.val() for a in down]), Counter([a.val() for a in up])

    if len(up) != len(down):
        raise ValueError('[Error] Invalid pair. No shift possible: ' + str(pair))

    lower_pivot = next(iter(down.keys()))
    lower_pivot_count = down[lower_pivot]
    lower_pivot_x, lower_pivot_y, lower_pivot_neg = lower_pivot
    for (upper_pivot_x, upper_pivot_y, upper_pivot_neg), upper_pivot_count in up.items():
        if upper_pivot_count * ratio != lower_pivot_count:
            continue
        distance_x, distance_y, distance_neg = \
            upper_pivot_x-lower_pivot_x, upper_pivot_y-lower_pivot_y, upper_pivot_neg != lower_pivot_neg
        # For the distance of the selected pivots, we must find a mapping for all remaining atoms
        # if not, the pivot selection was wrong and we select another pivot (break)
        for lower_x, lower_y, lower_neg in down.keys():
            if (lower_x+distance_x, lower_y+distance_y, lower_neg != distance_neg) not in up.keys():
                break
        else:
            return scale, (distance_x, distance_y), distance_neg
    raise ValueError('[Error] Invalid pair. No shift possible: ' + str(pair))


def find_goal_in_reg(reg_state, needle_goal):
    for reg, goal in reg_state.items():
        if goal == needle_goal:
            return reg
    return -1


def generate_meta_program(plan):
    meta_program = []

    prev_reg_state = {
        0: plan[0].pair[0]  # assign initial state
    }

    next_reg = 1

    for step in plan:

        trivial = set()
        new_reg_state = {}

        non_trivial_goals = []
        # consider all trivial goals
        for i, goal in enumerate(step.goals):
            # if the goal is a goal we had before, just leave it in same register, nothing else to be done
            prev_reg = find_goal_in_reg(prev_reg_state, goal)
            if prev_reg >= 0:
                new_reg_state[prev_reg] = goal
                trivial.add(prev_reg)
            else:
                non_trivial_goals.append(goal)
        if len(non_trivial_goals) == 0:
            continue
        if len(non_trivial_goals) > 2:
            print('[ERROR] Wrong number of non-trivial goals per step')
            return

        # analyze non trivial goals
        # A non trivial goal is either:
        # - sum of two previous goals plus a shift of a previous goal
        # - sum of one previous goals plus a shift of a previous goal
        # - shift of a previous goal.
        # - sum of two previous goals
        # There can be only one non-trivial goal with a shift, and only one without shift
        # We have to perform the non-trivial goal without shift first

        shift_gen_set = step.pair[1]
        shift_source = find_goal_in_reg(prev_reg_state, step.pair[0])
        if shift_source == -1:
            print('[ERROR] Could not construct new register state from previous register state. (No shift gen)')


        goal_props = []
        for goal in non_trivial_goals:
            # grab all the previous goals that are subsets of this goal (max. 2)
            subset_sources = set()
            shift_portion = goal
            for reg, prev_goal in prev_reg_state.items():
                if prev_goal.issubset(goal):
                    subset_sources.add(reg)
                    shift_portion = shift_portion.difference(prev_goal)
            if shift_portion and shift_portion != shift_gen_set and shift_portion | step.pair[0] != shift_gen_set:
                print('[ERROR] Could not construct new register state from previous state (shift gen do not match)')
            goal_props.append((False if not shift_portion else True, subset_sources, goal))

        # separate the shift goal from the non-shift goal
        goal_props.sort(key=lambda x: x[0])

        # if we have a non-shift non-trivial goal, apply that first
        if len(goal_props) > 1:  # we have both, non shift and shift
            _, non_shift_subset_sources, goal = goal_props[0]
            s1, s2 = tuple(non_shift_subset_sources)
            # find a target
            t = next_reg
            next_reg += 1
            meta_program.append(AddMetaInstruction(s1, s2, False, False, t))
            new_reg_state[t] = goal

        # the second part is now the shift non-trivial goal
        _, shift_subset_sources, shift_goal = goal_props[-1]
        scale, shift, polarity = get_shift(step.pair)
        # if we have a zero distance shift, we have to remove the shift source from the subset sources, as this
        # is no longer a subset source, but results from the scaling (move)
        if not polarity and shift[0] == 0 and shift[1] == 0 and shift_source in shift_subset_sources:
            shift_subset_sources.remove(shift_source)

        # if we have two subset sources, it uses less registers to add them together first. Otherwise, do shift first
        if len(shift_subset_sources) < 2 or shift_subset_sources.issubset(trivial):
            target = next_reg
            next_reg += 1
            # if we do not do any adds later on, we have to do a potential inversion in the move step
            meta_program.append(MoveMetaIntstruction(shift_source, target, scale, shift, (len(shift_subset_sources) == 0) and polarity))
            prev_polarity = polarity

            for subset_source in shift_subset_sources:
                prev_target = target
                target = next_reg
                next_reg += 1
                meta_program.append(AddMetaInstruction(subset_source, prev_target, False, prev_polarity, target))
                prev_polarity = False

        else:
            s1, s2 = tuple(shift_subset_sources)
            sub_target = next_reg
            next_reg += 1
            meta_program.append(AddMetaInstruction(s1, s2, False, False, sub_target))
            shift_target = next_reg
            next_reg += 1
            meta_program.append(MoveMetaIntstruction(shift_source, shift_target, scale, shift))
            target = next_reg
            next_reg += 1
            meta_program.append(AddMetaInstruction(sub_target, shift_target, False, polarity, target))

        new_reg_state[target] = shift_goal
        prev_reg_state = new_reg_state

    return meta_program