#!/usr/bin/env python3
"""Eval stand-in for the workbench's providers/resolve.py: prints the path of this fixture's stand-in provider.

Usage: python3 resolve.py --class <class>      (generator:image)
Exit 0 with the path on stdout, 2 on a usage error, 3 when this workbench has no provider for the class.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAND_INS = {"generator:image": "generator/stand_in.py"}

args = sys.argv[1:]
if "--class" not in args or args.index("--class") + 1 >= len(args):
    print("usage: resolve.py --class <class>", file=sys.stderr)
    sys.exit(2)
cls = args[args.index("--class") + 1]
rel = STAND_INS.get(cls)
if rel is None:
    print(f"error: no provider for class {cls!r} in this workbench; set the class's provider variable",
          file=sys.stderr)
    sys.exit(3)
print(HERE / rel)
