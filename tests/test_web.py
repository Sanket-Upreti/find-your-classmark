""" 
    drives the web page in-process, so it is checked without opening a browser

    run it with: python3 tests/test_web.py
"""
import os
import sys
import threading
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import config
from web import app

CHECKS = []

def check(name):
    def keep(function):
        CHECKS.append((name, function))
        return function
    return keep

# starting a real server on a spare port, then stopping it again
class Serving:
    def __init__(self, dataset):
        self.server = app.make_server(dataset, port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *details):
        self.server.shutdown()
        self.server.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.status, response.read().decode("utf-8")

    def status_of(self, path):
        try:
            return self.get(path)[0]
        except urllib.error.HTTPError as error:
            return error.code

CLASSMARKS = config.load_default()
SURVEY = config.load_config(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         "datasets", "survey.yaml"))

@check("the home page lists every search")
def _():
    with Serving(CLASSMARKS) as serving:
        status, markup = serving.get("/")
        assert status == 200
        for search in CLASSMARKS.searches:
            assert search.label in markup, search.label

@check("a search offering choices renders a dropdown, not a text box")
def _():
    with Serving(CLASSMARKS) as serving:
        markup = serving.get("/")[1]
        assert "<select" in markup
        assert "Top floor bottom left" in markup

@check("a subject search answers with the app's own wording")
def _():
    with Serving(CLASSMARKS) as serving:
        markup = serving.get("/search?i=0&q=Art")[1]
        assert "Subject Art happens on class N which is located in Top floor top left" in markup

@check("a search with several answers lists them all")
def _():
    with Serving(CLASSMARKS) as serving:
        markup = serving.get("/search?i=0&q=American%20History")[1]
        assert "class E" in markup and "class F" in markup

@check("the rows behind an answer are shown as a table")
def _():
    with Serving(CLASSMARKS) as serving:
        markup = serving.get("/search?i=1&q=JX")[1]
        assert "<table>" in markup
        assert "Top floor top left" in markup and "Bottom floor" in markup

@check("a location search is answered by the number of the choice")
def _():
    with Serving(CLASSMARKS) as serving:
        markup = serving.get("/search?i=2&q=2")[1]
        assert "Top floor top left" in markup

@check("an unknown search term is reported, not crashed on")
def _():
    with Serving(CLASSMARKS) as serving:
        status, markup = serving.get("/search?i=0&q=zzz")
        assert status == 200
        assert "no class or location was found" in markup

@check("summaries are counted and drawn")
def _():
    with Serving(SURVEY) as serving:
        markup = serving.get("/summary?i=0")[1]
        assert "Would you recommend this module?" in markup
        assert "Yes" in markup and "62%" in markup

@check("a dataset with no summaries doesn't offer any")
def _():
    with Serving(CLASSMARKS) as serving:
        assert "Summaries" not in serving.get("/")[1]

@check("out of range and unknown paths give a 404, not a traceback")
def _():
    with Serving(CLASSMARKS) as serving:
        assert serving.status_of("/search?i=99&q=x") == 404
        assert serving.status_of("/summary?i=99") == 404
        assert serving.status_of("/nope") == 404

@check("a search term containing html is escaped")
def _():
    with Serving(CLASSMARKS) as serving:
        markup = serving.get("/search?i=0&q=%3Cscript%3Ealert(1)%3C/script%3E")[1]
        assert "<script>alert(1)</script>" not in markup
        assert "&lt;script&gt;" in markup

if __name__ == '__main__':
    import urllib.error
    failures = 0
    for name, function in CHECKS:
        try:
            function()
            print(f"  ok   {name}")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error or 'assertion failed'}")
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    raise SystemExit(1 if failures else 0)
