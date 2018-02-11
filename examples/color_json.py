#!/usr/bin/env python
import sys
import json
from pyout import Tabular
# there is nothing here specific about json really besides how we load
# the structured data, so could be autodetected in some cases but option
# -f --format could be used to define how to parse input (tsv, csv, ssv
# (space separated values ;-)) json, jsonstream, yaml, ...)
if __name__ == '__main__':
    # TODO: cmldline args etc for above
    idfield = "key"  # TODO: how do we specify
    out = Tabular(style=dict(
        header_=dict(bold=True, transform=lambda x: x.upper()),
        # Default styling could be provided from some collection of styling files
        default_=dict(
            color=dict(
                # needs catchall as discussed?
                label={
                    # Some common indicators
                    ('True', 'true', True, 'success', 'Success', 'SUCCESS', 'ok'): 'green',
                    ('False', 'false', False, 'error', 'Error', 'ERROR', 'fail', None): 'red',
                })
        ),
        )
    )
    first = True
    for line in sys.stdin:
        line_json = json.loads(line)
        line_json['_line_json_'] = json.dumps(line_json)
        if first:
            first = False
            if idfield in line_json:
                out.ids = [idfield]
        out(line_json)