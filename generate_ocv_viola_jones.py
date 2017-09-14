from math import log2
from scamp_filter.scamp_filter import generate
from scamp_filter.approx import approx
from xml_loader import parse_xml
import pickle
import os
import numpy as np

TILE_SIZE = 24


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


def generate_centre_goal_for_feature(feature):
    tlx, tly = feature.top_left
    kernel = np.zeros((feature.height, feature.width))
    area = feature.width * feature.height
    for rect in feature.rects:
        for x in range(rect.top_left[0]-tlx, rect.top_left[0]-tlx+rect.width):
            for y in range(rect.top_left[1]-tly, rect.top_left[1]-tly+rect.height):
                kernel[y, x] += 1./area * rect.weight
    return kernel
        

def generate_filter_code_for_feature(feature, search_time=2):
    goal = generate_centre_goal_for_feature(feature)
    some_val = goal[0,0]
    scaling = -int(log2(abs(approx(some_val, depth=20, max_coeff=1)[0])))

    program, sol_stats = generate(goal, search_time, available_regs=['C', 'D', 'E'], start_reg='A', target_reg='C', verbose=0, approx_depth=20, max_approx_coeffs=1)
    return program, scaling


def generate_threshold_code_for_feature(feature, dpalpha, dnalpha, scaling):
    t0 = int(feature.threshold*255*feature.width*feature.height/(2**scaling))
    t0s = max(-127, t0)
    t0s = min(127, t0s)

    prog = [
        'D = in(%d)' % t0s,
        'E = sub(C, D)',
        'where(E)',
        'R4 = FLAG',
        'all'
    ]

    off_x = 12 - feature.top_left[0] - feature.width // 2
    off_y = 12 - feature.top_left[1] - feature.height // 2

    prog = prog + ['R4 = pro.digital_news(R4, \'south\')' for _ in range(off_y, 0)]
    prog = prog + ['R4 = pro.digital_news(R4, \'north\')' for _ in range(0, off_y)]
    prog = prog + ['R4 = pro.digital_news(R4, \'east\')' for _ in range(off_x, 0)]
    prog = prog + ['R4 = pro.digital_news(R4, \'west\')' for _ in range(0, off_x)]

    prog = prog + [
        'where(R4)',
        'D = in(%d)' % dnalpha,
        'others',
        'D = in(%d)' % dpalpha,
        'all',
        'B = add(B, D)'
    ]

    return prog

def generate_stage_end_code(dthreshold):
    return [
        'D = in(%d)' % dthreshold,
        'D = sub(B, D)',
        'where(D)',
        'R5 = and(FLAG, R5)',
        'all'
    ]

def find_feature_groups(features):
    global total_progs, total_new_progs
    s = {}
    for feature in features:
        key = tuple((r.width, r.height, r.weight) for r in sorted(feature.rects, key=lambda r: (r.width, r.height, r.weight)))
        if key not in s:
            s[key] = [feature]
        else:
            s[key].append(feature)
    total_progs += len(features)
    total_new_progs += len(s.keys())
    print('%d --> %d'%(len(features), len(s.keys())))
    return s


def generate_program_for_stage(stage, program_store):
    # compute average alpha ranges
    OVERSHOOT = 1
    up_total_alpha = sum((f.palpha if f.palpha > 0 else f.nalpha) for f in stage.features)
    down_total_alpha = sum((f.palpha if f.palpha < 0 else f.nalpha) for f in stage.features)
    alpha_range = up_total_alpha - down_total_alpha

    total_program = []

    groups = find_feature_groups(stage.features)

    for key, features  in groups.items():
        if key in program_store:
            program, scaling = program_store[key]
        else:
            # generate filter code
            program, scaling = generate_filter_code_for_feature(features[0])
            program_store[key] = (program, scaling)

        total_program.extend(program)


        for feature in features:
            dpalpha = int(round(OVERSHOOT * (feature.palpha / alpha_range) * 254))
            dnalpha = int(round(OVERSHOOT * (feature.nalpha / alpha_range) * 254))
            total_program.extend(generate_threshold_code_for_feature(feature, dpalpha, dnalpha, scaling))

    dstage_threshold = int(round(OVERSHOOT * (stage.threshold/alpha_range) * 254))
    print(dstage_threshold)
    total_program.extend(generate_stage_end_code(dstage_threshold))

    print('... stage done')
    return total_program

total_progs = 0
total_new_progs = 0




def main():
    # load pretrained model
    stages = parse_xml('haarcascade_frontalface_default.xml')

    # generate core programs
    for i, stage in enumerate(stages):
        print('STAGE %d..' % (i+1))

        if os.path.isfile('pre_ocv_kernels.pkl'):
            with open('pre_ocv_kernels.pkl', 'rb') as file:
                program_store = pickle.load(file)
        else:
            program_store = {}
            
        program = generate_program_for_stage(stage, program_store)

        with open('pre_ocv_kernels.pkl', 'wb') as file:
            pickle.dump(program_store, file)

        with open('ocv_stages/vj_core_ocv_stage_%d.aps'%(i+1), 'w') as file:
            file.write('#vj_stage_%d\n'%(i+1))
            for line in program:
                file.write(line + '\n')
            file.write('_ret\n\n\n')

    print('...Generation done')




    global total_progs, total_new_progs
    print('%d =====> %d' % (total_progs, total_new_progs))


if __name__ == '__main__':
     main()
