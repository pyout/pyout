"""Define a "field" based on a sequence of processor functions.
"""
from itertools import chain


class Field(object):
    """Render values based on a list of processors.

    A Field instance is a template for a string that is defined by its
    width, text alignment, and its "processors".

    When a field is called with a value, the value is rendered in
    three steps.

                       pre -> format -> post

    During the first step, the value is fed through the list of
    pre-format processor functions.  The result of this value is then
    formatted as a string with the specified width and alignment.
    Finally, this result is fed through the list of the post-format
    processors.  The rendered string is the result returned by the
    last processor

    Parameters
    ----------
    width : int
    align : {'left', 'right', 'center'}

    Attributes
    ----------
    width : int
    align : str
    pre, post : dict
        Each key maps to a list of processors.
    pre_keys, post_keys : list
        These lists define which processor lists are called by default
        and in what order.  The values can be overridden by the
        providing `pre_keys` and `post_keys` arguments when calling
        the instance.
    """

    _align_values = {"left": "<", "right": ">", "center": "^"}

    def __init__(self, width=10, align="left"):
        self._width = width
        self._align = align
        self._fmt = self._build_format()

        self.pre = {}
        self.pre_keys = []
        self.post = {}
        self.post_keys = []

    def add(self, kind, key, *values):
        """Add processor functions.

        This method both adds the processor function and registers the
        key.  As a result, any processor added through this method
        will be enabled when the instance is called without the
        `pre_keys` (if kind is "pre") or `post_keys` argument (if kind
        is "post").  To set up non-default keys, modify the `pre` or
        `post` attributes directly.

        Parameters
        ----------
        kind : {"pre", "post"}
        key : str
            Put the functions under this key in the pre or post
            processor collection.
        *values : callables
            Processors to add.
        """
        if kind == "pre":
            procs, keys = self.pre, self.pre_keys
        elif kind == "post":
            procs, keys = self.post, self.post_keys
        else:
            raise ValueError("kind is not 'pre' or 'post'")

        if key not in keys:
            keys.append(key)
        if key not in procs:
            procs[key] = []
        procs[key].extend(values)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        self._fmt = self._build_format()

    def _build_format(self):
        align = self._align_values[self._align]
        return "".join(["{:", align, str(self.width), "}"])

    def _format(self, _, result):
        """Wrap format call as a two-argument processor function.
        """
        return self._fmt.format(result)

    def __call__(self, value, pre_keys=None, post_keys=None):
        """Render `value` by feeding it through the processors.

        Parameters
        ----------
        value : str
        pre_keys, post_keys : sequence, optional
            These lists define which processor lists are called and in
            what order.  If not specified, the keys defined by the
            corresponding attribute (`pre_keys` or `post_keys`) will
            be used.
        """
        if pre_keys is None:
            pre_keys = self.pre_keys
        if post_keys is None:
            post_keys = self.post_keys

        pre_funcs = chain(*(self.pre[k] for k in pre_keys))
        post_funcs = chain(*(self.post[k] for k in post_keys))

        funcs = chain(pre_funcs, [self._format], post_funcs)
        result = value
        for fn in funcs:
            result = fn(value, result)
        return result


class StyleFunctionError(Exception):
    """Signal that a style function failed.
    """
    def __init__(self, function):
        msg = ("Style transform {} raised an exception. "
               "See above.".format(function))
        super(StyleFunctionError, self).__init__(msg)


class StyleProcessors(object):
    """A base class for generating Field.processors for styled output.

    Attributes
    ----------
    style_keys : list of tuples
        Each pair consists of a style attribute (e.g., "bold") and the
        expected type.
    """

    style_keys = [("bold", bool),
                  ("underline", bool),
                  ("color", str)]

    def translate(self, name):
        """Translate a style key for a given output type.

        Parameters
        ----------
        name : str
            A style key (e.g., "bold").

        Returns
        -------
        An output-specific translation of `name`.
        """
        raise NotImplementedError

    @staticmethod
    def truncate(length, marker=True):
        """Return a processor that truncates the result to `length`.

        Note: You probably want to place this function at the
        beginning of the processor list so that the truncation is
        based on the length of the original value.

        Parameters
        ----------
        length : int
        marker : str or bool
            Indicate truncation with this string.  If True, indicate
            truncation by replacing the last three characters of a
            truncated string with '...'.  If False, no truncation
            marker is added to a truncated string.

        Returns
        -------
        A function.
        """
        if marker is True:
            marker = "..."

        # TODO: Add an option to center the truncation marker?
        def truncate_fn(_, result):
            if len(result) <= length:
                return result
            if marker:
                marker_beg = max(length - len(marker), 0)
                if result[marker_beg:].strip():
                    if marker_beg == 0:
                        return marker[:length]
                    return result[:marker_beg] + marker
            return result[:length]
        return truncate_fn

    @staticmethod
    def transform(function):
        """Return a processor for a style's "transform" function.
        """
        def transform_fn(_, result):
            try:
                return function(result)
            except:
                raise StyleFunctionError(function)
        return transform_fn

    def by_key(self, key):
        """Return a processor for the style given by `key`.

        Parameters
        ----------
        key : str
            A style key to be translated.

        Returns
        -------
        A function.
        """
        def by_key_fn(_, result):
            return self.translate(key) + result
        return by_key_fn

    def by_lookup(self, mapping, key=None):
        """Return a processor that extracts the style from `mapping`.

        Parameters
        ----------
        mapping : mapping
            A map from the field value to a style key, or, if `key` is
            given, a map from the field value to a value that
            indicates whether the processor should style its result.
        key : str, optional
            A style key to be translated.  If not given, the value
            from `mapping` is used.

        Returns
        -------
        A function.
        """
        def by_lookup_fn(value, result):
            try:
                lookup_value = mapping[value]
            except KeyError:
                return result

            if not lookup_value:
                return result
            return self.translate(key or lookup_value) + result
        return by_lookup_fn

    def by_interval_lookup(self, intervals, key=None):
        """Return a processor that extracts the style from `intervals`.

        Parameters
        ----------
        intervals : sequence of tuples
            Each tuple should have the form `(start, end, key)`, where
            start is the start of the interval (inclusive) , end is
            the end of the interval, and key is a style key.
        key : str, optional
            A style key to be translated.  If not given, the value
            from `mapping` is used.

        Returns
        -------
        A function.
        """
        def by_interval_lookup_fn(value, result):
            value = float(value)
            for start, end, lookup_value in intervals:
                if start is None:
                    start = float("-inf")
                elif end is None:
                    end = float("inf")

                if start <= value < end:
                    if not lookup_value:
                        return result
                    return self.translate(key or lookup_value) + result
            return result
        return by_interval_lookup_fn

    @staticmethod
    def value_type(value):
        """Classify `value` of bold, color, and underline keys.

        Parameters
        ----------
        value : style value

        Returns
        -------
        str, {"simple", "label", "interval"}
        """
        try:
            keys = list(value.keys())
        except AttributeError:
            return "simple"
        if keys in [["label"], ["interval"]]:
            return keys[0]
        raise ValueError("Type of `value` could not be determined")

    def pre_from_style(self, column_style):
        """Yield pre-format processors based on `column_style`.

        Parameters
        ----------
        column_style : dict
            A style where the top-level keys correspond to style
            attributes such as "bold" or "color".

        Returns
        -------
        A generator object.
        """
        if "transform" in column_style:
            yield self.transform(column_style["transform"])

    def post_from_style(self, column_style):
        """Yield post-format processors based on `column_style`.

        Parameters
        ----------
        column_style : dict
            A style where the top-level keys correspond to style
            attributes such as "bold" or "color".

        Returns
        -------
        A generator object.
        """
        for key, key_type in self.style_keys:
            if key not in column_style:
                continue

            vtype = self.value_type(column_style[key])
            attr_key = key if key_type is bool else None

            if vtype == "simple":
                if key_type is bool:
                    if column_style[key] is True:
                        yield self.by_key(key)
                elif key_type is str:
                    yield self.by_key(column_style[key])
            elif vtype == "label":
                yield self.by_lookup(column_style[key][vtype], attr_key)
            elif vtype == "interval":
                yield self.by_interval_lookup(column_style[key][vtype],
                                              attr_key)
