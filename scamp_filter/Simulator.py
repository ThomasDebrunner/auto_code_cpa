from .Item import Item as I
import re


def _move(set, scale, x, y, neg):
    return {I(o.scale + scale, o.x + x, o.y + y, o.neg != neg) for o in set}


def _add(s1, s2):
    while not s1.isdisjoint(s2):
        intersect = s1.intersection(s2)
        s1 = (s1 | s2).difference(intersect)
        s2 = _move(intersect, -1, 0, 0, False)
    return s1 | s2


def interpret_apron(program, start_reg='A'):
    add_r = re.compile('([A-Z]) = add\(([A-Z]), ([A-Z])\)')
    sub_r = re.compile('([A-Z]) = sub\(([A-Z]), ([A-Z])\)')
    addneg_r = re.compile('([A-Z]) = addneg\(([A-Z]), ([A-Z])\)')
    north_r = re.compile('([A-Z]) = north\(([A-Z])\)')
    east_r = re.compile('([A-Z]) = east\(([A-Z])\)')
    south_r = re.compile('([A-Z]) = south\(([A-Z])\)')
    west_r = re.compile('([A-Z]) = west\(([A-Z])\)')
    div_r = re.compile('([A-Z]) = div2\(([A-Z])\)')
    neg_r = re.compile('([A-Z]) = (neg|sneg)\(([A-Z])\)')
    copy_r = re.compile('([A-Z]) = copy\(([A-Z])\)')


    reg_state = {
        start_reg: {I(0,0,0)}
    }

    for line in program:
        # parse
        if add_r.match(line):
            m = add_r.search(line)
            t, s1, s2 = m.group(1), m.group(2), m.group(3)
            reg_state[t] = _add(reg_state[s1], reg_state[s2])

        elif addneg_r.match(line):
            m = addneg_r.search(line)
            t, s1, s2 = m.group(1), m.group(2), m.group(3)
            reg_state[t] = {-i for i in _add(reg_state[s1], reg_state[s2])}

        elif sub_r.match(line):
            m = sub_r.search(line)
            t, s1, s2 = m.group(1), m.group(2), m.group(3)
            ns2 = {-i for i in reg_state[s2]}
            reg_state[t] = _add(reg_state[s1], ns2)

        elif north_r.match(line):
            m = north_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = _move(reg_state[s], 0, 0, 1, False)

        elif east_r.match(line):
            m = east_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = _move(reg_state[s], 0, 1, 0, False)

        elif south_r.match(line):
            m = south_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = _move(reg_state[s], 0, 0, -1, False)

        elif west_r.match(line):
            m = west_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = _move(reg_state[s], 0, -1, 0, False)

        elif div_r.match(line):
            m = div_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = _move(reg_state[s], 1, 0, 0, False)

        elif neg_r.match(line):
            m = neg_r.search(line)
            t, s = m.group(1), m.group(3)
            reg_state[t] = _move(reg_state[s], 0, 0, 0, True)

        elif copy_r.match(line):
            m = copy_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = reg_state[s]
    return reg_state


def interpret_csim(program, start_reg='A'):
    add_r = re.compile('add\(([A-Z]), ([A-Z]), ([A-Z])\)')
    sub_r = re.compile('sub\(([A-Z]), ([A-Z]), ([A-Z])\)')
    addneg_r = re.compile('addneg\(([A-Z]), ([A-Z]), ([A-Z])\)')
    copy_r = re.compile('copy\(([A-Z]), ([A-Z])\)')
    transform_r = re.compile('_transform\(([A-Z]), ([A-Z]), ([-+]?[0-9]+), ([-+]?[0-9]+), ([-+]?[0-9]+), ([01])\)')

    reg_state = {
        start_reg: {I(0, 0, 0)}
    }

    for line in program:
        # parse
        if add_r.match(line):
            m = add_r.search(line)
            t, s1, s2 = m.group(1), m.group(2), m.group(3)
            reg_state[t] = _add(reg_state[s1], reg_state[s2])

        elif addneg_r.match(line):
            m = addneg_r.search(line)
            t, s1, s2 = m.group(1), m.group(2), m.group(3)
            reg_state[t] = {-i for i in _add(reg_state[s1], reg_state[s2])}

        elif sub_r.match(line):
            m = sub_r.search(line)
            t, s1, s2 = m.group(1), m.group(2), m.group(3)
            ns2 = {-i for i in reg_state[s2]}
            reg_state[t] = _add(reg_state[s1], ns2)

        elif copy_r.match(line):
            m = copy_r.search(line)
            t, s = m.group(1), m.group(2)
            reg_state[t] = reg_state[s]

        elif transform_r.match(line):
            m = transform_r.search(line)
            t, s, x_shift, y_shift, scale, neg_s = [m.group(i) for i in range(1, 7)]
            neg = True if neg_s == '1' else False
            reg_state[t] = _move(reg_state[s], int(scale), int(x_shift), int(y_shift), neg)
    return reg_state


def validate(program, expected_result, start_reg, target_reg, out_format):
    """Validates a given SCAMP program based on correctness by simulating the SCAMP chip execution"""
    if out_format == 'CSIM':
        reg_state = interpret_csim(program, start_reg)
    else:
        reg_state = interpret_apron(program, start_reg)
    actual = reg_state[target_reg]

    if len(actual) == len(expected_result) and set(expected_result).issubset(actual):
        return True

    print('Expecected: ')
    print(sorted(list(expected_result)))
    print('Actual result: ')
    print(sorted(list(actual)))
    print('Missing:')
    print(sorted(list(set(expected_result).difference(set(actual)))))
    print('Extra:')
    print(sorted(list(set(actual).difference(set(expected_result)))))

    return False