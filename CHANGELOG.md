# v0.7.3 (Tue Mar 28 2023)

#### 🐛 Bug Fix

- Accepting either bless* (blessed, blessings) library [#137](https://github.com/pyout/pyout/pull/137) ([@TheChymera](https://github.com/TheChymera) [@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- codespell: workflow, typo fix, minor var rename [#139](https://github.com/pyout/pyout/pull/139) ([@yarikoptic](https://github.com/yarikoptic))

#### 🧪 Tests

- Add python 3.11 into testing [#140](https://github.com/pyout/pyout/pull/140) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Horea Christian ([@TheChymera](https://github.com/TheChymera))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.7.2 (Thu Feb 03 2022)

#### 🐛 Bug Fix

- Adjust README for needing 3.7 [#134](https://github.com/pyout/pyout/pull/134) ([@yarikoptic](https://github.com/yarikoptic))
- github+appveyor: add 3.7 into matrix since we support it [#134](https://github.com/pyout/pyout/pull/134) ([@yarikoptic](https://github.com/yarikoptic))
- appveyor: specify newer base image, drop 32bit, drop PYTHON env var [#134](https://github.com/pyout/pyout/pull/134) ([@yarikoptic](https://github.com/yarikoptic))
- Drop Python 3.6 support, add testing for 3.10, test against 3.8 on appveyor [#134](https://github.com/pyout/pyout/pull/134) ([@yarikoptic](https://github.com/yarikoptic))
- Declare JSON schema as following Draft 7 [#131](https://github.com/pyout/pyout/pull/131) ([@jwodder](https://github.com/jwodder))

#### 🏠 Internal

- Set up auto [#133](https://github.com/pyout/pyout/pull/133) ([@jwodder](https://github.com/jwodder))

#### Authors: 2

- John T. Wodder II ([@jwodder](https://github.com/jwodder))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# [0.7.1] - 2021-05-14

- For a table with a summary, encountering an unknown row led to lines
  before the first line of the table being overwritten.

# [0.7.0] - 2020-11-13

- Python 3.6 or later is now required.

- `Tabular` now tries to detect changes in the terminal's width and
   height.

- The new context manager `Tabular.outside_write` can be used by block
  further output from `Tabular` so that callers can write to the
  screen, restoring the table on exit.

# [0.6.1] - 2020-08-04

- Before the last release, `Tabular` worked when given a tuple for
  `columns` instead of one of the documented types (a list of strings
  or an `OrderedDict`).  This previous behavior has been restored.

# [0.6.0] - 2020-08-03

## Changed

- The list of known columns is now expanded dynamically if a row
  passed to `Tabular` contains a new column, provided that either the
  row is a dictionary or a value of the row is a callable that returns
  a dictionary.

## Added

- A simple example of using `pyout.Tabular`, contributed by vsoch, is
  now available in [examples/simple/](examples/simple).

# [0.5.1] - 2020-04-08

- Fixed two racy tests.

# [0.5.0] - 2019-11-18

## Removed

- Support for Python 2 has been dropped.  Python 3.4 or later is
  required.

## Added

- A new style attribute, "hide", makes it possible to hide a column,
  either unconditionally or until `Tabular` is called with a record
  that includes the column.

- The `Tabular` class now accepts a `max_workers` argument that
  controls the maximum number of asynchronous workers that run
  concurrently.

- The `Tabular` class gained a `continue_on_failure` argument.  When
  set to false, an exception in an asynchronous worker is raised as it
  is encountered rather than after all asynchronous workers have
  returned.

- `Tabular` now waits until the asynchronous workers of the top three
  rows have completed before adding a new row that would advance the
  screen.  The number of top rows that are considered can be
  configured via the new `wait_for_top` keyword argument.

## Changed

- The `jsonschema` module (v3.0.0 or later) is now a requirement
  rather than an optional dependency.

- The `mode` property of the `Tabular` class has been removed.
  The mode should instead be specified via the `mode` keyword argument
  when initializing the class.

- The calculation of auto-width columns has been enhanced so that the
  available width is more evenly spread across the columns.  The width
  style attribute takes a "weight" key to allow a column's growth to
  be prioritized.

- The width style attribute learned to take fraction that represents
  the proportion of the table.  For example, setting the "max" key to
  0.5 means that the key should exceed half of the total table width.

- When operating non-interactively, by default the width is now
  expanded to accommodate the content.  To force a particular table
  width in this situation, set the table's width using the "width_"
  style attribute.

# [0.4.1] - 2019-10-02

Fix stale `pyout.__version__`, which hasn't been updated since v0.1.0.

# [0.4.0] - 2019-03-24

## Added

- The new style attribute "re_lookup" adds support for styling a value
  when it matches a regular expression.

- `pyout` should now run, in a very limited way, on Windows.  The
  `Tabular` class used on Windows, `tabular_dummy.Tabular`, does not
  support updating previous lines or styling values with the "color",
  "bold", or "underline" keys.

- The Tabular class now returns a row's value when indexed with a
  tuple containing the ID values for that row.  This is useful for
  inspecting values populated by asynchronous functions.

- The Tabular class now accepts a `stream` parameter that can be used
  to specify a stream other than `sys.stdout`.

- Whether Tabular behaves as though the output stream is a TTY (for
  example, by coloring the output) can now be controlled with the
  `interactive` parameter.

# [0.3.0] - 2018-12-18

## Added

- A fixed width could be specified by setting the "width" style
  attribute to an integer, but there was previously no way to specify
  the truncation marker.  A "width" key is now accepted in the
  dictionary form (e.g., `{"width": 10, "marker": "…"}`).

- The "width" style attribute now supports a "truncate" key that can
  be "left", "center", or "right" (e.g., `{"width": {"truncate":
  "left"}}}`).

## Changed

- When giving a dictionary as the "width" style attribute's value, the
  "auto" key is no longer supported because the appropriate behavior
  can be inferred from the "min", "max", and "width" keys.

## Fixed

- The output was corrupted when a callback function tried to update a
  line that was no longer visible on the screen.

- When a table did not include a summary, "incremental" and "final"
  mode added "None" as the last row.

# [0.2.0] - 2018-12-10

This release includes several new style attributes, enhancements to
how asynchronous values can be defined, and support for different
output "modes".

## Added

- A new style attribute, "transform", can be used to provide a
  function that takes a field value and returns a transformed field
  value.

- A new style attribute, "aggregate", can be used to provide a
  function that summarizes values within a column.  The summary will
  be displayed at the bottom of the table.

- A new style attribute, "missing", allows customizing the value that
  is shown for missing values.

- A new style attribute, "delayed", instructs `pyout` to wrap value
  access in a callable, which is useful when obtaining values from
  properties that take time to compute.  Otherwise, the object's
  property would have to be wrapped in another callable by the caller.

- A new style attribute, "width_", determines the total width of the
  table, which is otherwise taken as the terminal's width.

- Row values can now be generator functions or generator objects in
  addition to plain values and non-generator functions.  This feature
  can be used to update previous fields with a sequence of new values
  rather than a one-time update.

- The Tabular class now has a `mode` property.  The default value,
  "update", means display row values as they come in, going back to
  update previous lines if needed.  If it is set to "incremental", no
  previous lines are updated.  If it is set to "final", values are
  only updated once, at the exit of the context manager.

## Changed

- `pyout` has been restructured from a single module into a package.
  The only associated user-facing change is the rename of
  `pyout.SCHEMA` to `pyout.schema`.

- The style attribute "label" has been renamed to "lookup".

- Flanking white space in a field is no longer underlined.

- In addition to the form `(initial value, callable)`, a plain
  callable can now be used as a field value.  In this case, the
  initial value will be an empty string by default and can configured
  with the "missing" style attribute.

## Fixed

- Rows that exceeded the terminal's width wrapped to the next line and
  broke pyout's line counting logic (used to, e.g., update a previous
  line).

# [0.1.0] - 2018-01-08

Initial release

This release adds a basic schema for styling columns (defined in
`pyout.SCHEMA`) and the `Tabular` class, which serves as the entry
point for writing tabular output.  The features at this point include
value-based styling, auto-sizing of column widths, a `rewrite` method
that allows the user to update a previous row, and the ability to
update previous fields by defining asynchronous callback functions.


[0.7.1]: https://github.com/pyout/pyout/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/pyout/pyout/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/pyout/pyout/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/pyout/pyout/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/pyout/pyout/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/pyout/pyout/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/pyout/pyout/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/pyout/pyout/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pyout/pyout/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pyout/pyout/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pyout/pyout/commits/v0.1.0
