#!/usr/bin/env python
import os
import sys
import json
from pyout import Tabular
from collections import OrderedDict

# there is nothing here specific about json really besides how we load
# the structured data, so could be autodetected in some cases but option
# -f --format could be used to define how to parse input (tsv, csv, ssv
# (space separated values ;-)) json, jsonstream, yaml, ...)
if __name__ == '__main__':
    # TODO: cmldline args etc for above
    idfield = "key"  # TODO: how do we specify
    flatten = True   # flatten nested dicts
    format = None    # input format, if not specified -- deduced
    out = Tabular(style=dict(
        header_=dict(bold=True, transform=lambda x: x.upper()),
        # Default styling could be provided from some collection of styling files
        default_=dict(
            width=dict(
                auto=True,
                max=20  # TODO: ideally just a proportion of the available width estate as discussed
            ),
            color=dict(
                # needs catchall as discussed?
                lookup={
                    # Some common indicators
                    ('yes', 'True', 'true', True, 'success', 'Success', 'SUCCESS', 'ok'): 'green',
                    ('no', 'False', 'false', False, 'error', 'Error', 'ERROR', 'fail'): 'red',
                    ('none', 'n/a', 'NA', 'N/A', None): 'cyan', # TODO: wants grey
                    # Since above doesn't work any longer -- listing my main ones now
                    'yes': 'green',
                    'no':  'red',
                    'none': 'black',  # since no grey for now
                })
        ),
        )
    )

    # For tsv/csv/ssv (space value sep)
    delims = {'\t': 't', ' ': 's', ',': 'c'}
    delims_inverse = {v: k for k, v in delims.items()}

    first = True
    for line in sys.stdin:
        line = line.rstrip(os.linesep)
        if format is None:
            # we need to figure it out
            if line.lstrip().startswith('{'):
                format = 'json'
            else:
                # could use csv guessing later, for now just choose the delim which gives
                # most fields
                lens = [(len(line.split(delim)), delim) for delim in delims]
                maxlen, delim = max(lens)
                print("Will use delimiter %r" % delim)
                format = delims[delim] + 'sv'

        if format == 'json':
            parser = json.loads
        elif format in ['tsv', 'csv', 'ssv']:
            delim = delims_inverse[format[0]]
            parser = lambda x: x.split(delim)

        line_parsed = parser(line)
        #line_parsed['_line_parsed_'] = json.dumps(line_parsed)
        if isinstance(line_parsed, dict):
            adjusted = line_parsed.__class__()
            for k, v in line_parsed.items():
                # RF: to make it recursive
                if flatten and isinstance(v, dict):
                    for k_, v_ in v.items():
                        adjusted[k_] = v_
                    else:
                        adjusted[k] = v
        else:
            adjusted = line_parsed

        if first:
            first = False
            if isinstance(adjusted, list):
                # let's use it as a header
                header = adjusted
                continue
            # doesn't work ATM anyways, disabled
            #if idfield in adjusted:
            #    out.ids = [idfield]
        else:
            if isinstance(adjusted, list):
                # assuming tabular format
                adjusted = OrderedDict(zip(header, adjusted))

        #print adjusted
        out(adjusted)
