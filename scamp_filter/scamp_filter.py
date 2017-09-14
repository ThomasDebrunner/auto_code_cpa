from scamp_filter.Item import Atom as A
import scamp_filter.Programmer as Programmer
import scamp_filter.Simulator as Simulator
import scamp_filter.MetaTransform as MetaTransform
import scamp_filter.Grapher as Grapher
import scamp_filter.RegAlloc as RegAlloc
from scamp_filter.costs import operation_cost
from scamp_filter.Latexer import latexify_goal, print_filter
from scamp_filter.approx import approx_filter
import time
from scamp_filter.pair_gen import generate_pairs, generate_pairs_gen, translate_back_set, translate_goal
import random
from termcolor import colored

L_INT = 1e6

class PlanStep:
    def __init__(self, goals, pair):
        self.goals = goals
        self.pair = pair

    def __str__(self):
        return str(self.goals) + '   |   ' + str(self.pair[0]) + ' > ' + str(self.pair[1])


class SolutionStats:
    def __init__(self, start_time):
        self.sols = []
        self.start_time = start_time

    def log_solution(self, cost):
        self.sols.append((time.time()-self.start_time, cost))


class PairGenProps:
    def __init__(self, sort_distinct_pos, short_distance_first, low_scale_first, max_sets, exhaustive, line, generate_all, randomize, log_all=True):
        self.sort_distinct_pos = sort_distinct_pos
        self.short_distance_first = short_distance_first
        self.low_scale_first = low_scale_first
        self.exhaustive = exhaustive
        self.line = line
        self.generate_all = generate_all
        self.max_sets = max_sets
        self.randomize = randomize
        self.log_all = log_all



def _end_state(goal):
    """An end state is reached when all atoms in the goal are at the same position"""
    pivot_atom = next(iter(goal))
    px, py, pneg = pivot_atom.x, pivot_atom.y, pivot_atom.neg
    for a in goal:
        if a.x != px or a.y != py or a.neg != pneg:
            return False
    return True


def _last_cost(goal, scale):
    cost = 0
    items = translate_back_set(goal, scale)
    for item in items:
        cost += (abs(item.x) + abs(item.y)) * operation_cost['shift']
        if item.scale > 0:
            cost += item.scale * operation_cost['div']
        else:
            cost += abs(item.scale) * operation_cost['double']
        if item.neg and len(items) == 1:
            cost += 1
    return cost


def _not_equal_goals(goals1, goals2):
    """Return true, if the goals are equal"""
    for s in goals1:
        if s not in goals2:
            return True
    return False


def _generate_initial_state(scale, initial_step):
    """Generates the initial state, making sure that all ids at zero position in the initial step are present"""
    if len(initial_step) != 1:
        raise ValueError('[Error] Initial step should have length 1')
    initial_set = initial_step[0]
    gen_id_start = 1e6
    n_initial = 2 ** scale
    initial = {a for i, a in enumerate(initial_set) if a.x == 0 and a.y == 0 and a.neg == False and i < n_initial}
    return initial | {A(gen_id_start + i, 0, 0) for i in range(n_initial-len(initial))}



def _search(final_goal, n_reg, search_time, scale, pair_props):
    """Driver function for the search algorithm"""
    end_time = search_time + time.time()
    plans = []

    print(colored('>> Searching for plans...', 'magenta'))
    # we have one less reg available for intermediate results, as we need a reg for shifting in the generation phase
    sol_stats = SolutionStats(time.time())
    min_cost = _r_search([final_goal], n_reg, [], plans, 0, float('inf'), end_time, scale, sol_stats, pair_props)
    for plan in plans:
        plan[1].reverse()
    print(colored('\n...Done', 'yellow'))
    return plans, sol_stats


def _r_search(goals, n_reg, plan, plans, cost_acc, min_cost, end_time, scale, sol_stats, pair_props):
    """Recursive function that searches for all the plans"""

    # if we only have one goal with one item left, we found a solution
    if len(goals) == 1 and _end_state(goals[0]):
        total_cost = cost_acc + _last_cost(goals[0], scale)
        if pair_props.log_all:
            sol_stats.log_solution(total_cost)

        if total_cost <= min_cost:
            if not pair_props.log_all:
                sol_stats.log_solution(total_cost)
            # append first step to plan
            plan.append(PlanStep(goals, (_generate_initial_state(scale, goals), goals[0])))
            plans.append((total_cost, plan))
            if total_cost < min_cost:
                print('\r>>> minimum cost found %d ' % total_cost, end='', flush=True)
            return total_cost
        return min_cost

    # compute pairs
    if pair_props.generate_all:
        pairs = generate_pairs(goals, pair_props)
        if pair_props.randomize:
            random.shuffle(pairs)
    else:
        pairs = generate_pairs_gen(goals, pair_props)

    # choose a pair
    for cost, (up_set, down_set) in pairs:
        # compute rests
        eliminator = up_set | down_set
        new_goals = []
        for goal in goals:
            new_goal = goal.difference(eliminator)
            if len(new_goal) > 0:
                new_goals.append(new_goal)
            # if we generate a rest term, we have to add that one in this step as well
            step_cost = cost + operation_cost['add'] if len(new_goals) > len(goals) else cost

        new_goals.append(down_set)
        # only continue to search here, if we can hold this many sub results in registers
        if len(new_goals) <= n_reg and cost_acc+step_cost < min_cost and _not_equal_goals(goals, new_goals):
            min_cost = _r_search(new_goals, n_reg, plan + [PlanStep(goals, (down_set, up_set))], plans, cost_acc + step_cost, min_cost, end_time, scale, sol_stats, pair_props)
            if end_time < time.time():
                return min_cost
    return min_cost


def generate(filter, search_time, available_regs=('A', 'B', 'C'), start_reg='A', target_reg='B', verbose=1, pair_props=None, approx_depth=5, max_approx_coeffs=-1):
    """Generates a SCAMP program for the given filter"""
    if pair_props is None:
        pair_props = PairGenProps(
            sort_distinct_pos=True,
            short_distance_first=True,
            low_scale_first=True,
            exhaustive=False,
            line=True,
            generate_all=True,
            max_sets=True,
            randomize=False)

    available_regs = list(available_regs)
    n_reg = len(available_regs) - 1

    pre_goal, _ = approx_filter(filter, depth=approx_depth, max_coeff=max_approx_coeffs, verbose=verbose)

    scale = max(max(pre_goal, key=lambda i: i.scale).scale, 0)
    final_goal, _ = translate_goal(pre_goal, scale)

    if verbose > 0:
        print(colored('>> Pre goal', 'yellow'))
        print(pre_goal)
        print(colored('>> Goal with %d atoms..' % len(final_goal), 'yellow'))
        print(latexify_goal(final_goal))


    plans, sol_stats = _search(final_goal, n_reg=n_reg, search_time=search_time, scale=scale, pair_props=pair_props)

    if len(plans) == 0:
        raise ValueError('[Error] No plans found')

    # sort the plans according to cost
    cheapest_cost = min(plans, key=lambda x: x[0])[0]
    best_plans = [plan for plan in plans if plan[0] == cheapest_cost]
    if verbose > 0:
        print('... Found %d plans with approx. cost %d ' % (len(best_plans), cheapest_cost))

    if verbose > 1:
        print(colored('>> Best plan', 'yellow'))
        for step in best_plans[0][1]:
            print(step)

    if verbose > 0:
        print(colored('>> Generating meta programs', 'magenta'))
    meta_programs = []
    for i, (_, best_plan) in enumerate(best_plans):
        if i == 1:
            break
        meta_program = Programmer.generate_meta_program(best_plan)
        cost = sum(x.cost() for x in meta_program)
        if verbose > 0:
            print(colored('| ... Meta program with %d steps generated. Cost: %d' % (len(meta_program), cost), 'yellow'))

        meta_program = MetaTransform.eliminate_empty_shifts(meta_program)

        if verbose > 9:
            Grapher.print_meta_program(meta_program, verbose>10, title='Computational graph before relaxation')

        if verbose > 0:
            print('')
            print(colored('| >> Relaxing meta program', 'magenta'))
        while True:
            meta_program = MetaTransform.relax_same_shift(meta_program, n_reg)
            new_cost = sum(x.cost() for x in meta_program)
            meta_program = MetaTransform.relax_rebalance(meta_program, n_reg)
            new_cost = sum(x.cost() for x in meta_program)
            if new_cost >= cost:
                break
            cost = new_cost

        if verbose > 0:
            print(colored('| ... Done. New cost: %d' % cost, 'yellow'))

        meta_programs.append((cost, meta_program))
        if verbose > 0:
            print('')

    meta_programs.sort(key=lambda x: x[0])
    # get the cheapest meta program
    cost, meta_program = meta_programs[0]
    if verbose > 0:
        print(colored('... Cheapest meta program has cost %d' % cost, 'yellow'))

    if verbose > 9:
        Grapher.print_meta_program(meta_program, verbose>10, title='Computational graph after relaxation')
    if verbose > 3:
        for step in meta_program:
            print(step)

    if verbose > 0:
        print(colored('>> Performing register allocation', 'magenta'))
    meta_program = RegAlloc.alloc(meta_program, n_reg+1, verbose)
    if verbose > 0:
        print(colored('... Done', 'yellow'))

    if verbose > 4:
        for step in meta_program:
            print(step)

    if verbose > 0:
        print(colored('>> Generating SCAMP code', 'magenta'))
    program = Programmer.generate_scamp_program(meta_program, available_regs, start_reg, target_reg)
    if verbose > 0:
        print(colored('... SCAMP code with %d instructions generated' % len(program), 'yellow'))

    if verbose > 2:
        for step in program:
            print(step)

    if verbose > 0:
        print(colored('>> Validating SCAMP code', 'magenta'))
    # validate
    if Simulator.validate(program, pre_goal, start_reg, target_reg):
        if verbose > 0:
            print(colored('\U0001F37A Validation succeeded', 'green'))
    else:
        raise AssertionError('[Error] Code validation failed')

    return program, sol_stats