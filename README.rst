===========================================
pyout: Terminal styling for structured data
===========================================

.. image:: https://travis-ci.org/pyout/pyout.svg?branch=master
    :target: https://travis-ci.org/pyout/pyout
.. image:: https://codecov.io/github/pyout/pyout/coverage.svg?branch=master
    :target: https://codecov.io/github/pyout/pyout?branch=master
.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
    :target: https://opensource.org/licenses/MIT

``pyout`` is a Python package that defines an interface for writing
structured records as a table in a terminal.  It is being developed to
replace custom code for displaying tabular data in in NICEMAN_ and
DataLad_.

A primary goal of the interface is the separation of content from
style and presentation.  Current capabilities include

- automatic width adjustment and updating of previous values

- styling based on a field value or specified interval

- defining a transform function that maps a raw value to the displayed
  value

- defining a summary function that generates a summary of a column
  (e.g., value totals)

- support for delayed, asynchronous values that are added to the table
  as they come in


Status
======

This package is currently in early stages of development.  While it
should be usable in its current form, it may change in substantial
ways that break backward compatibility, and many aspects currently
lack polish and documentation.

It is developed and tested under Python 2 and 3 in GNU/Linux
environments and is expected to work in macOS environments as well.
There is currently very limited Windows support.


License
=======

``pyout`` is under the MIT License.  See the COPYING file.


.. _DataLad: https://datalad.org
.. _NICEMAN: http://niceman.repronim.org
