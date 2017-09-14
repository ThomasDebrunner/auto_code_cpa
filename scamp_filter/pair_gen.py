from .Item import Atom as A
from .Item import Item as I
from operator import itemgetter
from itertools import groupby
from .costs import operation_cost
from itertools import chain
from math import log2
L_INT = 1e6


class ElemMove:
    def __init__(self, sources, targets, n_sources, n_targets, move):
        self.sources = sources
        self.targets = targets
        self.n_sources = n_sources
        self.n_targets = n_targets
        self.move = move

    def __str__(self):
        return ('take %d generate %d'%(self.n_sources, self.n_targets)) + ' from ' + str(self.sources) + ' to ' + str(self.targets)


def translate_goal(igoal, scale, nr_offset=0):
    agoal = set()
    nr = nr_offset
    for item in igoal:
        n_atoms = 2**(scale - item.scale)
        agoal = agoal | {A(i, item.x, item.y, item.neg) for i in range(nr, nr+n_atoms)}
        nr += n_atoms
    return agoal, nr


def get_scales(acc, scale):
    """Returns the item scales required to get the accumulator value given the global scale"""
    res = []
    i = scale
    while acc > 0:
        if acc & 1:
            res.append(i)
        acc >>= 1
        i -= 1
    return res


def translate_back_set(s, scale):
    if not s:
        return set()
    s = list(s)
    s.sort(key=lambda i: (i.x, i.y))
    o_x, o_y, o_p = s[0].x, s[0].y, s[0].neg
    acc = 0
    ns = set()
    for item in s:
        if o_x != item.x or o_y != item.y or o_p != item.neg:
            ns = ns | {I(s, o_x, o_y, o_p) for s in get_scales(acc, scale)}
            acc = 1
            o_x, o_y, o_p = item.x, item.y, item.neg
        else:
            acc += 1
    ns = ns | {I(s, o_x, o_y, o_p) for s in get_scales(acc, scale)}
    return ns


def translate_back_plan(aplan, scale):
    return [[translate_back_set(s, scale) for s in step] for step in aplan]


def distinct_pos(s):
    """Returns the amount of distinct positions that are present in the goal"""
    seen = set()
    pos = 0
    for atom in s:
        key = atom.val()
        if key not in seen:
            pos += 1
            seen.add(key)
    return pos


def get_distances(s1, s2):
    """Returns the distances from every atom to every other in the given set"""
    distances = []
    for a in s1:
        for b in s2:
            x, y, p = a.x - b.x, a.y - b.y, a.neg != b.neg
            distances.append(((x, y, p), (a, b)))
    return distances


def generate_elementary_moves(group):
    # form clusters. A cluster is the set of all tuples in a group that have same start and end coord
    clusters = {}
    for (a, b) in group:
        key = (a.val(), b.val())
        if key in clusters:
            clusters[key].append((a, b))
        else:
            clusters[key] = [(a, b)]

    emoves = []
    for key, cluster in clusters.items():
        sources, targets = {a.nr for a, _ in cluster}, {b.nr for _, b in cluster}
        for n_sources in range(int(log2(len(sources)))+1):
            for n_targets in range(int(log2(len(targets)))+1):
                if n_sources != n_targets or sources != targets:
                    emoves.append(ElemMove(sources, targets, 2**n_sources, 2**n_targets, key))
    return emoves


def group_emoves(emoves, props):
    # group the emoves by ratio
    emoves.sort(key=lambda x: x.n_sources/x.n_targets)
    emovemap = {ratio: list(emove) for ratio, emove in groupby(emoves, key=lambda x: x.n_sources/x.n_targets)}
    ratios = list(emovemap.keys())
    # consider non-scales first -> ratio of 1 first
    if props.low_scale_first:
        ratios.sort(key=lambda x: abs(log2(x)))

    for ratio in ratios:
        if ratio < 1:
            continue
        ratio_emoves = emovemap[ratio]

        # we generate the a list of possible allocations to the emoves, that work to form a possible pair
        line_gen = _group_emoves_lines(ratio_emoves, ratio)
        exhaust_gen = _group_emoves_exhaust(ratio_emoves, 0, set(), props)

        if props.exhaustive and props.line:
            gen = chain(line_gen, exhaust_gen)
        elif props.exhaustive:
            gen = exhaust_gen
        else:
            gen = line_gen

        # generate the actual pair out of the emove allocation
        for emove_alloc in gen:
            if emove_alloc is None:
                continue
            up, down = set(), set()
            for (emove, sources, targets) in emove_alloc:
                (lx, ly, lneg), (hx, hy, hneg) = emove.move
                up |= {A(nr, lx, ly, lneg) for nr in sources}
                down |= {A(nr, hx, hy, hneg) for nr in targets}
            yield (up, down)


def _group_emoves_exhaust(emoves, pos, used_nrs, props):
    """Exhaustively groups emoves to all possible sets"""
    if pos >= len(emoves):
        return []

    emove = emoves[pos]
    # allocate
    source_candidates = list(emove.sources.difference(used_nrs))
    target_candidates = list(emove.targets.difference(used_nrs))

    # assume not taking it
    yield from _group_emoves_exhaust(emoves, pos+1, used_nrs, props)
    # take it, if possible
    if len(source_candidates) >= emove.n_sources and len(target_candidates) >= emove.n_targets:
        sources = {source_candidates[i] for i in range(emove.n_sources)}
        targets = {target_candidates[i] for i in range(emove.n_targets)}
        take_plans = _group_emoves_exhaust(emoves, pos+1, used_nrs | sources | targets, props)
        for plan in take_plans:
            yield [(emove, sources, targets)] + plan
        if len(sources) == len(source_candidates) and len(targets) == len(target_candidates) or not props.max_sets:
            yield [(emove, sources, targets)]


def _group_emoves_lines(emoves, ratio):
    """Tries to group emoves in a way that they form compact clusters"""
    # detect movement
    s_pos, t_pos = emoves[0].move
    x_mov, y_mov = s_pos[0] - t_pos[0], s_pos[1] - t_pos[1]
    # if we only have x movement, prefer to have emoves in same row
    if x_mov == 0:
        emoves.sort(key=lambda x: (x.move[0][1], x.move[0][0], -x.n_sources))

    # else, prefer have emoves in same column
    else:
        emoves.sort(key=lambda x: (x.move[0][0], x.move[0][1], -x.n_sources))

    used = set()
    plan = []
    # go through the emoves, and add them all
    for i, emove in enumerate(emoves):
        source_candidates = list(emove.sources.difference(used))
        target_candidates = list(emove.targets.difference(used))

        if len(source_candidates) >= emove.n_sources and len(target_candidates) >= emove.n_targets:
            sources = {source_candidates[i] for i in range(emove.n_sources)}
            targets = {target_candidates[i] for i in range(emove.n_targets)}
            used = used | sources | targets
            plan.append((emove, sources, targets))
    yield plan


def form_pairs(goal1, goal2, props):
    """Looks for sets of atoms with the same distances"""

    distances = get_distances(goal1, goal2)

    distances.sort(key=itemgetter(0))
    groups = {}
    # group the ones with the same distance
    for dist, s in groupby(distances, key=itemgetter(0)):
        groups[dist] = [t for _, t in s]

    dists = list(groups.keys())
    if props.short_distance_first:
        dists.sort(key=lambda x: sum(abs(i) for i in x))

    for dist in dists:
        group = groups[dist]

        base_cost = operation_cost['add'] + (abs(dist[0]) + abs(dist[1])) * operation_cost['shift'] + \
                    (operation_cost['neg'] if dist[0] == 0 and dist[1] == 0 and dist[2] else 0)

        emoves = generate_elementary_moves(group)
        pairs = group_emoves(emoves, props)

        for pair in pairs:
            if len(pair[0]) > len(pair[1]):
                scale_cost = (log2(len(pair[0])/len(pair[1]))) * operation_cost['double']
            else:
                scale_cost = (log2(len(pair[1]) / len(pair[0]))) * operation_cost['div']
            yield (base_cost + scale_cost, pair)


def generate_pairs(agoals, props):
    """Forms all the pairs that are applicable to the current goals"""
    all_pairs = []
    for i in range(0, len(agoals)):
        for j in range(i, len(agoals)):
            goal1, goal2 = agoals[i], agoals[j]
            all_pairs.extend(list(form_pairs(goal1, goal2, props)))
    if props.sort_distinct_pos:
        all_pairs.sort(key=lambda p: distinct_pos(set.union(*agoals).difference(p[1][0]) | p[1][1]))
    return all_pairs


def generate_pairs_gen(agoals, props):
    """Forms all the pairs that are applicable to the current goals"""
    for i in range(0, len(agoals)):
        for j in range(i, len(agoals)):
            goal1, goal2 = agoals[i], agoals[j]
            yield from form_pairs(goal1, goal2, props)