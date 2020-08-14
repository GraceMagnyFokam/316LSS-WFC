from scipy import sparse
import numpy
import sys
import math
import itertools
from numba import jit

# By default Python has a very low recursion limit.
# Might still be better to rewrite te recursion as a loop, of course
sys.setrecursionlimit(5500)


class Contradiction(Exception):
  """Solving could not proceed without backtracking/restarting."""
  pass

class TimedOut(Exception):
  """Solve timed out."""
  pass

class StopEarly(Exception):
  """Aborting solve early."""
  pass

def makeWave(n, w, h, ground=None):
  wave = numpy.ones((n, w, h),dtype=bool)
  if ground is not None:
      wave[:,:,h-1] = 0
      for g in ground:
        wave[g,:,] = 0
        wave[g,:,h-1] = 1
  #print(wave)
  #for i in range(wave.shape[0]):
  #  print(wave[i])
  return wave

def makeAdj(adjLists):
  adjMatrices = {}
  #print(adjLists)
  num_patterns = len(list(adjLists.values())[0])
  for d in adjLists:
    m = numpy.zeros((num_patterns,num_patterns),dtype=bool)
    for i, js in enumerate(adjLists[d]):
      #print(js)
      for j in js:
        m[i,j] = 1
    adjMatrices[d] = sparse.csr_matrix(m)
  return adjMatrices


######################################
# Location Heuristics

def makeRandomLocationHeuristic(preferences):
  def randomLocationHeuristic(wave):
    unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
    cell_weights = numpy.where(unresolved_cell_mask, preferences, numpy.inf)
    row, col = numpy.unravel_index(numpy.argmin(cell_weights), cell_weights.shape)
    return [row, col]
  return randomLocationHeuristic

def makeEntropyLocationHeuristic(preferences):
  def entropyLocationHeuristic(wave):
    unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
    cell_weights = numpy.where(unresolved_cell_mask, preferences + numpy.count_nonzero(wave, axis=0), numpy.inf)
    row, col = numpy.unravel_index(numpy.argmin(cell_weights), cell_weights.shape)
    return [row, col]
  return entropyLocationHeuristic

def makeAntiEntropyLocationHeuristic(preferences):
  def antiEntropyLocationHeuristic(wave):
    unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
    cell_weights = numpy.where(unresolved_cell_mask, preferences + numpy.count_nonzero(wave, axis=0), -numpy.inf)
    row, col = numpy.unravel_index(numpy.argmax(cell_weights), cell_weights.shape)
    return [row, col]
  return antiEntropyLocationHeuristic


def spiral_transforms():
  for N in itertools.count(start=1):
    if N % 2 == 0:
      yield (0, 1) # right
      for i in range(N):
        yield (1, 0) # down
      for i in range(N):
        yield (0, -1) # left
    else:
      yield (0, -1) # left
      for i in range(N):
        yield (-1, 0) # up
      for i in range(N):
        yield (0, 1) # right

def spiral_coords(x, y):
  yield x,y
  for transform in spiral_transforms():
    x += transform[0]
    y += transform[1]
    yield x,y

def fill_with_curve(arr, curve_gen):
    arr_len = numpy.prod(arr.shape)
    fill = 0
    for idx, coord in enumerate(curve_gen):
      #print(fill, idx, coord)
      if fill < arr_len:
        try:
          arr[coord[0], coord[1]] = fill / arr_len
          fill += 1
        except IndexError:
          pass
      else:
        break
    #print(arr)
    return arr



def makeSpiralLocationHeuristic(preferences):
  # https://stackoverflow.com/a/23707273/5562922

  spiral_gen = (sc for sc in spiral_coords(preferences.shape[0] // 2, preferences.shape[1] // 2))

  cell_order = fill_with_curve(preferences, spiral_gen)

  def spiralLocationHeuristic(wave):
    unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
    cell_weights = numpy.where(unresolved_cell_mask, cell_order, numpy.inf)
    row, col = numpy.unravel_index(numpy.argmin(cell_weights), cell_weights.shape)
    return [row, col]

  return spiralLocationHeuristic

from hilbertcurve.hilbertcurve import HilbertCurve

def makeHilbertLocationHeuristic(preferences):
  curve_size = math.ceil( math.sqrt(max(preferences.shape[0], preferences.shape[1])))
  print(curve_size)
  curve_size = 4
  h_curve = HilbertCurve(curve_size, 2)

  def h_coords():
    for i in range(100000):
      #print(i)
      try:
        coords = h_curve.coordinates_from_distance(i)
      except ValueError:
          coords = [0,0]
      #print(coords)
      yield coords

  cell_order = fill_with_curve(preferences, h_coords())
  #print(cell_order)

  def hilbertLocationHeuristic(wave):
    unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
    cell_weights = numpy.where(unresolved_cell_mask, cell_order, numpy.inf)
    row, col = numpy.unravel_index(numpy.argmin(cell_weights), cell_weights.shape)
    return [row, col]

  return hilbertLocationHeuristic

def simpleLocationHeuristic(wave):
  unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
  cell_weights = numpy.where(unresolved_cell_mask, numpy.count_nonzero(wave, axis=0), numpy.inf)
  row, col = numpy.unravel_index(numpy.argmin(cell_weights), cell_weights.shape)
  return [row, col]


def lexicalLocationHeuristic(wave):
  unresolved_cell_mask = (numpy.count_nonzero(wave, axis=0) > 1)
  cell_weights = numpy.where(unresolved_cell_mask, 1.0, numpy.inf)
  row, col = numpy.unravel_index(numpy.argmin(cell_weights), cell_weights.shape)
  return [row, col]

#####################################
# Pattern Heuristics

def lexicalPatternHeuristic(weights):
  return numpy.nonzero(weights)[0][0]

def makeWeightedPatternHeuristic(weights):
  num_of_patterns = len(weights)
  def weightedPatternHeuristic(wave, _):
    # TODO: there's maybe a faster, more controlled way to do this sampling...
    weighted_wave = (weights * wave)
    weighted_wave /= weighted_wave.sum()
    result = numpy.random.choice(num_of_patterns, p=weighted_wave)
    return result
  return weightedPatternHeuristic

def makeRarestPatternHeuristic(weights):
  """Return a function that chooses the rarest (currently least-used) pattern."""
  num_of_patterns = len(weights)
  def weightedPatternHeuristic(wave, total_wave):
    print(total_wave.shape)
    #[print(e) for e in wave]
    wave_sums = numpy.sum(total_wave, (1,2))
    #print(wave_sums)
    selected_pattern = numpy.random.choice(numpy.where(wave_sums == wave_sums.max())[0])
    return selected_pattern
  return weightedPatternHeuristic



def makeMostCommonPatternHeuristic(weights):
  """Return a function that chooses the most common (currently most-used) pattern."""
  num_of_patterns = len(weights)
  def weightedPatternHeuristic(wave, total_wave):
    print(total_wave.shape)
    #[print(e) for e in wave]
    wave_sums = numpy.sum(total_wave, (1,2))
    selected_pattern = numpy.random.choice(numpy.where(wave_sums == wave_sums.min())[0])
    return selected_pattern
  return weightedPatternHeuristic

def makeRandomPatternHeuristic(weights):
  num_of_patterns = len(weights)
  def randomPatternHeuristic(wave, _):
    # TODO: there's maybe a faster, more controlled way to do this sampling...
    weighted_wave = (1.0 * wave)
    weighted_wave /= weighted_wave.sum()
    result = numpy.random.choice(num_of_patterns, p=weighted_wave)
    return result
  return randomPatternHeuristic


######################################
# Global Constraints

def make_global_use_all_patterns():
  def global_use_all_patterns(wave):
    """Returns true if at least one instance of each pattern is still possible."""
    return numpy.all(numpy.any(wave, axis=(1,2)))
  return global_use_all_patterns



#####################################
# Solver

def propagate(wave, adj_offsets, adj_matrix, periodic=False, onPropagate=None):
  last_count = wave.sum()

  while True:
    supports = {}
    if periodic:
      padded = numpy.pad(wave,((0,0),(1,1),(1,1)), mode='wrap')
    else:
      padded = numpy.pad(wave,((0,0),(1,1),(1,1)), mode='constant',constant_values=True)
    for d_count, dir in adj_offsets:
      dx,dy = dir
      shifted = numpy.roll(wave, (dx, dy), axis=(1,2))
      #shifted = padded[:,1+dx:1+wave.shape[1]+dx,1+dy:1+wave.shape[2]+dy]
      supports[dir] = (adj_matrix[d_count] @ shifted.reshape(shifted.shape[0], -1)).reshape(shifted.shape) > 0

    for d_count, d in adj_offsets:
      wave *= supports[d]

    if wave.sum() == last_count:
      break
    else:
      last_count = wave.sum()

  if onPropagate:
    onPropagate(wave)

  if (wave.sum(axis=0) == 0).any():
    raise Contradiction


def propagate_with_stack(wave, adj_offsets, inverted_offsets, adj_matrix, propagation_stack, compatibility_matrix, periodic=False, onPropagate=None):
  if onPropagate:
    onPropagate(wave)
  while len(propagation_stack) > 0:
    curr_cell, curr_pat = propagation_stack.pop()
    for d_count, dir in adj_offsets:
      dx,dy = dir
      if periodic:
        dx = ((curr_cell[0] + dx) + wave.shape[1]) % wave.shape[1]
        dy = ((curr_cell[1] + dy) + wave.shape[2]) % wave.shape[2]
      else:
        if (dx < 0) or (dy < 0) or (dx >= wave.shape[1]) or (dy >= wave.shape[2]):
          break
      adj_propagator = adj_matrix[d_count, curr_pat]
      for p_count in range(adj_propagator.shape[0]):
        adj_valid = adj_propagator[p_count]
        if adj_valid:
          compatibility_matrix[dx, dy, p_count, d_count] -= 1
          if compatibility_matrix[dx, dy, p_count, d_count] == 0:
            wave, compatibility_matrix, propagation_stack = ban(wave, compatibility_matrix, propagation_stack, dx, dy, p_count, adj_offsets, inverted_offsets)
    if (wave.sum(axis=0) <= 0).any():
      raise Contradiction
  if (wave.sum(axis=0) <= 0).any():
    raise Contradiction

def observe(wave, locationHeuristic, patternHeuristic):
  i,j = locationHeuristic(wave)
  pattern = patternHeuristic(wave[:,i,j], wave)
  return pattern, i, j

def ban(wave, compatibility_matrix, prop_stack, i, j, pattern, adj_offsets, inverted_offsets):
  wave[pattern, i, j] = False
  for d_count, dir in adj_offsets:
    dx,dy = dir
    compatibility_matrix[i, j, pattern, d_count] = 0
  prop_stack.append(((i, j), pattern))
  return wave, compatibility_matrix, prop_stack

def invert_offsets(adj_offsets):
  inverted_offsets = []
  for d_count, dir in adj_offsets:
    dx,dy = dir
    flipped = (0-dx, 0-dy)
    for d_count2, dir2 in adj_offsets:
      i,j = dir2
      if flipped == (i,j):
        inverted_offsets.append((d_count2, dir2))
  return inverted_offsets

def run_with_loop(wave, adj_offsets, adj_matrix, locationHeuristic, patternHeuristic, periodic=False, backtracking=False, onBacktrack=None, onChoice=None, onObserve=None, onPropagate=None, checkFeasible=None, onFinal=None, depth=0, depth_limit=None, use_a_stack=False):
  inverted_offsets = invert_offsets(adj_offsets)
  compatibility_matrix = numpy.zeros((wave.shape[1], wave.shape[2], wave.shape[0], len(adj_offsets)), dtype=numpy.int16)
  for i in range(wave.shape[1]):
    for j in range(wave.shape[2]):
      for d_count, dir in adj_offsets:
        dx,dy = dir
        for p1 in range(wave.shape[0]):
          compatibility_matrix[i, j, p1, d_count] = adj_matrix[d_count, :, p1].sum()
  original = wave.copy()
  past_waves = [(wave.copy(), compatibility_matrix.copy())]
  if not use_a_stack:
    propagate(wave, adj_offsets, adj_matrix, periodic=periodic, onPropagate=onPropagate)
  propagation_stack = []

  depth = 0
  while True:
    if checkFeasible:
      if not checkFeasible(wave):
        raise Contradiction
      if depth_limit:
        if depth > depthlimit:
          raise TimedOut
    if depth % 10 == 0:
      #print(depth)
      print(f"{wave.sum()} / {depth}")
      #print(compatibility_matrix.sum())
    try:
      pattern, i, j = observe(wave, locationHeuristic, patternHeuristic)
      if onChoice:
        onChoice(pattern, i, j)
      for p1 in range(wave.shape[0]):
        if p1 != pattern:
          if wave[p1, i, j]:
            wave, compatibility_matrix, propagation_stack = ban(wave, compatibility_matrix, propagation_stack, i, j, p1, adj_offsets, inverted_offsets)
      if onObserve:
        onObserve(wave)
      if use_a_stack:
        propagate_with_stack(wave, adj_offsets, inverted_offsets, adj_matrix, propagation_stack, compatibility_matrix, periodic=periodic, onPropagate=onPropagate)
      else:
        propagate(wave, adj_offsets, adj_matrix, periodic=periodic, onPropagate=onPropagate)
      if wave.sum() > wave.shape[1] * wave.shape[2]:
        pass
      else:
        if onFinal:
          onFinal(wave)
        return numpy.argmax(wave, 0)
      past_waves.append((wave.copy(), compatibility_matrix.copy()))
    except Contradiction:
      if backtracking and (len(past_waves) > 0):
        if onBacktrack:
          onBacktrack()
        wave, compatibility_matrix = past_waves.pop()
        wave[pattern, i, j] = False
      else:
        if onFinal:
          onFinal(wave)
        raise
    depth += 1

def run(wave, adj_offsets, adj_matrix, locationHeuristic, patternHeuristic, periodic=False, backtracking=False, onBacktrack=None, onChoice=None, onObserve=None, onPropagate=None, checkFeasible=None, onFinal=None, depth=0, depth_limit=None):
  #print("run.")
  if checkFeasible:
    if not checkFeasible(wave):
      raise Contradiction
    if depth_limit:
      if depth > depthlimit:
        raise TimedOut
  if depth % 2 == 0:
    print(depth)
  original = wave.copy()
  propagate(wave, adj_offsets, adj_matrix, periodic=periodic, onPropagate=onPropagate)
  try:
    pattern, i, j = observe(wave, locationHeuristic, patternHeuristic)
    if onChoice:
      onChoice(pattern, i, j)
    wave[:, i, j] = False
    wave[pattern, i, j] = True
    if onObserve:
      onObserve(wave)

    propagate(wave, adj_offsets, adj_matrix, periodic=periodic, onPropagate=onPropagate)
    if wave.sum() > wave.shape[1] * wave.shape[2]:
      #return run(wave, adj, locationHeuristic, patternHeuristic, periodic, backtracking, onBacktrack)
      return run(wave, adj_offsets, adj_matrix, locationHeuristic, patternHeuristic, periodic=periodic, backtracking=backtracking, onBacktrack=onBacktrack, onChoice=onChoice, onObserve=onObserve, onPropagate=onPropagate, checkFeasible=checkFeasible, depth=depth+1, depth_limit=depth_limit)
    else:
      if onFinal:
        onFinal(wave)
      return numpy.argmax(wave, 0)
  except Contradiction:
    if backtracking:
      if onBacktrack:
        onBacktrack()
      wave = original
      wave[pattern, i, j] = False
      return run(wave, adj_offsets, adj_matrix, locationHeuristic, patternHeuristic, periodic=periodic, backtracking=backtracking, onBacktrack=onBacktrack, onChoice=onChoice, onObserve=onObserve, onPropagate=onPropagate, checkFeasible=checkFeasible, depth=depth+1, depth_limit=depth_limit)
    else:
      if onFinal:
        onFinal(wave)
      raise

#############################
# Tests

def test_makeWave():
  wave = makeWave(3, 10, 20, ground=[-1])
  #print(wave)
  #print(wave.sum())
  #print((2*10*19) + (1*10*1))
  assert wave.sum() == (2*10*19) + (1*10*1)
  assert wave[2,5,19] == True
  assert wave[1,5,19] == False

def test_entropyLocationHeuristic():
    wave = numpy.ones((5, 3, 4), dtype=bool) # everthing is possible
    wave[1:,0, 0] = False # first cell is fully observed
    wave[4, :, 2] = False
    preferences = numpy.ones((3, 4), dtype=float) * 0.5
    preferences[1, 2] = 0.3
    preferences[1, 1] = 0.1
    heu = makeEntropyLocationHeuristic(preferences)
    result = heu(wave)
    assert [1, 2] == result

def test_observe():

  my_wave = numpy.ones((5, 3, 4), dtype=bool)
  my_wave[0,1,2] = False

  def locHeu(wave):
    assert numpy.array_equal(wave, my_wave)
    return 1,2
  def patHeu(weights):
    assert numpy.array_equal(weights, my_wave[:,1,2])
    return 3

  assert observe(my_wave,
                 locationHeuristic=locHeu,
                 patternHeuristic=patHeu) == (3,1,2)

def test_propagate():
  wave = numpy.ones((3,3,4),dtype=bool)
  adjLists = {}
  # checkerboard #0/#1 or solid fill #2
  adjLists[(+1,0)] = adjLists[(-1,0)] = adjLists[(0,+1)] = adjLists[(0,-1)] = [[1],[0],[2]]
  wave[:,0,0] = False
  wave[0,0,0] = True
  adj = makeAdj(adjLists)
  propagate(wave, adj, periodic=False)
  expected_result = numpy.array([[[ True, False,  True, False],
          [False,  True, False,  True],
          [ True, False,  True, False]],
        [[False,  True, False,  True],
          [ True, False,  True, False],
          [False,  True, False,  True]],
        [[False, False, False, False],
          [False, False, False, False],
          [False, False, False, False]]])
  assert numpy.array_equal(wave, expected_result)


def test_run():
  wave = makeWave(3,3,4)
  adjLists = {}
  adjLists[(+1,0)] = adjLists[(-1,0)] = adjLists[(0,+1)] = adjLists[(0,-1)] = [[1],[0],[2]]
  adj = makeAdj(adjLists)

  first_result = run(wave.copy(),
      adj,
      locationHeuristic=lexicalLocationHeuristic,
      patternHeuristic=lexicalPatternHeuristic,
      periodic=False)

  expected_first_result = numpy.array([[0, 1, 0, 1],[1, 0, 1, 0],[0, 1, 0, 1]])

  assert numpy.array_equal(first_result, expected_first_result)

  event_log = []
  def onChoice(pattern, i, j):
    event_log.append((pattern,i,j))
  def onBacktrack():
    event_log.append('backtrack')

  second_result = run(wave.copy(),
      adj,
      locationHeuristic=lexicalLocationHeuristic,
      patternHeuristic=lexicalPatternHeuristic,
      periodic=True,
      backtracking=True,
      onChoice=onChoice,
      onBacktrack=onBacktrack)

  expected_second_result = numpy.array([[2, 2, 2, 2],[2, 2, 2, 2],[2, 2, 2, 2]])

  assert numpy.array_equal(second_result, expected_second_result)
  print(event_log)
  assert event_log == [(0, 0, 0), 'backtrack']

  def explode(wave):
    if wave.sum() < 20:
      raise Infeasible

  try:
    result = run(wave.copy(),
        adj,
        locationHeuristic=lexicalLocationHeuristic,
        patternHeuristic=lexicalPatternHeuristic,
        periodic=True,
        backtracking=True,
        checkFeasible=explode)
    print(result)
    happy = False
  except Contradiction:
    happy = True

  assert happy

def test_recurse_vs_loop():
  from wfc_tiles import make_tile_catalog
  from wfc_patterns import make_pattern_catalog, pattern_grid_to_tiles
  from wfc_adjacency import adjacency_extraction
  from wfc_solver import run, makeWave, makeAdj, lexicalLocationHeuristic, lexicalPatternHeuristic
  from wfc_visualize import figure_list_of_tiles, figure_false_color_tile_grid, figure_pattern_catalog, render_tiles_to_output, figure_adjacencies

  import imageio
  img = imageio.imread("../images/samples/Red Maze.png")
  tile_size = 1
  pattern_width = 2
  rotations = 0
  output_size = [84, 84]
  ground = None
  direction_offsets = list(enumerate([(0, -1), (1, 0), (0, 1), (-1, 0)]))
  tile_catalog, tile_grid, code_list, unique_tiles = make_tile_catalog(img, tile_size)
  pattern_catalog, pattern_weights, pattern_list, pattern_grid = make_pattern_catalog(tile_grid, pattern_width, rotations)
  adjacency_relations = adjacency_extraction(pattern_grid, pattern_catalog, direction_offsets)
  number_of_patterns = len(pattern_weights)
  encode_patterns = dict(enumerate(pattern_list))
  decode_patterns = {x: i for i, x in enumerate(pattern_list)}
  decode_directions = {j:i for i,j in direction_offsets}
  adjacency_list = {}
  for i,d in direction_offsets:
    adjacency_list[d] = [set() for i in pattern_weights]
  for i in adjacency_relations:
    adjacency_list[i[0]][decode_patterns[i[1]]].add(decode_patterns[i[2]])
  wave = makeWave(number_of_patterns, output_size[0], output_size[1])
  adjacency_matrix = makeAdj(adjacency_list)
  solution_loop = run(wave.copy(),
               adjacency_matrix,
               locationHeuristic=lexicalLocationHeuristic,
               patternHeuristic=lexicalPatternHeuristic,
               periodic=True,
               backtracking=False,
               onChoice=None,
               onBacktrack=None)
  solution_recurse = run_recurse(wave.copy(),
               adjacency_matrix,
               locationHeuristic=lexicalLocationHeuristic,
               patternHeuristic=lexicalPatternHeuristic,
               periodic=True,
               backtracking=False,
               onChoice=None,
               onBacktrack=None)
  assert (numpy.array_equiv(solution_loop, solution_recurse))






from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

if __name__ == "__main__":
  with PyCallGraph(output=GraphvizOutput()):
    test_makeWave()
    test_entropyLocationHeuristic()
    test_observe()
    test_propagate()
    test_run()
    #test_recurse_vs_loop()
