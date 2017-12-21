Terminal styling for structured data
------------------------------------

.. image:: https://travis-ci.org/pyout/pyout.svg?branch=master
    :target: https://travis-ci.org/pyout/pyout

This Python module is created to provide a way to produce nice text
outputs from structured records.  One of the goals is to separate
style (color, formatting, etc), behavior (display as soon as available
and adjust later, or wait until all records come in), and actual data
apart so they could be manipulated independently.

It is largely WiP ATM which later intends to replace custom code in
`niceman <http://niceman.repronim.org>`_ and
`datalad <http://datalad.org>`_ `ls` commands by providing a helper to
consistently present tabular data.
