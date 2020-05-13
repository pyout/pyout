#!/usr/bin/env python

from pyout import Tabular
import pyout

import argparse
import csv
import os
import sys


def get_parser():
    parser = argparse.ArgumentParser(description="Pyout Simple Example")

    parser.add_argument(
        "--version",
        dest="version",
        help="show version of pyout",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--no-header",
        dest="no_header",
        help="data does not have a header",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "input_file",
        help="csv file to read into table",
        type=str,
        default="cereal.csv",
        nargs="?",
    )

    parser.add_argument(
        "--delim",
        dest="delim",
        help="delimiter to split tabular file (defaults to comma)",
        default=",",
    )
    return parser


def main():
    """main entrypoint for pyout simple example
    """

    parser = get_parser()

    def help(return_code=0):
        """print help, including the software version and active client
           and exit with return code.
        """

        print("\npyout v%s" % pyout.__version__)
        parser.print_help()
        sys.exit(return_code)

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # Show the version and exit
    if args.version:
        print(pyout.__version__)
        sys.exit(0)

    # Generate and print a table to the terminal
    generate_table(
        delim=args.delim, input_file=args.input_file, header=not args.no_header
    )


def read_rows(filepath, newline="", delim=","):
    """read in the data rows of a csv file.
    """
    # Read in the entire membership counts
    with open(filepath, newline=newline) as infile:
        reader = csv.reader(infile, delimiter=delim)
        data = [row for row in reader]
    return data


def generate_table(input_file, delim=",", header=True):
    """Given an input file and a delimiter, read it in and generate
       a pyout Tabular table to print to the console.

       Arguments:
        - input_file (str) : path to an input file (must exist)
        - delim (str) : single delimiter to split file by
    """
    input_file = os.path.abspath(input_file)
    if not os.path.exists(input_file):
        sys.exit("%s does not exist." % input_file)

    # Read in rows with user specified delimiter
    rows = read_rows(input_file, delim=delim)

    # Generate tabulars expected format
    labels = ["column %s" % x for x in range(len(rows[0]))]
    if header:
        labels = rows.pop(0)

    # Generate Tabular table to output
    table = Tabular(
        # Note that columns are specified here, so we provide a row (list) later
        columns=labels,
        style=dict(
            header_=dict(bold=True, transform=str.upper),
            # Default styling could be provided from some collection of styling files
            default_=dict(
                color=dict(
                    lookup={
                        "Trix": "green",
                        "110": "red",
                        "100": "green",  # since no grey for now
                    }
                )
            ),
        ),
    )

    # Add row to table. If columns aren't specified on init, provide dict here
    for row in rows:
        table(row)


if __name__ == "__main__":
    main()
