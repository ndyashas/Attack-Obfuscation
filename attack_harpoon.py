import os
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
    """
    Recursive function to remove the influence of the given node downstream.
    """

    # Stopping contion - If the current node has no fanout.
    if ((ck.fanout(node) is set())):
        return affected_nodes, already_visited, ck

    # Add the current node to the list of already visited nodes.
    already_visited.add(node)

    # If the node is affected - a positive or a negative node
    if (ck.type(node) in (ck_two_input_positive + ck_two_input_negative + ["bb_input"])):
        # Add to the affected_nodes set.
        affected_nodes.add(node)

        print(ck.type(node), "disconnecting ", node, "of type ", ck.type(node), "from parent ", parent_node)

        # Disconnect the child from the current node.
        ck.disconnect(parent_node, node)

        # And replace the node with a buffer or a not gate based on the type of its disconnected parent.
        if (ck.type(node) in ck_two_input_positive):
            ck.set_type(node, "buf")
        elif (ck.type(node) in ck_two_input_positive):
            ck.set_type(node, "not")

        return affected_nodes, already_visited, ck

    # Else if the node is not affected,
    else:
        # Recursive call to the function.
        for child_node in ck.fanout(node):
            affected_nodes_tmp, already_visited_tmp, ck = fix_affected_nodes(ck, child_node, node, affected_nodes, already_visited)
            affected_nodes = affected_nodes | affected_nodes_tmp
            already_visited = already_visited | already_visited_tmp    
            
    return affected_nodes, already_visited, ck


def main(args):
    """
    This function filters flip flops based on their reset port signal, and removes them from the design
    based on the kind of signal it is.
    """
    
    dffsr_bb = cg.BlackBox('DFFSR', ['R', 'S', 'C', 'D'], ['Q']);
    ck = cg.from_file(str(args.netlist_file), blackboxes = [dffsr_bb])

    ## separate DFFSRs based on how their reset signals originate
    # dffsr_resets are the reset signals feeding into all the flip flops
    all_dffsr_inputs = ck.filter_type("bb_input")
    dffsr_resets = [ip for ip in all_dffsr_inputs if ".R" in ip]

    # Initialize a list to store the obfuscated and original flip flops
    obfuscated_dffsr = []
    original_dffsr = []
    for dffsr_reset in dffsr_resets:
        # start_points are the nodes which are top most ansestors of the cone of influence for the reset signal
        # of each of the flip flop. We filter nodes by seeing if their start_points has any signal originating
        # from another flip-flop.
        #
        # Flip flops are seen as black boxes. Thus, we set the type as bb_output (The 'Q' output from the flip flop)
        start_points = {node for node in ck.startpoints(dffsr_reset) if ck.type(node) == "bb_output"}

        # If there is a signal that is affecting the reset signal of this flip flop, and that signal originated from
        # within the circuit, then that flip flop belongs to the original circuit.
        if (start_points):
            original_dffsr.append(dffsr_reset.replace(".R", ""))

        # Else, the flip flop belongs to the M'Baku's trible
        else:
            obfuscated_dffsr.append(dffsr_reset.replace(".R", ""))


    # Step 2: Remove the flip flops and its connections down stream.
    # Implemented a Depth First Search to find the first two-input gate and convert it
    # to either a buffer or a not gate based on the kind of gate it was (positive, or negative)
    affected_nodes = set()
    visits = set()
    for dffsr in obfuscated_dffsr:
        # Recursive calls to the fix_affected_nodes function. As Python does not support pass by reference, we
        # need to update our values as they are getting computed.
        affected_nodes_tmp, visits_tmp, ck = fix_affected_nodes(ck, dffsr + ".Q", "DUMMY_INPUT", set(), set())
        affected_nodes = affected_nodes | affected_nodes_tmp
        visits = visits | visits_tmp
    ck.remove_unloaded()
    
    for dffsr in original_dffsr:
        ck.connect("reset", dffsr + ".R")

    cg.to_file(ck, "residual-design.v")

    os.system("./utils/postprocess.sh")
    

if (__name__ == "__main__"):
    
    parser = argparse.ArgumentParser(description = "Command line arguments for the tool attacking HARPOON obfuscated designs.")

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
