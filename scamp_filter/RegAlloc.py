from .MetaProgrammer import AddMetaInstruction, MoveMetaIntstruction
import scamp_filter.Grapher as Grapher


def get_liveness(meta_program):
    """Algorithm gets the live set of registers at every instruction"""
    min_table = {0: 0}
    max_table = {}

    for i, instr in enumerate(meta_program):
        if instr.target not in min_table:
            min_table[instr.target] = i
            max_table[instr.target] = i

        max_table[instr.source] = i
        if isinstance(instr, AddMetaInstruction):
            max_table[instr.source2] = i

    # for key in min_table.keys()
    #    print('#%d  [%d - %d]' % (key, min_table[key], max_table[key]))

    l = [set() for _ in range(len(meta_program))]
    for reg in min_table.keys():
        low, high = min_table[reg], max_table[reg]
        for i in range(low, high):
            l[i].add(reg)
    return l


def create_graph(liveness):
    """Takes the liveness and transforms it to a graph (dict with key node, value set of edges"""
    g = {}
    for l_set in liveness:
        for item in l_set:
            s = (g[item] if item in g else set()) | l_set
            if item in s:  # remove self edge
                s.remove(item)
            g[item] = s
    return g


def color_graph(g, n_colors):
    """Simple backtracking algorithm that tries to find a coloring of the graph with n colors"""
    colors = {}
    while len(colors) < len(g):  # make sure we color al disjoint parts individually
        start_node = next(iter(set(g.keys()).difference(set(colors.keys()))))  # pick a start node have not colored yet
        success = _color_graph(g, start_node, colors, n_colors)
        if not success:
            return None

    return colors


def _color_graph(graph, node, colors, n_colors):
    neighbors = graph[node]
    for c in range(n_colors):
        # check if a neighbor already uses the same color
        for neighbor in neighbors:
            if neighbor in colors and colors[neighbor] == c:
                break
        else:
            colors[node] = c
            for neighbor in neighbors:
                if neighbor in colors:
                    continue
                success = _color_graph(graph, neighbor, colors, n_colors)
                if not success:
                    break
            else:
                return True
    if node in colors:
        del colors[node]
    return False


def allocate_coloring(meta_program, coloring):
    """Replaces the registers in the original program by the ones found in coloring. Assign reg 0 for unconstrained"""
    for instr in meta_program:
        instr.source = coloring.get(instr.source, 0)
        instr.target = coloring.get(instr.target, 0)
        if isinstance(instr, AddMetaInstruction):
            instr.source2 = coloring.get(instr.source2, 0)
    return meta_program


def alloc(meta_program, n_reg, verbose=0):
    if verbose > 0:
        print('| >> Register liveness analysis')
    liveness = get_liveness(meta_program)
    min_reg = len(max(liveness, key=len))
    if verbose > 0:
        print('| ... Done. At most, %d registers are live at the same time' % min_reg)
    if n_reg < min_reg:
        print('[Error] Register allocation won\t be possible with less than %d registers' % min_reg)
    if verbose > 0:
        print('| >> Creating dependency graph')
    graph = create_graph(liveness)
    if verbose > 0:
        print('| ..Done')
        print('| >> Colouring graph')
    coloring = color_graph(graph, n_reg)
    if verbose > 0:
        print('| ..Done')
    if coloring is None:
        print('[Error] There is no register allocation with %d registers possible' % n_reg)

    if verbose > 9:
        Grapher.print_reg_graph(graph, coloring, verbose>10, title='Register allocation graph colouring')
        Grapher.show()
    if verbose > 0:
        print('| >> Allocating registers to meta program')
        print('| ..Done')
    allocate_coloring(meta_program, coloring)
    return meta_program
