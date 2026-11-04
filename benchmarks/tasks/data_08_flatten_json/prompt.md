Write `solution.py` with a function `flatten_file(path: str, sep: str = ".") -> dict`.

`path` is a JSON file whose top level is an object or an array. The sample file
`config.json` is in the working directory. Return a flat dict that maps a path string to the
leaf value:

- Descend into objects: the path is the keys joined with `sep` (`{"a": {"b": 1}}` gives
  `{"a.b": 1}`).
- Descend into arrays: the element position (0-based) is used as the path part, written as
  decimal text (`{"a": [5, 6]}` gives `{"a.0": 5, "a.1": 6}`).
- Leaves are numbers, strings, booleans and `null` (`None`). Keep their values and types
  unchanged.
- An empty object or empty array is itself a leaf: it is kept as `{}` or `[]` under its
  path (`{"a": {}}` gives `{"a": {}}`).
- Keys appear in document order (depth first, left to right).
- If the top level is an array, its positions are the first path parts (`[{"x": 1}]` gives
  `{"0.x": 1}`). A top-level empty object or array gives `{}`.
- Read the file from the `path` argument, not from a hard-coded name.
