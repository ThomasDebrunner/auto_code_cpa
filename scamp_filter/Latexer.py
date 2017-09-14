def latexify_atom(atom):
    return '%s([%d], %d, %d)' % ('-' if atom.neg else '', atom.nr, atom.x, atom.y)


def latexify_goal(goal, math=True):
    gl = list(goal)
    gl.sort(key=lambda x: x.nr)
    strs = [latexify_atom(a) for a in gl]
    st = ', '.join(strs)
    if math:
        st = '$' + st + '$'
    return st


def latexify_shift_label(label):
    return label.replace('→', '\\rightarrow').replace('←', '\\leftarrow').replace('↑', '\\uparrow').replace('↓', '\\downarrow')


def print_filter(filter):
    # get dimensions
    nx, px = min(filter, key=lambda x:x.x).x, max(filter, key=lambda x:x.x).x
    ny, py = min(filter, key=lambda x: x.y).y, max(filter, key=lambda x: x.y).y
    width = px-nx+1
    height = py-ny+1
    map = [[0 for _ in range(height)] for _ in range(width)]
    for item in filter:
        map[-item.x - nx][item.y - ny] += 2**(-item.scale) * (-1 if item.neg else 1)

    print('K = \\begin{bmatrix}')
    for line in map:
        print(' & '.join(str(factor) for factor in line), end='\\\n')
    print('\\end{bmatrix}')
