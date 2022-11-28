#!/bin/bash

yosys ./utils/yosys-synth-script.ys

# cat yosys-synth.v
sed -Ei 's/\\//g' yosys-synth.v
sed -Ei 's/([a-zA-Z0-9]|_)\.([a-zA-Z0-9]|_)/\1_\2/g' yosys-synth.v
# cat yosys-synth.v

python3 -c "import circuitgraph as cg;\
	    dffsr_bb = cg.BlackBox('DFFSR', ['R', 'S', 'C', 'D'], ['Q']);\
	    ck = cg.from_file('yosys-synth.v',blackboxes = [dffsr_bb]);\
	    cg.to_file(ck, 'recovered-design.v')"
