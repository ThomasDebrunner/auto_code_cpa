import re
from .MetaProgrammer import AddMetaInstruction, MoveMetaIntstruction
# ---------------------------------------------------------------------------------------------------


def generate_scamp_shift(source, target, scale, shift, neg, reg_names):
    program = []
    s, t = reg_names[source], reg_names[target]
    if scale == 0 and shift == (0, 0) and not neg:
        program.append('%s = copy(%s)' % (t, s))
        return program

    copied = False

    for _ in range(shift[1], 0):
        program.append('%s = south(%s)' % (t, s if not copied else t))
        copied = True
    for _ in range(0, shift[1]):
        program.append('%s = north(%s)' % (t, s if not copied else t))
        copied = True

    for _ in range(shift[0], 0):
        program.append('%s = west(%s)' % (t, s if not copied else t))
        copied = True
    for _ in range(0, shift[0]):
        program.append('%s = east(%s)' % (t, s if not copied else t))
        copied = True
    for _ in range(scale, 0):
        program.append('%s = add(%s, %s)' % (t, s if not copied else t, s if not copied else t))
        copied = True
    for _ in range(0, scale):
        program.append('%s = div2(%s)' % (t, s if not copied else t))
        copied = True
    if neg:
        ss = s if not copied else t
        if ss == t:
            program.append('%s = sneg(%s)' % (t, ss))
        else:
            program.append('%s = neg(%s)' % (t, ss))

    return program


def generate_scamp_add(source1, source2, s1neg, s2neg, target, reg_names):
    s1, s2, t = reg_names[source1], reg_names[source2], reg_names[target]
    if not s1neg and not s2neg:
        return ['%s = add(%s, %s)' % (t, s1, s2)]
    if not s1neg and s2neg:
        return ['%s = sub(%s, %s)' % (t, s1, s2)]
    if s1neg and not s2neg:
        return ['%s = sub(%s, %s)' % (t, s2, s1)]
    if s1neg and s2neg:
        return ['%s = addneg(%s, %s)' % (t, s1, s2)]


def generate_scamp_program(meta_program, available_regs, start_reg, target_reg):

    # if we can overwrite the start reg, have to order the names in a way that it works
    if start_reg in available_regs:
        exp_pos = meta_program[0].source
        available_regs.remove(start_reg)
        available_regs.insert(exp_pos, start_reg)
    else:
        available_regs.append(start_reg)
        exp_pos = meta_program[0].source
        meta_program.insert(0, MoveMetaIntstruction(len(available_regs)-1, exp_pos, 0, (0,0), False))

    # append target_reg, to be used by last instr
    available_regs.append(target_reg)
    meta_program[-1].target = len(available_regs) -1

    program = []
    for step in meta_program:
        if isinstance(step, MoveMetaIntstruction):
            program = program + generate_scamp_shift(step.source, step.target, step.scale, step.shift, step.neg, available_regs)
        elif isinstance(step, AddMetaInstruction):
            program = program + generate_scamp_add(step.source, step.source2, step.s1neg, step.s2neg, step.target, available_regs)
        else:
            print('[ERROR] Unknown meta instruction encountered')

    return program
# ---------------------------------------------------------------------------------------------------


def translate_program_csim(program):
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

    out_program = []

    for line in program:
        if add_r.match(line):
            m = add_r.search(line)
            out_program.append('add(%s, %s, %s);' % (m.group(1), m.group(2), m.group(3)))
        elif addneg_r.match(line):
            m = addneg_r.search(line)
            out_program.append('add(%s, %s, %s);' % (m.group(1), m.group(2), m.group(3)))
            out_program.append('neg(%s, %s);' % (m.group(1), m.group(1)))
        elif sub_r.match(line):
            m = sub_r.search(line)
            out_program.append('sub(%s, %s, %s);' % (m.group(1), m.group(2), m.group(3)))
        elif north_r.match(line):
            m = north_r.search(line)
            out_program.append('north(%s, %s);' % (m.group(1), m.group(2)))
        elif east_r.match(line):
            m = east_r.search(line)
            out_program.append('east(%s, %s);' % (m.group(1), m.group(2)))
        elif south_r.match(line):
            m = south_r.search(line)
            out_program.append('south(%s, %s);' % (m.group(1), m.group(2)))
        elif west_r.match(line):
            m = west_r.search(line)
            out_program.append('west(%s, %s);' % (m.group(1), m.group(2)))
        elif div_r.match(line):
            m = div_r.search(line)
            out_program.append('div2(%s, %s);' % (m.group(1), m.group(2)))
        elif neg_r.match(line):
            m = neg_r.search(line)
            out_program.append('neg(%s, %s);' % (m.group(1), m.group(2)))
        elif copy_r.match(line):
            m = copy_r.search(line)
            out_program.append('mov(%s, %s);' % (m.group(1), m.group(2)))
    return out_program
