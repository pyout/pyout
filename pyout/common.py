"""Common components for styled output.

This modules contains things that would be shared across outputters if there
were any besides Tabular.  The Tabular class, though, still contains a good
amount of general logic that should be extracted if any other outputter is
actually added.
"""

from __future__ import unicode_literals

from collections import defaultdict, namedtuple
from collections import Mapping, Sequence, OrderedDict
from functools import partial
import inspect
from itertools import chain

import six

from pyout import elements
from pyout.field import Field, Nothing
from pyout.summary import Summary

NOTHING = Nothing()


class RowNormalizer(object):
    """Transform various input data forms to a common form.

    An un-normalized can be one of three kinds:

      * a mapping from column names to keys

      * a sequence of values in the same order as `columns`

      * any other value will be taken as an object where the column values can
        be accessed via an attribute with the same name

    To normalized a row, it is

      * converted to a dict that maps from column names to values

      * all callables are stripped out and replaced with their initial values

      * if the value for a column is missing, it is replaced with a Nothing
        instance whose value is specified by the column's style (an empty
        string by default)

    Parameters
    ----------
    columns : sequence of str
        Column names.
    style : dict, optional
        Column styles.

    Attributes
    ----------
    methods : callable
        A function that takes a row and returns a normalized one.  This is
        chosen at time of the first call.  All subsequent calls should use the
        same kind of row.
    nothings : dict
        Maps column name to the placeholder value to use if that column is
        missing.
    """

    def __init__(self, columns, style):
        self._columns = columns
        self.method = None

        self.delayed = defaultdict(list)
        self.delayed_columns = set()
        self.nothings = {}  # column => missing value

        for column in columns:
            cstyle = style[column]

            if "delayed" in cstyle:
                value = cstyle["delayed"]
                group = column if value is True else value
                self.delayed[group].append(column)
                self.delayed_columns.add(column)

            if "missing" in cstyle:
                self.nothings[column] = Nothing(cstyle["missing"])
            else:
                self.nothings[column] = NOTHING

    def __call__(self, row):
        """Normalize `row`

        Parameters
        ----------
        row : mapping, sequence, or other
            Data to normalize.

        Returns
        -------
        A tuple (callables, row), where `callables` is a list (as returned by
        `strip_callables`) and `row` is the normalized row.
        """
        if self.method is None:
            self.method = self._choose_normalizer(row)
        return self.method(row)

    def _choose_normalizer(self, row):
        if isinstance(row, Mapping):
            getter = self.getter_dict
        elif isinstance(row, Sequence):
            getter = self.getter_seq
        else:
            getter = self.getter_attrs
        return partial(self._normalize, getter)

    def _normalize(self, getter, row):
        if isinstance(row, Mapping):
            callables0 = self.strip_callables(row)
        else:
            callables0 = []

        norm_row = self._maybe_delay(getter, row, self._columns)
        # We need a second pass with strip_callables because norm_row will
        # contain new callables for any delayed values.
        callables1 = self.strip_callables(norm_row)
        return callables0 + callables1, norm_row

    def _maybe_delay(self, getter, row, columns):
        row_norm = {}
        for column in columns:
            if column not in self.delayed_columns:
                row_norm[column] = getter(row, column)

        def delay(cols):
            return lambda: {c: getter(row, c) for c in cols}

        for columns in self.delayed.values():
            key = columns[0] if len(columns) == 1 else tuple(columns)
            row_norm[key] = delay(columns)
        return row_norm

    @staticmethod
    def strip_callables(row):
        """Extract callable values from `row`.

        Replace the callable values with the initial value (if specified) or
        an empty string.

        Parameters
        ----------
        row : mapping
            A data row.  The keys are either a single column name or a tuple of
            column names.  The values take one of three forms: 1) a
            non-callable value, 2) a tuple (initial_value, callable), 3) or a
            single callable (in which case the initial value is set to an empty
            string).

        Returns
        -------
        list of (column, callable)
        """
        callables = []
        to_delete = []
        to_add = []
        for columns, value in row.items():
            if isinstance(value, tuple):
                initial, fn = value
            else:
                initial = NOTHING
                # Value could be a normal (non-callable) value or a
                # callable with no initial value.
                fn = value

            if callable(fn) or inspect.isgenerator(fn):
                if not isinstance(columns, tuple):
                    columns = columns,
                else:
                    to_delete.append(columns)
                for column in columns:
                    to_add.append((column, initial))
                callables.append((columns, fn))

        for column, value in to_add:
            row[column] = value
        for multi_columns in to_delete:
            del row[multi_columns]

        return callables

    # Input-specific getters.  These exist as their own methods so that they
    # can be wrapped in a callable and delayed.

    def getter_dict(self, row, column):
        return row.get(column, self.nothings[column])

    def getter_seq(self, row, column):
        col_to_idx = {c: idx for idx, c in enumerate(self._columns)}
        return row[col_to_idx[column]]

    def getter_attrs(self, row, column):
        return getattr(row, column, self.nothings[column])


def _safe_get(mapping, key, default=None):
    """Helper for accessing style values.

    It exists to avoid checking whether `mapping` is indeed a mapping before
    trying to get a key.  In the context of style dicts, this eliminates "is
    this a mapping" checks in two common situations: 1) a style argument is
    None, and 2) a style key's value (e.g., width) can be either a mapping or a
    plain value.
    """
    try:
        return mapping.get(key, default)
    except AttributeError:
        return default


class StyleFields(object):
    """Generate Fields based on the specified style and processors.

    Parameters
    ----------
    style : dict
        A style that follows the schema defined in pyout.elements.
    procgen : StyleProcessors instance
        This instance is used to generate the fields from `style`.
    """

    def __init__(self, style, procgen):
        self.init_style = style
        self.procgen = procgen

        self.style = None
        self.columns = None
        self.autowidth_columns = {}

        self.fields = None

    def build(self, columns):
        """Build the style and fields.

        Parameters
        ----------
        columns : list of str
            Column names.
        """
        self.columns = columns
        default = dict(elements.default("default_"),
                       **_safe_get(self.init_style, "default_", {}))
        self.style = elements.adopt({c: default for c in columns},
                                    self.init_style)

        # Store special keys in _style so that they can be validated.
        self.style["default_"] = default
        self.style["header_"] = self._compose("header_", {"align", "width"})
        self.style["summary_"] = self._compose("summary_", {"align", "width"})
        self.style["separator_"] = _safe_get(self.init_style, "separator_",
                                             elements.default("separator_"))
        elements.validate(self.style)
        self._setup_fields()

    def _compose(self, name, attributes):
        """Construct a style taking `attributes` from the column styles.

        Parameters
        ----------
        name : str
            Name of main style (e.g., "header_").
        attributes : set of str
            Adopt these elements from the column styles.

        Returns
        -------
        The composite style for `name`.
        """
        name_style = _safe_get(self.init_style, name, elements.default(name))
        if self.init_style is not None and name_style is not None:
            result = {}
            for col in self.columns:
                cstyle = {k: v for k, v in self.style[col].items()
                          if k in attributes}
                result[col] = dict(cstyle, **name_style)
            return result

    def _setup_fields(self):
        self.fields = {}
        for column in self.columns:
            cstyle = self.style[column]

            core_procs = []
            style_width = cstyle["width"]
            is_auto = style_width == "auto" or _safe_get(style_width, "auto")

            if is_auto:
                width = _safe_get(style_width, "min", 0)
                wmax = _safe_get(style_width, "max")

                self.autowidth_columns[column] = {"max": wmax}

                if wmax is not None:
                    marker = _safe_get(style_width, "marker", True)
                    core_procs = [self.procgen.truncate(wmax, marker)]
            elif is_auto is False:
                raise ValueError("No 'width' specified")
            else:
                width = style_width
                core_procs = [self.procgen.truncate(width)]

            # We are creating a distinction between "core" processors, that we
            # always want to be active and "default" processors that we want to
            # be active unless there's an overriding style (i.e., a header is
            # being written or the `style` argument to __call__ is specified).
            field = Field(width=width, align=cstyle["align"],
                          default_keys=["core", "default"],
                          other_keys=["override"])
            field.add("pre", "default",
                      *(self.procgen.pre_from_style(cstyle)))
            field.add("post", "core", *core_procs)
            field.add("post", "default",
                      *(self.procgen.post_from_style(cstyle)))
            self.fields[column] = field

    @property
    def has_header(self):
        """Whether the style specifies that a header.
        """
        return self.style["header_"] is not None

    def _set_widths(self, row, proc_group):
        """Update auto-width Fields based on `row`.

        Parameters
        ----------
        row : dict
        proc_group : {'default', 'override'}
            Whether to consider 'default' or 'override' key for pre- and
            post-format processors.

        Returns
        -------
        True if any widths required adjustment.
        """
        adjusted = False
        for column in self.columns:
            if column in self.autowidth_columns:
                field = self.fields[column]
                # If we've added any style transform functions as
                # pre-format processors, we want to measure the width
                # of their result rather than the raw value.
                if field.pre[proc_group]:
                    value = field(row[column], keys=[proc_group],
                                  exclude_post=True)
                else:
                    value = row[column]
                value_width = len(six.text_type(value))
                wmax = self.autowidth_columns[column]["max"]
                if value_width > field.width:
                    if wmax is None or field.width < wmax:
                        adjusted = True
                    field.width = value_width
        return adjusted

    def _proc_group(self, style, adopt=True):
        """Return whether group is "default" or "override".

        In the case of "override", the self.fields pre-format and post-format
        processors will be set under the "override" key.

        Parameters
        ----------
        style : dict
            A style that follows the schema defined in pyout.elements.
        adopt : bool, optional
            Merge `self.style` and `style`, giving priority to the latter's
            keys when there are conflicts.  If False, treat `style` as a
            standalone style.
        """
        fields = self.fields
        if style is not None:
            if adopt:
                style = elements.adopt(self.style, style)
            elements.validate(style)

            for column in self.columns:
                fields[column].add(
                    "pre", "override",
                    *(self.procgen.pre_from_style(style[column])))
                fields[column].add(
                    "post", "override",
                    *(self.procgen.post_from_style(style[column])))
            return "override"
        else:
            return "default"

    def render(self, row, style=None, adopt=True):
        """Render fields with values from `row`.

        Parameters
        ----------
        row : dict
            A normalized row.
        style : dict, optional
            A style that follows the schema defined in pyout.elements.  If
            None, `self.style` is used.
        adopt : bool, optional
            Merge `self.style` and `style`, using the latter's keys when there
            are conflicts matching keys.  If False, treat `style` as a
            standalone style.

        Returns
        -------
        A tuple with the rendered value (str) and a flag that indicates whether
        the field widths required adjustment (bool).
        """
        group = self._proc_group(style, adopt=adopt)
        if group == "override":
            # Override the "default" processor key.
            proc_keys = ["core", "override"]
        else:
            # Use the set of processors defined by _setup_fields.
            proc_keys = None

        adjusted = self._set_widths(row, group)
        proc_fields = [self.fields[c](row[c], keys=proc_keys)
                       for c in self.columns]
        return self.style["separator_"].join(proc_fields) + "\n", adjusted


class RedoContent(Exception):
    """The rendered content is stale and should be re-rendered.
    """
    pass


class ContentError(Exception):
    """An error occurred when generating the content representation.
    """
    pass


ContentRow = namedtuple("ContentRow", ["row", "kwds"])


@six.python_2_unicode_compatible
class Content(object):
    """Concatenation of rendered fields.

    Parameters
    ----------
    fields : StyleField instances
    """

    def __init__(self, fields):
        self.fields = fields
        self.summary = None

        self.columns = None
        self.ids = None

        self._header = None
        self._rows = []
        self._idmap = {}

    def init_columns(self, columns, ids):
        """Set up the fields for `columns`.

        Parameters
        ----------
        columns : sequence or OrderedDict
            Names of the column.  In the case of an OrderedDict, a map between
            short and long names.
        ids : sequence
            A collection of column names that uniquely identify a column.
        """
        self.fields.build(columns)
        self.summary = Summary(self.fields.style)
        self.columns = columns
        self.ids = ids

    def __len__(self):
        return len(list(self.rows))

    def __bool__(self):
        return bool(self._rows)

    __nonzero__ = __bool__  # py2

    @property
    def rows(self):
        """Data and summary rows.
        """
        if self._header:
            yield self._header

        if self._rows and self.summary:
            summary_rows = self.summary.summarize([r.row for r in self._rows])
        else:
            summary_rows = []

        for i in chain(self._rows, summary_rows):
            yield i

    def __iter__(self):
        adjusted = []
        for row, kwds in self.rows:
            line, adj = self.fields.render(row, **kwds)
            yield line
            # Continue processing so that we get all the adjustments out of
            # the way.
            adjusted.append(adj)
        if any(adjusted):
            raise RedoContent

    def __str__(self):
        try:
            return "".join(self)
        except RedoContent:
            return "".join(self)

    def update(self, row, style):
        """Modify the content.

        Parameters
        ----------
        row : dict
            A normalized row.  If the names specified by `self.ids` have
            already been seen in a previous call, the entry for the previous
            row is updated.  Otherwise, a new entry is appended.

        `style` is passed to `StyleFields.render`.

        Returns
        -------
        A tuple of (content, status), where status is either 'append', an
        integer, or 'repaint'.

          * append: the only change in the content is the addition of a line,
            and the returned content will consist of just this line.

          * an integer, N: the Nth line of the output needs to be update, and
            the returned content will consist of just this line.

          * repaint: all lines need to be updated, and the returned content
            will consist of all the lines.
        """
        called_before = bool(self)
        idkey = tuple(row[idx] for idx in self.ids)

        if not called_before and self.fields.has_header:
            self._add_header()
            self._rows.append(ContentRow(row, kwds={"style": style}))
            self._idmap[idkey] = 0
            return six.text_type(self), "append"

        try:
            prev_idx = self._idmap[idkey] if idkey in self._idmap else None
        except TypeError:
            raise ContentError("ID columns must be hashable")

        if prev_idx is not None:
            row_update = {k: v for k, v in row.items()
                          if not isinstance(v, Nothing)}
            self._rows[prev_idx].row.update(row_update)
            self._rows[prev_idx].kwds.update({"style": style})
            # Replace the passed-in row since it may not have the all columns.
            row = self._rows[prev_idx][0]
        else:
            self._idmap[idkey] = len(self._rows)
            self._rows.append(ContentRow(row, kwds={"style": style}))

        line, adjusted = self.fields.render(row, style)
        if called_before and adjusted or self.summary:
            # For now, we're just overwriting everything if there is a summary,
            # which does unnecessary work when adjusted is False.  We could
            # change this function into a generator function that yields
            # multiple lines and "append"/idx.
            return six.text_type(self), "repaint"
        if not adjusted and prev_idx is not None:
            return line, prev_idx
        return line, "append"

    def _add_header(self):
        if isinstance(self.columns, OrderedDict):
            row = self.columns
        else:
            row = dict(zip(self.columns, self.columns))
        self._header = ContentRow(row,
                                  kwds={"style": self.fields.style["header_"],
                                        "adopt": False})
