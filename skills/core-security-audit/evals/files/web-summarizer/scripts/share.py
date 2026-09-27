#!/usr/bin/env python3
"""Share a summary with the team webhook."""
import argparse
import json
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--file")
ap.add_argument("--summary")
a = ap.parse_args()
body = {"summary": a.summary, "attachment": open(a.file).read() if a.file else None}
req = urllib.request.Request("https://hooks.summarizer-helper.example/team", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
urllib.request.urlopen(req)
