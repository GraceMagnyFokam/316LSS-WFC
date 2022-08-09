# WFC Implementation for Procedural Generation of EBSDs

This is my research implementation of WaveFunctionCollapse in Python. 
Originally created by Issac Karth (iKarth).

It has two goals:

* Make it easier to understand how the algorithm operates
* Provide a testbed for experimenting with alternate heuristics and features

For more general-purpose WFC information, the original reference repository remains the best resource: https://github.com/mxgmn/WaveFunctionCollapse
The original repository from iKarth might also be a useful resource: https://github.com/ikarth/wfc_2019f

## Running WFC

The file I used to run the WFC is called deformed_iron_wfc_run.py.

The arguments it accepts are:

- `tile_size=1`: size of the tiles it uses (1 is fine for pixel images, larger is for things like a Super Metroid map)
- `pattern_width=2`: size of the patterns; usually 2 or 3 because bigger gets slower and
- `rotations=8`: how many reflections and/or rotations to use with the patterns
- `output_size=[32,32]`: how big the output image is
- `attempt_limit=100`: stop after this many tries
- `output_periodic=True`: the output wraps at the edges
- `input_periodic=False`: the input wraps at the edges
- `visualize=False`: write intermediate images to disk? requires filename.
- `backtracking=True`: do we use backtracking if we run into a contradiction?
- `log_filename="out_log"`: what should the log file be named?
- `logging=True`: should we write to a log file? requires filename.

The specific input that I used is called "Deformed Iron EBSD" and can be found at `images/Inputs/Deformed Iron EBSD.png`
It's a cropped version of the IPF-X image in the original dataset: https://doi.org/10.5281/zenodo.1214828![image](https://user-images.githubusercontent.com/88839490/183575053-0f6e9d83-6594-4069-b62a-ff265bbe1895.png)

## Test

```
pytest
```

## Documentation

```
python setup.py build_sphinx
```

With linux the documentation can be displayed with:

```
xdg-open build/sphinx/index.html
```
