from .Programmer import AddMetaInstruction, MoveMetaIntstruction
from .RegAlloc import get_liveness
from itertools import chain, combinations
from statistics import median
from math import floor

def powerset(s):
    return chain.from_iterable(combinations(s, r) for r in range(2, len(s)+1))


def get_highest_reg_number(mp):
    """Returns the highest register number used"""
    reg = 0
    for instr in mp:
        reg = max(reg, instr.source, instr.target)
        if isinstance(instr, AddMetaInstruction):
            reg = max(reg, instr.source2)
    return reg


def get_edges(mp):
    reg_shift_out = {}
    reg_add_out = {}
    reg_in = {}

    # get set of shifts from every register
    for i, instr in enumerate(mp):
        reg_in[instr.target] = i
        if isinstance(instr, MoveMetaIntstruction):
            reg_shift_out[instr.source] = reg_shift_out.get(instr.source, set()) | {i}
        if isinstance(instr, AddMetaInstruction):
            reg_add_out[instr.source] = reg_add_out.get(instr.source, set()) | {i}
            reg_add_out[instr.source2] = reg_add_out.get(instr.source2, set()) | {i}
    return reg_shift_out, reg_add_out, reg_in


def get_same_shift_candidates(mp, edges, n_reg):
    """Gets all the candidate sets of shifts that are from the same source register in a common direction"""
    reg_shifts, _, _ = edges
    liveness = get_liveness(mp)

    relax_candidates = []
    # for every set of shifts take the power set and analyse every set if its beneficial to carry on
    for reg, addrs in reg_shifts.items():
        if len(addrs) < 2:  # there is nothing to optimize in a single shift
            continue

        if len(addrs) > 20:
            print('[WARNING] More than 20 shifts from same reg (%d). Powerset is not computable. Nothing done.'%len(addrs))
            return []

        for s in powerset(addrs):
            # liveness has to be lower than n_reg for all
            for i in range(min(s), max(s)+1):
                if len(liveness[i]) >= n_reg:
                    break
            else:
                xp, xn, yp, yn, sp, sn = 1e6, 1e6, 1e6, 1e6, 1e6, 1e6
                for i in s:
                    xp = max(min(xp, mp[i].shift[0]), 0)
                    xn = max(min(xn, -mp[i].shift[0]), 0)
                    yp = max(min(yp, mp[i].shift[1]), 0)
                    yn = max(min(yn, -mp[i].shift[1]), 0)
                    sp = max(min(sp, mp[i].scale), 0)
                    sn = max(min(sn, -mp[i].scale), 0)
                if xp>0 or xn>0 or yp>0 or yn>0 or sp>0 or sn>0:
                    # format: (source, common shift, common scale, relaxed instructions)
                    relax_candidates.append((reg, (xp-xn, yp-yn), sp-sn, s))
    return relax_candidates


def get_rebalance_in_pairs(mp, edges, liveness):
    reg_shifts, reg_adds, reg_in = edges
    pairs = [(r, r) for r in reg_in.keys()]
    # find all nodes with liveness 1 in or out
    l1in, l1out = [], []
    # find liveness 1 pairs
    for r in reg_in.keys():
        # expect liveness 1
        if r in reg_in and len(liveness[reg_in[r]]) == 1:
            if isinstance(mp[reg_in[r]], MoveMetaIntstruction):
                l1in.append(r)
            else:
                l1out.append(r)
    for ri in l1in:
        for ro in l1out:
            pairs.append((ri, ro))
    return pairs


def get_rebalance_candidates(mp, edges, n_reg):
    candidates = []
    reg_shifts, reg_adds, reg_in = edges
    liveness = get_liveness(mp)
    pairs = get_rebalance_in_pairs(mp, edges, liveness)

    for ri, ro in pairs:
        # to optimize, we need at least one non-addition child and the parent has to be a move node
        if ro in reg_shifts and ri in reg_in and isinstance(mp[reg_in[ri]], MoveMetaIntstruction):

            # we need to be under live at the time of the adds, or the add has to be the last child, or there is no add
            if ro not in reg_adds or max(reg_shifts[ro]) < min(reg_adds[ro]) or \
                    all([len(liveness[i]) < n_reg for i in range(min(reg_adds[ro])-1, max(reg_adds[ro]))]):
                benefit = 0

                shift_children = {mp[i] for i in reg_shifts[ro]}
                add_children = {mp[i] for i in reg_adds.get(ro, set())}
                parent = mp[reg_in[ri]]

                x_weights = [c.shift[0] for c in shift_children]
                x_weights = x_weights + [0 for _ in add_children]
                x_weights.append(-parent.shift[0])
                x_diff = floor(median(x_weights))
                benefit += sum(abs(c) for c in x_weights) - sum(abs(c - x_diff) for c in x_weights)

                y_weights = [c.shift[1] for c in shift_children]
                y_weights = y_weights + [0 for _ in add_children]
                y_weights.append(-parent.shift[1])
                y_diff = floor(median(y_weights))
                benefit += sum(abs(c) for c in y_weights) - sum(abs(c - y_diff) for c in y_weights)

                s_weights = [c.scale for c in shift_children]
                s_weights = s_weights + [0 for _ in add_children]
                s_weights.append(-parent.scale)
                s_diff = floor(median(s_weights))
                benefit += sum(abs(c) for c in s_weights) - sum(abs(c - s_diff) for c in s_weights)

                if abs(x_diff) > 0 or abs(y_diff) > 0 or abs(s_diff) > 0:
                    # format: (benefit, ri, ro, shift_diff, scale_diff, in instr, (add instrs), (move instrs))
                    if benefit > 0:
                        candidates.append((benefit, ri, ro, (x_diff, y_diff), s_diff, reg_in[ri],
                                       reg_adds.get(ro, set()), reg_shifts[ro]))
    return candidates



def eliminate_empty_shifts(mp):
    """Removes empty shifts from the meta program"""
    c_map = {}
    affected_instrs = []

    for i in range(len(mp)):
        if mp[i].source in c_map:
            mp[i].source = c_map[mp[i].source]
        if isinstance(mp[i], AddMetaInstruction) and mp[i].source2 in c_map:
            mp[i].source2 = c_map[mp[i].source2]
        if isinstance(mp[i], MoveMetaIntstruction) and mp[i].shift == (0,0) and mp[i].scale == 0 and not mp[i].neg:
            c_map[mp[i].target] = mp[i].source
            affected_instrs.append(mp[i])

    for i in affected_instrs:
        mp.remove(i)
    return mp


def relax_same_shift(meta_program, n_reg):
    meta_program = eliminate_empty_shifts(meta_program)
    while True:
        edges = get_edges(meta_program)
        relax_candidates = get_same_shift_candidates(meta_program, edges, n_reg)
        if len(relax_candidates) <= 0:
            break
        # select the best possible relax
        best_relax = max(relax_candidates, key=lambda x: len(x[3])*(abs(x[1][0]) + abs(x[1][1] + abs(x[2]))))
        source_reg, c_shift, c_scale, instrs = best_relax
        # get current max reg number
        temp_reg = get_highest_reg_number(meta_program) + 1

        # add the common move instr at the first position of the instrs to be relaxed
        instrs = sorted(list(instrs))
        meta_program.insert(instrs[0], MoveMetaIntstruction(source_reg, temp_reg, c_scale, c_shift))
        for i in instrs:
            oi = meta_program[i+1]
            meta_program[i+1] = MoveMetaIntstruction(temp_reg, oi.target, oi.scale-c_scale, (oi.shift[0] - c_shift[0], oi.shift[1] - c_shift[1]), oi.neg)
    meta_program = eliminate_empty_shifts(meta_program)
    return meta_program



def relax_rebalance(mp, n_reg):
    mp = eliminate_empty_shifts(mp)
    while True:
        edges = get_edges(mp)

        candidates = get_rebalance_candidates(mp, edges, n_reg)
        if len(candidates) <= 0:
            break
        # select best candidate first
        best_relax = max(candidates, key=lambda x: x[0])
        benefit, ri, ro, shift_diff, scale_diff, in_instr, add_instrs, move_instrs = best_relax

        # apply rebalancing
        mp[in_instr].shift = (mp[in_instr].shift[0] + shift_diff[0], mp[in_instr].shift[1] + shift_diff[1])
        mp[in_instr].scale = mp[in_instr].scale + scale_diff
        for m_i in move_instrs:
            mp[m_i].shift = (mp[m_i].shift[0] - shift_diff[0], mp[m_i].shift[1] - shift_diff[1])
            mp[m_i].scale = mp[m_i].scale - scale_diff

        if add_instrs:
            temp_reg = get_highest_reg_number(mp) + 1
            for add_instr in add_instrs:
                if mp[add_instr].source == ro:
                    mp[add_instr].source = temp_reg
                if mp[add_instr].source2 == ro:
                    mp[add_instr].source2 = temp_reg
            mp.insert(min(add_instrs), MoveMetaIntstruction(ro, temp_reg, -scale_diff, (-shift_diff[0], -shift_diff[1])))

    mp = eliminate_empty_shifts(mp)
    return mp
