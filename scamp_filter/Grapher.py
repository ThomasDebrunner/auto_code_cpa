import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
from networkx.drawing.nx_agraph import write_dot
from .MetaProgrammer import AddMetaInstruction
from .Latexer import latexify_shift_label
import matplotlib.pyplot as plt
import time

def print_meta_program(meta_program, dot=False, title=''):
    G = nx.DiGraph()
    G.add_node(str(0))
    node_labels = {}
    edge_labels = {}
    for i, instr in enumerate(meta_program):
        if i==0:
            G.add_node(0)
            node_labels[instr.source] = '0'
            G.node[instr.source]['label'] = '0'
        G.add_node(instr.target)
        node_labels[instr.target] = '%d'%(i+1)
        G.node[instr.target]['label'] = node_labels[instr.target]
        edge_labels[(instr.source, instr.target)] = str(instr).split('|| ')[-1]
        G.add_edge(instr.source, instr.target, attr_dict={'label': latexify_shift_label(edge_labels[(instr.source, instr.target)])})
        if isinstance(instr, AddMetaInstruction):
            edge_labels[(instr.source, instr.target)] = '+' if not instr.s1neg else '-'
            edge_labels[(instr.source2, instr.target)] = '+' if not instr.s2neg else '-'
            G[instr.source][instr.target]['label'] = edge_labels[(instr.source, instr.target)]
            G.add_edge(instr.source2, instr.target, attr_dict={'label': edge_labels[(instr.source2, instr.target)]})


    plt.figure()
    plt.title(title)
    pos = graphviz_layout(G)
    nx.draw_networkx_labels(G, pos, node_labels)
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
    nx.draw(G, pos=pos, prog='dot')

    if dot:
        filename = 'dots/meta_' + str(int(round(time.time() * 1000)))+'.dot'
        write_dot(G, filename)



def print_reg_graph(g, coloring, dot=False, title=''):
    G = nx.from_dict_of_lists(g)
    pos = graphviz_layout(G)
    node_labels = {}

    node_colors = [coloring[node] for node in G.nodes()]

    colors = ['circle', 'regular polygon,regular polygon sides=4', 'diamond', 'regular polygon,regular polygon sides=5']

    for n in G.node:
        G.node[n]['style'] = 'draw, %s'%colors[coloring[n]]


    for n in g.keys():
        node_labels[n] = str(n)
    plt.figure()
    plt.title(title)
    nx.draw_networkx_labels(G, pos, node_labels)
    nx.draw(G, pos=pos, prog='dot', node_color=node_colors)

    if dot:
        filename = 'dots/reg_' + str(int(round(time.time() * 1000)))+'.dot'
        write_dot(G, filename)


def print_pair_constraints(group, dot):
    nodes = {}
    node_labels = {}
    for a1, a2 in group:
        nodes[a1] = nodes.get(a1, []) + [a2]
        nodes[a2] = nodes.get(a2, []) + [a1]
        node_labels[a1] = str(a1.nr)
        node_labels[a2] = str(a2.nr)
    G = nx.from_dict_of_lists(nodes)
    pos = graphviz_layout(G)
    plt.figure()
    nx.draw_networkx_labels(G, pos, node_labels)
    nx.draw(G, pos=pos, prog='dot')

    if dot:
        filename = 'dots/pair_' + str(int(round(time.time() * 1000)))+'.dot'
        write_dot(G, filename)

def show():
    plt.show()
