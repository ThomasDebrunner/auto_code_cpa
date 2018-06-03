# Automatic Code Generation for SIMD Cellular Processor Arrays

## Introduction
This repository contains an implementation of an algorithm that can automatically generate code for Cellular Processor Arrays (CPAs) from a convolutional kernel representation. It is targeted towards the *SCAMP* family of devices

A **Cellular Processor Array (CPA)** is massively parallel image processing device that has minimal computing capabillities built into every pixel. This makes certain image processing tasks extremely fast and power efficient. The challenge is to program these devices. The algorithm in this repository can automatically generate code for convolutional filters.

**Example**

Consider a Sobel edge detection filter:

```
┌         ┐
│ 1  0 -1 │
│ 2  0 -2 │
│ 1  0 -1 │
└         ┘
```

On a **CPA** smart code for this filter could look like this, considering that we want to filter image in register `A` into register `A`, and storing intermediate values in register `B`.

```
B = north(A)
A = add(A, B)
B = south(A)
A = add(A, B)
B = east(A)
A = west(A)
A = sub(A, B)
```

Finding programs as short as possible for arbitrary filters is a non-trivial problem that this algorithm solves.

## Usage

Run
`python3 generate_filter_demo.py` to run a demo. You can edit the file to adjust parameters. 

To incorporate the filter generator to your application (Python) you can also import the code generation function via `from scamp_filter import generate`


## Parameters
* **start_reg** : String - The register [A-F] the image to be filtered is stored
* **target_reg** : String - The register [A-F] the result image should be stored
* **available_regs** : List - A list of available registers to store intermediate results. All values in these registers will potentially get overridden
* **verbose** : Integer - Verbosity level. 0: silent, 9: most textually verbose, 10: plot graphs
* **out_format** : ["APRON" | "CSIM"] - The code format the resulting code should be written in. *APRON* is a format understood by older SCAMP hardware and the APRON simulator. *CSIM* is a C format understood by the **[cpa-sim](https://github.com/najiji/cpa-sim)** simulator. Note that the *CSIM* format comments out all of the data-moving instructions and introduces `_transform` instructions for the simulator. This is an effort to speed up simulation. To run on real hardware, one would have to remove the `_transform` instructions and uncomment the individual data movement instructions.
* **approx_depth** : Integer - the `2^(-D)` approximation depth of the filter generation. The chip approximates all scalar values as additions/subtractions of `2^k` scalings of the value. The higher the approximation depth, the better the approximation, but the more complex the program
* **pair_props** : PairGenProps object - An object containing the more technical settings to tune the search algorithm. 


### Search parameters
A reasonable guideline for a speedy result would be something like:

```
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
```

The algorithm is based on a recursion that splits a set into subsets in every step. As the number of possible subsets define the branching factor, it is important to explore the more promising parts of the tree first to speed things up. The parameters here guide the heuristics of the split-pair generating algorithm. 

* `sort_distinct_pos [True]` - Explore pairs first that have an effect on as many distinct locations as possible in the filter.
* `short_distance_first [True]` - Explore pairs first that exhibit short transformation distances
* `low_scale_first [True]` - Explore pairs with lower transformation scale first
* `exhaustive [False]` - Explore all possible split-pairs
* `generate_all [True]` - Generate all not-excluded pairs first and apply the sorting metrincs afterwards, rather than generating the pairs as-needed.
* `max_sets [True]` - Only consider sets of the maximum possible size for a given transformation
* `randomize [False]` - Randomize the ordering of the sets

**NOTE:**

Some of these parameter combinations have undefined behaviour. For example, sorting and randomizing at the same time. Some settings may loose their effect when other settings are set. 