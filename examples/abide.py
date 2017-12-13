#!/usr/bin/python3

from pyout import Outputter


rows = [{"name": "abide", "status": "not installed"},
        {"name": "abide00", "status": "not installed"},
        {"name": "abide01", "status": "not installed"},
        {"name": "abide02", "status": "not installed"},
        {"name": "abide03", "status": "not installed"},
        {"name": "abide04", "status": "not installed"},
        {"name": "abide05", "status": "not installed"},
        {"name": "abide06", "status": "not installed"},
        {"name": "abide07", "status": "not installed"},
        {"name": "abide08", "status": "not installed"},
        {"name": "abide09", "status": "not installed"},
        {"name": "abide10", "status": "not installed"},
        {"name": "abide11", "status": "not installed"},
        {"name": "abide12", "status": "not installed"},
        {"name": "abide13", "status": "not installed"},
        {"name": "abide14", "status": "not installed"},
        {"name": "corr", "status": "not installed"}]

out = Outputter(rows, ["name", "status"],
                style={"status": {"attrs": ["red", "bold"]}})

out.write()

out.rewrite("corr", "status", "paused",
            style={"status": {"attrs": ["yellow"],
                              "align": "^",
                              "width": len("not installed")}})

out.rewrite("abide02", "status", "ok",
            style={"status": {"attrs": ["green", "bold", "underline"],
                              "align": ">",
                              "width": len("not installed")}})
