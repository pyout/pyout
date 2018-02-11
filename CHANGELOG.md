# Changelog
All notable changes to this project will be documented (for humans) in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

TODO Summary

### Added

- A new style attribute, "transform", has been added to the schema.

  This feature can be used to provide a function that takes a field
  value and returns a transformed field value.

- Row values can now be generator functions or generator objects in
  addition to plain values and non-generator functions.

  This feature can be used to update previous fields with a sequence
  of new values rather than a one-time update.

### Changed

- `pyout` has been restructured from a single module into a package.
  The only associated user-facing change is the rename of
  `pyout.SCHEMA` to `pyout.schema`.

- The style attribute "label" has been renamed to "lookup".

### Deprecated
### Fixed
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
