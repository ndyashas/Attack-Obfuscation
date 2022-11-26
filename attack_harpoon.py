import argparse
from pathlib import Path
import circuitgraph as cg

import networkx as nx
import matplotlib.pyplot as plt

ck_two_input_positive = [
    "and",
    "or",
    "xor",
]
ck_two_input_negative = [
    "nand",
    "nor",
    "xnor",
]

def fix_affected_nodes(ck, node, parent_node, affected_nodes, already_visited):
    # print("#"*10)
    # print("NODE: ", node)
    # print("affected_nodes: ", affected_nodes)
    # print("already_visited: ", already_visited)
    
    # Stopping condition
    if ((node in already_visited) or (ck.fanout(node) is set())):
        return affected_nodes, already_visited, ck

    already_visited.add(node)
    # If the node is affected
    if (ck.type(node) in (ck_two_input_positive + ck_two_input_negative + ["bb_input"])):
        affected_nodes.add(node)

        print(ck.type(node), "disconnecting ", node, "of type ", ck.type(node), "from parent ", parent_node)
        
        ck.disconnect(parent_node, node)
        if (ck.type(node) in ck_two_input_positive):
            ck.set_type(node, "buf")
        elif (ck.type(node) in ck_two_input_positive):
            ck.set_type(node, "not")

        return affected_nodes, already_visited, ck

    # Else if the node is not affected,
    else:
        for child_node in ck.fanout(node):
            affected_nodes_tmp, already_visited_tmp, ck = fix_affected_nodes(ck, child_node, node, affected_nodes, already_visited)
            affected_nodes = affected_nodes | affected_nodes_tmp
            already_visited = already_visited | already_visited_tmp    
            
    return affected_nodes, already_visited, ck


def main(args):
    dffsr_bb = cg.BlackBox('DFFSR', ['R', 'S', 'C', 'D'], ['Q']);

    ck = cg.from_file(str(args.netlist_file), blackboxes = [dffsr_bb])

    ## separate DFFSRs based on how their reset signals originate
    # getting all the reset signals of DFFSR modules
    all_dffsr_inputs = ck.filter_type("bb_input")
    dffsr_resets = [ip for ip in all_dffsr_inputs if ".R" in ip]


    obfuscated_dffsr = []
    original_dffsr = []
    for dffsr_reset in dffsr_resets:
        # Has unrelated input nodes. Need to remove them
        start_points = {node for node in ck.startpoints(dffsr_reset) if ck.type(node) == "bb_output"}

        if (start_points):
            original_dffsr.append(dffsr_reset.replace(".R", ""))

        else:
            obfuscated_dffsr.append(dffsr_reset.replace(".R", ""))


    # Modify circuit to remove the children nodes
    # print(obfuscated_dffsr)

    affected_nodes = set()
    visits = set()
    for dffsr in obfuscated_dffsr:
        affected_nodes_tmp, visits_tmp, ck = fix_affected_nodes(ck, dffsr + ".Q", "DUMMY_INPUT", set(), set())
        affected_nodes = affected_nodes | affected_nodes_tmp
        visits = visits | visits_tmp

    ck.remove_unloaded()

    for dffsr in original_dffsr:
        ck.connect("reset", dffsr + ".R")

    cg.to_file(ck, "original.v")
    

if (__name__ == "__main__"):
    
    parser = argparse.ArgumentParser(description = "Command line arguments for the HARPOON Attack tool.")

    parser.add_argument("-f", "--netlist_file",
                        required = True,
                        type = Path,
                        help = "Input netlist file.")

    parser.add_argument("-t", "--top_module",
                        required = True,
                        type = str,
                        help = "Top module name.")

    args = parser.parse_args()

    main(args)
