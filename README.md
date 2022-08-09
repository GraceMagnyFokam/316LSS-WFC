# WFC Implementation for Procedural Generation of EBSDs

This is my research implementation of WaveFunctionCollapse in Python. 
Originally created by Issac Karth (iKarth).

It has two goals:

* Make it easier to understand how the algorithm operates
* Provide a testbed for experimenting with alternate heuristics and features

For more general-purpose WFC information, the original reference repository remains the best resource: https://github.com/mxgmn/WaveFunctionCollapse
The original repository from iKarth might also be a useful resource: https://github.com/ikarth/wfc_2019f

## Running WFC

If you want direct control over running WFC, call `wfc_control.execute_wfc()`.

The arguments it accepts are:

- `tile_size=1`: size of the tiles it uses (1 is fine for pixel images, larger is for things like a Super Metroid map)
- `pattern_width=2`: size of the patterns; usually 2 or 3 because bigger gets slower and
- `rotations=8`: how many reflections and/or rotations to use with the patterns


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
