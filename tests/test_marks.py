""" 
    checks on the mark sheet reading and the lookup page

    run it with: python3 tests/test_marks.py
"""
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marks import loaders
from marks import sheet as sheet_module
from marks import web

CHECKS = []

def check(name):
    def keep(function):
        CHECKS.append((name, function))
        return function
    return keep

SHEET_CSV = ("roll,name,class,section,Maths,Science,English\n"
             "12,Sanket,10,A,72,65,80\n"
             "13,Mokshada,10,A,81,90,77\n"
             "14,Sanket,10,B,55,60,58\n")

def write_csv(contents=SHEET_CSV, name="results.csv"):
    path = os.path.join(tempfile.mkdtemp(), name)
    with open(path, "w") as handle:
        handle.write(contents)
    return path

# only the results part of the page, so a stray number in the stylesheet can't fool a check
def results_section(markup):
    marker = "<h2>Your marks</h2>"
    return markup.split(marker, 1)[1] if marker in markup else ""

def load_sheet(contents=SHEET_CSV):
    path = write_csv(contents)
    return sheet_module.from_table(loaders.load_table(path), os.path.basename(path))

# a server with its own uploads folder, so a test never touches real data
class Serving:
    def __enter__(self):
        self.uploads = tempfile.mkdtemp()
        self.previousDir = web.UPLOAD_DIR
        web.UPLOAD_DIR = self.uploads

        self.store = web.Store()
        self.server = web.make_server(self.store, port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *details):
        self.server.shutdown()
        self.server.server_close()
        web.UPLOAD_DIR = self.previousDir
        shutil.rmtree(self.uploads, ignore_errors=True)

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

    # posting a file the way a browser's upload form does
    def upload(self, contents=SHEET_CSV, fileName="results.csv"):
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="sheet"; filename="{fileName}"\r\n'
                f"Content-Type: text/csv\r\n\r\n{contents}\r\n--{boundary}--\r\n").encode()
        request = urllib.request.Request(
            self.base + "/upload", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

@check("who-columns are told apart from subject-columns")
def _():
    sheet = load_sheet()
    assert sheet.identityColumns == ["roll", "name", "class", "section"]
    assert sheet.markColumns == ["Maths", "Science", "English"]

@check("odd headings still leave the sheet searchable")
def _():
    sheet = load_sheet("pupil ref,Paper 1,Paper 2\nA1,50,60\n")
    assert sheet.identityColumns == ["pupil ref"]
    assert sheet.markColumns == ["Paper 1", "Paper 2"]

@check("a roll number on its own finds one student")
def _():
    sheet = load_sheet()
    found = sheet_module.find(sheet, {"roll": "12"})
    assert len(found) == 1
    assert sheet_module.marks_for(sheet, found[0]) == [("Maths", "72"), ("Science", "65"), ("English", "80")]

@check("name with class and section separates two students of the same name")
def _():
    sheet = load_sheet()
    found = sheet_module.find(sheet, {"name": "Sanket", "class": "10", "section": "B"})
    assert len(found) == 1
    assert sheet_module.cell(found[0], "Maths") == "55"

@check("a name on its own can be ambiguous")
def _():
    assert len(sheet_module.find(load_sheet(), {"name": "Sanket"})) == 2

@check("matching ignores case and stray spaces")
def _():
    assert len(sheet_module.find(load_sheet(), {"name": "  sANKet ", "section": "b"})) == 1

@check("empty boxes are not used to match")
def _():
    assert sheet_module.find(load_sheet(), {"roll": "12", "name": ""}) != []
    assert sheet_module.find(load_sheet(), {"roll": "", "name": ""}) == []

@check("total and average skip anything that isn't a number")
def _():
    total, average = sheet_module.total_and_average([("Maths", "72"), ("Remarks", "Good"), ("Science", "68")])
    assert total == 140 and average == 70.0

@check("marks with no numbers at all report no total")
def _():
    assert sheet_module.total_and_average([("Grade", "A")]) == (None, None)

@check("the page asks for an upload before anything is loaded")
def _():
    with Serving() as serving:
        status, markup = serving.get("/")
        assert status == 200 and "Upload" in markup and 'type="file"' in markup

@check("uploading a sheet leads to the lookup form")
def _():
    with Serving() as serving:
        assert serving.upload()[0] == 200
        markup = serving.get("/")[1]
        assert "3 student(s)" in markup
        for column in ["roll", "name", "class", "section"]:
            assert f'name="{column}"' in markup

@check("a student sees their own marks and their total")
def _():
    with Serving() as serving:
        serving.upload()
        results = results_section(serving.get("/lookup?" + urllib.parse.urlencode(
            {"roll": "13", "name": "", "class": "", "section": ""}))[1])
        assert "81" in results and "90" in results and "77" in results
        assert "Total" in results and "248" in results

@check("a student does not see anyone else's marks")
def _():
    with Serving() as serving:
        serving.upload()
        results = results_section(serving.get("/lookup?" + urllib.parse.urlencode(
            {"roll": "12", "name": "", "class": "", "section": ""}))[1])
        assert "72" in results and "65" in results and "80" in results
        assert "81" not in results and "90" not in results and "77" not in results

@check("an ambiguous match asks for more detail instead of showing marks")
def _():
    with Serving() as serving:
        serving.upload()
        markup = serving.get("/lookup?" + urllib.parse.urlencode(
            {"roll": "", "name": "Sanket", "class": "", "section": ""}))[1]
        assert "2 students match" in markup
        # no marks table at all, so neither student's results are shown
        assert results_section(markup) == ""

@check("an unknown student is told so")
def _():
    with Serving() as serving:
        serving.upload()
        markup = serving.get("/lookup?" + urllib.parse.urlencode(
            {"roll": "99", "name": "", "class": "", "section": ""}))[1]
        assert "No student found" in markup

@check("submitting an empty form asks for something to go on")
def _():
    with Serving() as serving:
        serving.upload()
        markup = serving.get("/lookup?roll=&name=&class=&section=")[1]
        assert "at least one box" in markup

@check("a non-csv upload is refused with an explanation")
def _():
    with Serving() as serving:
        status, markup = serving.upload("nonsense", "results.xlsx")
        assert status == 400
        assert "Excel" in markup

@check("an empty sheet is refused")
def _():
    with Serving() as serving:
        status, markup = serving.upload("roll,name,Maths\n", "empty.csv")
        assert status == 400 and "no students" in markup

@check("an uploaded name cannot escape the uploads folder")
def _():
    assert web.safe_name("../../etc/passwd") == "passwd"
    assert web.safe_name("") == "sheet.csv"
    assert "/" not in web.safe_name("a/b/c.csv")

@check("a name containing html is escaped on the page")
def _():
    with Serving() as serving:
        serving.upload()
        markup = serving.get("/lookup?" + urllib.parse.urlencode(
            {"roll": "<script>alert(1)</script>", "name": "", "class": "", "section": ""}))[1]
        assert "<script>alert(1)</script>" not in markup
        assert "&lt;script&gt;" in markup

@check("an unknown address gives a 404, not a traceback")
def _():
    with Serving() as serving:
        serving.upload()
        assert serving.get("/nope")[0] == 404

if __name__ == '__main__':
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
