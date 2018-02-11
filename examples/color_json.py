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
    flatten = True   # flatten nested dicts
    out = Tabular(style=dict(
        header_=dict(bold=True, transform=lambda x: x.upper()),
        # Default styling could be provided from some collection of styling files
        default_=dict(
            width=dict(
                auto=True,
                max=20
            ),
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
        #line_json['_line_json_'] = json.dumps(line_json)
        adjusted = {}
        for k, v in line_json.items():
            # RF: to make it recursive
            if flatten and isinstance(v, dict):
                for k_, v_ in v.items():
                    adjusted[k_] = v_
            else:
                adjusted[k] = v

        if first:
            first = False
            if idfield in adjusted:
                out.ids = [idfield]
        #print adjusted
        out(adjusted)