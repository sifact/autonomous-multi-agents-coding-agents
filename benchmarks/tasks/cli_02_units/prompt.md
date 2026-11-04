Write `main.py`, a unit converter, run as `python main.py VALUE FROM TO`
(for example `python main.py 5 km mi`).

- `VALUE` is parsed with `float()` and must be finite (`nan` and `inf` are invalid). It may be
  negative, e.g. `-40`.
- Unit names are case-insensitive (`KM`, `Km` and `km` are the same unit). Known units:
  - length, with metres per unit: `m` 1, `km` 1000, `cm` 0.01, `in` 0.0254, `ft` 0.3048,
    `mi` 1609.344;
  - temperature: `c` (Celsius), `f` (Fahrenheit), `k` (Kelvin).
  Convert length as `value * from_factor / to_factor`. Convert temperature through Kelvin:
  `K = C + 273.15`, `K = (F - 32) * 5 / 9 + 273.15`, and back with the inverse formulas.
- On success print exactly one line `<result> <to>` and exit 0. `<result>` is the converted
  number formatted with `f"{result:.4f}"`, and `<to>` is the target unit in lowercase.
  Example: `python main.py 5 km mi` prints `3.1069 mi`. Converting a unit to itself works.
- Errors print nothing on standard output, put a message starting with `error:` on standard
  error, and use these exit codes, checked in this order:
  - 2: the wrong number of arguments, or `VALUE` is not a finite number;
  - 3: `FROM` or `TO` is not a known unit (the message names the unit);
  - 4: the units are of different kinds (length vs temperature);
  - 5: a temperature below absolute zero, i.e. the Kelvin value of the input is less than 0.
    (`-273.15 c` is exactly 0 K and is allowed.)
