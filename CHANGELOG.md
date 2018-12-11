# Changelog

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

TODO Summary

### Added

- A new style attribute, "transform", can be used to provide a
  function that takes a field value and returns a transformed field
  value.

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

### Deprecated
### Fixed

- Rows that exceeded the terminal's width wrapped to the next line and
  broke pyout's line counting logic (used to, e.g., update a previous
  line).

### Removed
### Security

## [0.1.0] - 2018-01-08

Initial release

This release adds a basic schema for styling columns (defined in
`pyout.SCHEMA`) and the `Tabular` class, which serves as the entry
point for writing tabular output.  The features at this point include
value-based styling, auto-sizing of column widths, a `rewrite` method
that allows the user to update a previous row, and the ability to
update previous fields by defining asynchronous callback functions.


[Unreleased]: https://github.com/pyout/pyout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pyout/pyout/commits/v0.1.0
