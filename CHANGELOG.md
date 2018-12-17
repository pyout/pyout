# Changelog

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]


### Added

- A fixed width could be specified by setting the "width" style
  attribute to an integer, but there was previously no way to specify
  the truncation marker.  A "width" key is now accepted in the
  dictionary form (e.g., `{"width": 10, "marker": "…"}`).

### Fixed

- The output was corrupted when a callback function tried to update a
  line that was no longer visible on the screen.

- When a table did not include a summary, "incremental" and "final"
  mode added "None" as the last row.

## [0.2.0] - 2018-12-10

This release includes several new style attributes, enhancements to
how asynchronous values can be defined, and support for different
output "modes".

### Added

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

### Changed

- `pyout` has been restructured from a single module into a package.
  The only associated user-facing change is the rename of
  `pyout.SCHEMA` to `pyout.schema`.

- The style attribute "label" has been renamed to "lookup".

- Flanking white space in a field is no longer underlined.

- In addition to the form `(initial value, callable)`, a plain
  callable can now be used as a field value.  In this case, the
  initial value will be an empty string by default and can configured
  with the "missing" style attribute.

### Fixed

- Rows that exceeded the terminal's width wrapped to the next line and
  broke pyout's line counting logic (used to, e.g., update a previous
  line).

## [0.1.0] - 2018-01-08

Initial release

This release adds a basic schema for styling columns (defined in
`pyout.SCHEMA`) and the `Tabular` class, which serves as the entry
point for writing tabular output.  The features at this point include
value-based styling, auto-sizing of column widths, a `rewrite` method
that allows the user to update a previous row, and the ability to
update previous fields by defining asynchronous callback functions.


[Unreleased]: https://github.com/pyout/pyout/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pyout/pyout/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pyout/pyout/commits/v0.1.0
