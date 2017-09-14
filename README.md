# Automatic Code Generation for SCAMP CPA

## Contents
This repository contains an automatic code generator to build comvolutional kernel code for the SCAMP CPA chip.



## Usage

Run
`python3 generate_filter_demo.py`

To edit the filter that gets created as well as to modify the search parameters, edit this file.


## What it does
It approximates the filter up to the specified approximation depth. It then runs the _reverse splitting algorithm_ to find optimal plans for assembling the filter. After that, a relaxation step minimises the number of operations required. As a last step, register allocation is done by means of graph colorin