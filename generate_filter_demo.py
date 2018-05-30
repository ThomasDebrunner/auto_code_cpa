from scamp_filter.scamp_filter import generate, PairGenProps
import numpy as np


# These options control the algorithms heuristics
pair_props = PairGenProps(
            sort_distinct_pos=True,
            short_distance_first=True,
            low_scale_first=True,
            exhaustive=False,
            line=True,
            generate_all=True,
            max_sets=True,
            randomize=False
)


# filter = np.array([
#     [1, 0, -1],
#     [2, 0, -2],
#     [1, 0, -1]
# ])
# #
# filter = np.array([
#     [1, 1, 1, 1, 1, 1, 1],
#     [1, 1, 1, 1, 1, 1, 1],
#     [1, 1, 1, 1, 1, 1, 1],
#     [1, 1, 1, 1, 1, 1, 1],
#     [1, 1, 1, 1, 1, 1, 1],
#     [1, 1, 1, 1, 1, 1, 1],
#     [1, 1, 1, 1, 1, 1, 1]
# ])
# #
filter = np.array([
    [0.342, 0.125, 0.513],
    [0.851, 0.111, 0.455],
    [0.513, 0.131, 0.634]
])


# filter = np.array([[1,0.5,1]])


start_reg = 'A'
target_reg = 'A'
available_regs = ['A', 'B', 'C']

search_time = 10
approx_depth = 3

# set verbosity to 10 to output filter graph representations. Requires pygraphviz.
program, stats = generate(filter, search_time,
                          start_reg=start_reg,
                          target_reg=target_reg,
                          available_regs=available_regs,
                          verbose=9,
                          approx_depth=approx_depth,
                          pair_props=pair_props)
