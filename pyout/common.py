"""Common components for styled output.

This modules contains things that would be shared across outputters if there
were any besides Tabular.  The Tabular class, though, still contains a good
amount of general logic that should be extracted if any other outputter is
actually added.
"""

from __future__ import unicode_literals

from collections import defaultdict
from collections import Mapping
from collections import namedtuple
from collections import OrderedDict
from collections import Sequence
from functools import partial
import inspect
from logging import getLogger

import six

from pyout import elements
from pyout.field import Field
from pyout.field import Nothing
from pyout.truncate import Truncater
from pyout.summary import Summary

lgr = getLogger(__name__)
NOTHING = Nothing()


class RowNormalizer(object):
    """Transform various input data forms to a common form.

    An un-normalized can be one of three kinds:

      * a mapping from column names to keys

      * a sequence of values in the same order as `columns`

      * any other value will be taken as an object where the column values can
        be accessed via an attribute with the same name

    To normalize a row, it is

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
    method : callable
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
                lgr.debug("Registered delay for column %r", column)
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
        lgr.debug("Selecting %s as normalizer", getter.__name__)
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

        for cols in self.delayed.values():
            key = cols[0] if len(cols) == 1 else tuple(cols)
            lgr.debug("Delaying %r for row %r", cols, row)
            row_norm[key] = delay(cols)
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
                lgr.debug("Using %r as the initial value "
                          "for columns %r in row %r",
                          initial, columns, row)
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

        self.width_separtor = None
        self.fields = None
        self._truncaters = {}

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
        self.style["aggregate_"] = self._compose("aggregate_",
                                                 {"align", "width"})
        self.style["separator_"] = _safe_get(self.init_style, "separator_",
                                             elements.default("separator_"))
        lgr.debug("Validating style %r", self.style)
        self.style["width_"] = _safe_get(self.init_style, "width_",
                                         elements.default("width_"))
        elements.validate(self.style)
        self._setup_fields()

        ngaps = len(self.columns) - 1
        self.width_separtor = len(self.style["separator_"]) * ngaps
        lgr.debug("Calculated separator width as %d", self.width_separtor)

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
            lgr.debug("Setting up field for column %r", column)
            cstyle = self.style[column]
            style_width = cstyle["width"]

            # Convert atomic values into the equivalent complex form.
            if style_width == "auto":
                style_width = {}
            elif isinstance(style_width, int):
                style_width = {"width": style_width}

            is_auto = "width" not in style_width
            if is_auto:
                lgr.debug("Automatically adjusting width for %s", column)
                width = _safe_get(style_width, "min", 0)
                wmax = _safe_get(style_width, "max")
                self.autowidth_columns[column] = {"max": wmax}
                if wmax is not None:
                    lgr.debug("Setting max width of column %r to %d",
                              column, wmax)
            else:
                if "min" in style_width or "max" in style_width:
                    raise ValueError(
                        "'min' and 'max' are incompatible with 'width'")
                width = style_width["width"]
                lgr.debug("Setting width of column %r to %d",
                          column, width)

            # We are creating a distinction between "width" processors, that we
            # always want to be active and "default" processors that we want to
            # be active unless there's an overriding style (i.e., a header is
            # being written or the `style` argument to __call__ is specified).
            field = Field(width=width, align=cstyle["align"],
                          default_keys=["width", "default"],
                          other_keys=["override"])
            field.add("pre", "default",
                      *(self.procgen.pre_from_style(cstyle)))
            truncater = Truncater(
                width,
                _safe_get(style_width, "marker", True),
                _safe_get(style_width, "truncate", "right"))
            field.add("post", "width", truncater.truncate)
            field.add("post", "default",
                      *(self.procgen.post_from_style(cstyle)))
            self.fields[column] = field
            self._truncaters[column] = truncater

    @property
    def has_header(self):
        """Whether the style specifies a header.
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
        width_free = self.style["width_"] - sum(
            [sum(self.fields[c].width for c in self.columns),
             self.width_separtor])

        if width_free < 0:
            width_fixed = sum(
                [sum(self.fields[c].width for c in self.columns
                     if c not in self.autowidth_columns),
                 self.width_separtor])
            assert width_fixed > self.style["width_"], "bug in width logic"
            raise elements.StyleError(
                "Fixed widths specified in style exceed total width")
        elif width_free == 0:
            lgr.debug("Not checking widths; no free width left")
            return False

        lgr.debug("Checking width for row %r", row)
        adjusted = False
        for column in sorted(self.columns, key=lambda c: self.fields[c].width):
            # ^ Sorting the columns by increasing widths isn't necessary; we do
            # it so that columns that already take up more of the screen don't
            # continue to grow and use up free width before smaller columns
            # have a chance to claim some.
            if width_free < 1:
                lgr.debug("Giving up on checking widths; no free width left")
                break

            if column in self.autowidth_columns:
                field = self.fields[column]
                lgr.debug("Checking width of column %r "
                          "(field width: %d, free width: %d)",
                          column, field.width, width_free)
                # If we've added any style transform functions as
                # pre-format processors, we want to measure the width
                # of their result rather than the raw value.
                if field.pre[proc_group]:
                    value = field(row[column], keys=[proc_group],
                                  exclude_post=True)
                else:
                    value = row[column]
                value = six.text_type(value)
                value_width = len(value)
                wmax = self.autowidth_columns[column]["max"]
                if value_width > field.width:
                    width_old = field.width
                    width_available = width_free + field.width
                    width_new = min(value_width,
                                    wmax or width_available,
                                    width_available)
                    if width_new > width_old:
                        adjusted = True
                        field.width = width_new
                        lgr.debug("Adjusting width of %r column from %d to %d "
                                  "to accommodate value %r",
                                  column, width_old, field.width, value)
                        self._truncaters[column].length = field.width
                        width_free -= field.width - width_old
                        lgr.debug("Free width is %d after processing column %r",
                                  width_free, column)
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
            Merge `self.style` and `style`, using the latter's keys
            when there are conflicts.  If False, treat `style` as a
            standalone style.

        Returns
        -------
        A tuple with the rendered value (str) and a flag that indicates whether
        the field widths required adjustment (bool).
        """
        group = self._proc_group(style, adopt=adopt)
        if group == "override":
            # Override the "default" processor key.
            proc_keys = ["width", "override"]
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
    fields : StyleField instance
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
        self.columns = columns
        self.ids = ids

    def __len__(self):
        return len(list(self.rows))

    def __bool__(self):
        return bool(self._rows)

    __nonzero__ = __bool__  # py2

    def __getitem__(self, key):
        idx = self._idmap[key]
        return self._rows[idx].row

    @property
    def rows(self):
        """Data and summary rows.
        """
        if self._header:
            yield self._header
        for i in self._rows:
            yield i

    def _render(self, rows):
        adjusted = []
        for row, kwds in rows:
            line, adj = self.fields.render(row, **kwds)
            yield line
            # Continue processing so that we get all the adjustments out of
            # the way.
            adjusted.append(adj)
        if any(adjusted):
            raise RedoContent

    def __str__(self):
        try:
            return "".join(self._render(self.rows))
        except RedoContent:
            return "".join(self._render(self.rows))

    def update(self, row, style):
        """Modify the content.

        Parameters
        ----------
        row : dict
            A normalized row.  If the names specified by `self.ids` have
            already been seen in a previous call, the entry for the previous
            row is updated.  Otherwise, a new entry is appended.

        style :
            Passed to `StyleFields.render`.

        Returns
        -------
        A tuple of (content, status), where status is 'append', an integer, or
        'repaint'.

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
            lgr.debug("Registering header")
            self._add_header()
            self._rows.append(ContentRow(row, kwds={"style": style}))
            self._idmap[idkey] = 0
            return six.text_type(self), "append"

        try:
            prev_idx = self._idmap[idkey] if idkey in self._idmap else None
        except TypeError:
            raise ContentError("ID columns must be hashable")

        if prev_idx is not None:
            lgr.debug("Updating content for row %r", idkey)
            row_update = {k: v for k, v in row.items()
                          if not isinstance(v, Nothing)}
            self._rows[prev_idx].row.update(row_update)
            self._rows[prev_idx].kwds.update({"style": style})
            # Replace the passed-in row since it may not have all the columns.
            row = self._rows[prev_idx][0]
        else:
            lgr.debug("Adding row %r to content for first time", idkey)
            self._idmap[idkey] = len(self._rows)
            self._rows.append(ContentRow(row, kwds={"style": style}))

        line, adjusted = self.fields.render(row, style)
        if called_before and adjusted:
            return six.text_type(self), "repaint"
        if not adjusted and prev_idx is not None:
            return line, prev_idx + self.fields.has_header
        return line, "append"

    def _add_header(self):
        if isinstance(self.columns, OrderedDict):
            row = self.columns
        else:
            row = dict(zip(self.columns, self.columns))
        self._header = ContentRow(row,
                                  kwds={"style": self.fields.style["header_"],
                                        "adopt": False})


class ContentWithSummary(Content):
    """Like Content, but append a summary to the return value of `update`.
    """

    def __init__(self, fields):
        super(ContentWithSummary, self).__init__(fields)
        self.summary = None

    def init_columns(self, columns, ids):
        super(ContentWithSummary, self).init_columns(columns, ids)
        self.summary = Summary(self.fields.style)

    def update(self, row, style):
        content, status = super(ContentWithSummary, self).update(row, style)
        if self.summary:
            summ_rows = self.summary.summarize([r.row for r in self._rows])

            def join():
                return "".join(self._render(summ_rows))

            try:
                summ_content = join()
            except RedoContent:
                # If rendering the summary lines triggered an adjustment, we
                # need to re-render the main content as well.
                return six.text_type(self), "repaint", join()
            return content, status, summ_content
        return content, status, None
