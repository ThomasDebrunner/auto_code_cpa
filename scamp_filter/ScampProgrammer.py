import re
from .MetaProgrammer import AddMetaInstruction, MoveMetaIntstruction
# ---------------------------------------------------------------------------------------------------

patterns_apron = {
    'copy': '{0} = copy({1})',
    'south': '{0} = south({1})',
    'north': '{0} = north({1})',
    'west': '{0} = west({1})',
    'east': '{0} = east({1})',
    'double': '{0} = add({1}, {2})',
    'div2': '{0} = div2({1})',
    'sneg': '{0} = sneg({1})',
    'neg': '{0} = neg({1})',
    'add': '{0} = add({1}, {2})',
    'sub': '{0} = sub({1}, {2})',
    'addneg': '{0} = addneg({1}, {2})'
}

patterns_csim = {
    'copy': 'mov({0}, {1});',
    'south': '// south({0}, {1});',
    'north': '// north({0}, {1});',
    'west': '// west({0}, {1});',
    'east': '// east({0}, {1});',
    'double': '// add({0}, {1}, {2});',
    'div2': '// div2({0}, {1});',
    'sneg': 'neg({0}, {1});',
    'neg': 'neg({0}, {1});',
    'add': 'add({0}, {1}, {2});',
    'sub': 'sub({0}, {1}, {2});',
    'addneg': 'addneg({0}, {1}, {2});',
}


def generate_scamp_shift(source, target, scale, shift, neg, reg_names, out_format):
    program = []
    s, t = reg_names[source], reg_names[target]
    program.append('// [{}] -> [{}] || x:{} y:{} s:{} neg:{:d}'.format(t, s, shift[0], shift[1], scale, neg))
    if out_format == 'CSIM':
        program.append('_transform({}, {}, {}, {}, {}, {:d});'.format(t, s, shift[0], shift[1], scale, neg))
        patterns = patterns_csim
    else:
        patterns = patterns_apron

    if scale == 0 and shift == (0, 0) and not neg:
        program.append(patterns['copy'].format(t, s))
        return program

    copied = False

    for _ in range(shift[1], 0):
        program.append(patterns['south'].format(t, s if not copied else t))
        copied = True
    for _ in range(0, shift[1]):
        program.append(patterns['north'].format(t, s if not copied else t))
        copied = True

    for _ in range(shift[0], 0):
        program.append(patterns['west'].format(t, s if not copied else t))
        copied = True
    for _ in range(0, shift[0]):
        program.append(patterns['east'].format(t, s if not copied else t))
        copied = True
    for _ in range(scale, 0):
        program.append(patterns['double'].format(t, s if not copied else t, s if not copied else t))
        copied = True
    for _ in range(0, scale):
        program.append(patterns['div2'].format(t, s if not copied else t))
        copied = True
    if neg:
        ss = s if not copied else t
        if ss == t:
            program.append(patterns['sneg'].format(t, ss))
        else:
            program.append(patterns['neg'].format(t, ss))

    length = abs(scale) + abs(shift[0]) + abs(shift[1]) + neg
    return program, length


def generate_scamp_add(source1, source2, s1neg, s2neg, target, reg_names, out_format):
    patterns = patterns_csim if out_format == 'CSIM' else patterns_apron
    s1, s2, t = reg_names[source1], reg_names[source2], reg_names[target]
    if not s1neg and not s2neg:
        return [patterns['add'].format(t, s1, s2)], 1
    if not s1neg and s2neg:
        return [patterns['sub'].format(t, s1, s2)], 1
    if s1neg and not s2neg:
        return [patterns['sub'].format(t, s2, s1)], 1
    if s1neg and s2neg:
        return [patterns['addneg'].format(t, s1, s2)], 1


def generate_scamp_program(meta_program, available_regs, start_reg, target_reg, out_format):

    # if we can overwrite the start reg, have to order the names in a way that it works
    if start_reg in available_regs:
        exp_pos = meta_program[0].source
        available_regs.remove(start_reg)
        available_regs.insert(exp_pos, start_reg)
    else:
        available_regs.append(start_reg)
        exp_pos = meta_program[0].source
        meta_program.insert(0, MoveMetaIntstruction(len(available_regs)-1, exp_pos, 0, (0, 0), False))

    # append target_reg, to be used by last instr
    available_regs.append(target_reg)
    meta_program[-1].target = len(available_regs) -1

    program = []
    program.append('// ----------------------------------------------------')
    program.append('// DO NOT MODIFY! (Automatically generated kernel code)')
    length = 0
    for step in meta_program:
        if isinstance(step, MoveMetaIntstruction):
            move_program, move_length = generate_scamp_shift(step.source, step.target, step.scale, step.shift, step.neg,
                                                             available_regs, out_format)
            program, length = program + move_program, length + move_length
        elif isinstance(step, AddMetaInstruction):
            add_program, add_length = generate_scamp_add(step.source, step.source2, step.s1neg, step.s2neg, step.target,
                                                         available_regs, out_format)
            program, length = program + add_program, length + add_length
        else:
            print('[ERROR] Unknown meta instruction encountered')
    program.append('// ----------------------------------------------------')
    return program, length