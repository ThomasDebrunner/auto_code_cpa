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
    # scaling = 2**int(log2(area/8))
    scaling = 1
    for rect in feature.rects:
        for x in range(rect.top_left[0]-tlx, rect.top_left[0]-tlx+rect.width):
            for y in range(rect.top_left[1]-tly, rect.top_left[1]-tly+rect.height):
                kernel[y, x] += (1./scaling) * rect.weight
    return kernel, scaling
        

def generate_filter_code_for_feature(feature, search_time=2):
    goal, scaling = generate_centre_goal_for_feature(feature)

    program, sol_stats = generate(goal, search_time, available_regs=['C', 'D', 'E'], out_format='CSIM', start_reg='A', target_reg='C', verbose=0, approx_depth=20, max_approx_coeffs=1)
    return program, scaling


def generate_threshold_code_for_feature(feature, dpalpha, dnalpha, scaling):
    # t0 = int(feature.threshold * 256 / scaling)
    # t0s = max(-127, t0)
    # t0s = min(127, t0s)

    prog = [
        'in(D, %.7f);' % feature.threshold,
        'sub(E, C, D);',
        'where(E);',
        'd_mov(R4, FLAG);',
        'all();'
    ]

    off_x = 12 - feature.top_left[0] - feature.width // 2
    off_y = 12 - feature.top_left[1] - feature.height // 2

    prog = prog + ['d_south(R4, R4);' for _ in range(off_y, 0)]
    prog = prog + ['d_north(R4, R4);' for _ in range(0, off_y)]
    prog = prog + ['d_east(R4, R4);' for _ in range(off_x, 0)]
    prog = prog + ['d_west(R4, R4);' for _ in range(0, off_x)]

    prog = prog + [
        'where(R4);',
        'in(D, %.7f);' % dnalpha,
        'nor(FLAG, FLAG);',
        'in(D, %.7f);' % dpalpha,
        'all();',
        'add(B, B, D);'
    ]

    return prog

def generate_stage_end_code(dthreshold):
    return [
        'in(D, %.7f);' % dthreshold,
        'sub(D, B, D);',
        'where(D);',
        'nor(R12, FLAG);',
        'nor(R11, R5);',
        'nor(R5, R11, R12);',
        'all();'
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
    # up_total_alpha = sum((f.palpha if f.palpha > 0 else f.nalpha) for f in stage.features)
    # down_total_alpha = sum((f.palpha if f.palpha < 0 else f.nalpha) for f in stage.features)
    # alpha_range = up_total_alpha - down_total_alpha
    # alpha_offset = up_total_alpha - alpha_range/2

    total_program = []

    groups = find_feature_groups(stage.features)

    for key, features in groups.items():
        if key in program_store:
            program, scaling = program_store[key]
        else:
            # generate filter code
            program, scaling = generate_filter_code_for_feature(features[0])
            program_store[key] = (program, scaling)

        total_program.extend(program)

        for feature in features:
            # dpalpha = int(round(((feature.palpha - alpha_offset) / alpha_range) * 256))
            # dnalpha = int(round(((feature.nalpha - alpha_offset) / alpha_range) * 256))
            total_program.extend(generate_threshold_code_for_feature(feature, feature.palpha, feature.nalpha, scaling))

    # dstage_threshold = int(round(((stage.threshold - alpha_offset)/alpha_range) * 256))
    total_program.extend(generate_stage_end_code(stage.threshold))

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
