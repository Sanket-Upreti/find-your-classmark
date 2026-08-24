""" 
    checks on the mark sheet reading, the lookup page and the per-student links

    run it with: python3 tests/test_marks.py
"""
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marks import links
from marks import loaders
from marks import sheet as sheet_module
from marks import web

CHECKS = []

class Skipped(Exception):
    """ raised by a check that can't run here, rather than failing it """

# excel checks only run when openpyxl is installed; csv must work without it
def needs_openpyxl():
    try:
        import openpyxl                     # noqa: F401
    except ImportError:
        raise Skipped("openpyxl is not installed")

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

""" 
    only the marks table itself, so neither a number in the stylesheet nor two
    digits that happen to fall inside a link token can fool a check
"""
def results_section(markup):
    marker = "<h2>Your marks</h2>"
    if marker not in markup:
        return ""
    return markup.split(marker, 1)[1].split("</table>", 1)[0]

SHEET_ADDRESS = re.compile(r"/sheet/([0-9a-f]{16})")
STUDENT_ADDRESS = re.compile(r"/s/([0-9a-f]{%d})" % links.TOKEN_LENGTH)

# the id an upload put the sheet under, read back off the page it landed on
def sheet_id(markup):
    found = SHEET_ADDRESS.search(markup)
    assert found, "the page that came back is not a sheet page"
    return found.group(1)

# every student link on a page, in the order they appear, without repeats
def student_tokens(markup):
    seen = []
    for token in STUDENT_ADDRESS.findall(markup):
        if token not in seen:
            seen.append(token)
    return seen

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
        return self.upload_bytes(contents.encode(), fileName)

    def upload_bytes(self, contents, fileName="results.csv"):
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="sheet"; filename="{fileName}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n").encode() + contents + \
               f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            self.base + "/upload", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

    # asking for one student through the sheet's own lookup form
    def lookup(self, sheetId, criteria):
        return self.get(f"/sheet/{sheetId}/lookup?" + urllib.parse.urlencode(criteria))

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

@check("a sheet's own Total column is shown but not added up again")
def _():
    sheet = load_sheet("roll,name,Maths,Science,Total,Percentage\n12,Sanket,72,65,137,68.5\n")
    assert sheet.summaryColumns == ["Total", "Percentage"]
    marks = sheet_module.marks_for(sheet, sheet_module.find(sheet, {"roll": "12"})[0])
    assert ("Total", "137") in marks
    total, average = sheet_module.total_and_average(marks, skip=sheet.summaryColumns)
    assert total == 137 and average == 68.5

@check("total and average skip anything that isn't a number")
def _():
    total, average = sheet_module.total_and_average([("Maths", "72"), ("Remarks", "Good"), ("Science", "68")])
    assert total == 140 and average == 70.0

@check("marks with no numbers at all report no total")
def _():
    assert sheet_module.total_and_average([("Grade", "A")]) == (None, None)

# ---------- the tokens behind the links ----------

@check("a link token is unguessable and tied to one row of one sheet")
def _():
    secret = os.urandom(32)
    first = links.student_token(secret, "aaaaaaaaaaaaaaaa", 0)
    assert len(first) == links.TOKEN_LENGTH
    # the same row always gives the same link, so a handed out address keeps working
    assert first == links.student_token(secret, "aaaaaaaaaaaaaaaa", 0)
    # a different row, a different sheet, or a different secret gives a different one
    assert first != links.student_token(secret, "aaaaaaaaaaaaaaaa", 1)
    assert first != links.student_token(secret, "bbbbbbbbbbbbbbbb", 0)
    assert first != links.student_token(os.urandom(32), "aaaaaaaaaaaaaaaa", 0)

@check("the secret behind the links is made once and then reused")
def _():
    folder = tempfile.mkdtemp()
    try:
        first = links.read_secret(folder)
        assert len(first) == 32
        assert first == links.read_secret(folder)
        assert oct(os.stat(os.path.join(folder, links.SECRET_NAME)).st_mode)[-3:] == "600"
    finally:
        shutil.rmtree(folder, ignore_errors=True)

@check("a saved file carries its sheet id, and an unrelated name is ignored")
def _():
    assert web.split_saved(web.saved_name("0123456789abcdef", "my__marks.csv")) == \
        ("0123456789abcdef", "my__marks.csv")
    assert web.split_saved("results.csv") == (None, None)
    assert web.split_saved("nothex__results.csv") == (None, None)

# ---------- the pages ----------

@check("the page asks for an upload before anything is loaded")
def _():
    with Serving() as serving:
        status, markup = serving.get("/")
        assert status == 200 and "Upload" in markup and 'type="file"' in markup

@check("uploading a sheet leads to a page of links")
def _():
    with Serving() as serving:
        status, markup = serving.upload()
        assert status == 200
        assert "3 student(s)" in markup
        for column in ["roll", "name", "class", "section"]:
            assert f'name="{column}"' in markup
        # one link for every student, all different
        assert len(student_tokens(markup)) == 3

@check("a student's own link shows their own marks")
def _():
    with Serving() as serving:
        markup = serving.upload()[1]
        tokens = student_tokens(markup)
        results = results_section(serving.get(f"/s/{tokens[0]}")[1])
        assert "72" in results and "65" in results and "80" in results
        assert "Total" in results and "217" in results

@check("a student's own link shows nobody else, and no way to reach them")
def _():
    with Serving() as serving:
        markup = serving.upload()[1]
        tokens = student_tokens(markup)
        status, theirs = serving.get(f"/s/{tokens[0]}")
        assert status == 200
        assert "Mokshada" not in theirs
        results = results_section(theirs)
        assert "81" not in results and "90" not in results and "77" not in results
        # nothing on the page walks back up to the sheet that holds everyone
        assert "/sheet/" not in theirs
        assert not [token for token in student_tokens(theirs) if token != tokens[0]]

@check("a made up link is not found")
def _():
    with Serving() as serving:
        serving.upload()
        assert serving.get("/s/" + "0" * links.TOKEN_LENGTH)[0] == 404

@check("a second upload does not replace the first")
def _():
    with Serving() as serving:
        first = sheet_id(serving.upload()[1])
        second = sheet_id(serving.upload("roll,name,Maths\n99,Other,40\n", "other.csv")[1])
        assert first != second
        assert "3 student(s)" in serving.get(f"/sheet/{first}")[1]
        assert "1 student(s)" in serving.get(f"/sheet/{second}")[1]

@check("the links handed out keep working after a restart")
def _():
    with Serving() as serving:
        markup = serving.upload()[1]
        sheetId = sheet_id(markup)
        before = student_tokens(markup)
        # a brand new store reading the same folder, the way a restart does
        restarted = web.Store()
        assert restarted.load_saved() == 1
        after = [restarted.token_for(sheetId, position) for position in range(3)]
        assert before == after
        assert restarted.student(before[0])[1] is not None

@check("an unknown sheet address is not found")
def _():
    with Serving() as serving:
        serving.upload()
        assert serving.get("/sheet/" + "0" * 16)[0] == 404

@check("a file type that isn't read is refused with an explanation")
def _():
    with Serving() as serving:
        status, markup = serving.upload("nonsense", "results.pdf")
        assert status == 400
        assert ".csv" in markup and ".xlsx" in markup

@check("a student is found through the sheet's own lookup form")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        results = results_section(serving.lookup(
            sheetId, {"roll": "13", "name": "", "class": "", "section": ""})[1])
        assert "81" in results and "90" in results and "77" in results
        assert "Total" in results and "248" in results

@check("a lookup shows only the student that was asked for")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        results = results_section(serving.lookup(
            sheetId, {"roll": "12", "name": "", "class": "", "section": ""})[1])
        assert "72" in results and "65" in results and "80" in results
        assert "81" not in results and "90" not in results and "77" not in results

@check("a sheet's own totals are shown once, not alongside worked out ones")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload(
            "roll,name,Maths,Science,Total\n12,Sanket,72,65,137\n", "withtotal.csv")[1])
        results = results_section(serving.lookup(sheetId, {"roll": "12", "name": ""})[1])
        assert results.count("Total") == 1
        assert "137" in results
        # nothing is worked out on top of the sheet's own figures
        assert "Average" not in results

@check("a sheet with no totals of its own gets them worked out")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload(
            "roll,name,Maths,Science\n12,Sanket,72,65\n", "plain.csv")[1])
        results = results_section(serving.lookup(sheetId, {"roll": "12", "name": ""})[1])
        assert "Total" in results and "137" in results
        assert "Average" in results and "68.5" in results

@check("an ambiguous match asks for more detail instead of showing marks")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        markup = serving.lookup(
            sheetId, {"roll": "", "name": "Sanket", "class": "", "section": ""})[1]
        assert "2 students match" in markup
        # no marks table at all, so neither student's results are shown
        assert results_section(markup) == ""

@check("an unknown student is told so")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        markup = serving.lookup(
            sheetId, {"roll": "99", "name": "", "class": "", "section": ""})[1]
        assert "No student found" in markup

@check("submitting an empty form asks for something to go on")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        markup = serving.lookup(sheetId, {"roll": "", "name": "", "class": "", "section": ""})[1]
        assert "at least one box" in markup

@check("an empty sheet is refused, and leaves nothing behind")
def _():
    with Serving() as serving:
        status, markup = serving.upload("roll,name,Maths\n", "empty.csv")
        assert status == 400 and "no students" in markup
        assert serving.store.sheets == {} and serving.store.students == {}
        assert [name for name in os.listdir(serving.uploads) if name.endswith(".csv")] == []

@check("an uploaded name cannot escape the uploads folder")
def _():
    assert web.safe_name("../../etc/passwd") == "passwd"
    assert web.safe_name("") == "sheet.csv"
    assert "/" not in web.safe_name("a/b/c.csv")

@check("a name containing html is escaped on the page")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        markup = serving.lookup(
            sheetId, {"roll": "<script>alert(1)</script>", "name": "", "class": "", "section": ""})[1]
        assert "<script>alert(1)</script>" not in markup
        assert "&lt;script&gt;" in markup

@check("a host header cannot smuggle markup into a link")
def _():
    with Serving() as serving:
        sheetId = sheet_id(serving.upload()[1])
        request = urllib.request.Request(f"{serving.base}/sheet/{sheetId}")
        request.add_header("Host", '127.0.0.1"><script>alert(1)</script>')
        with urllib.request.urlopen(request) as response:
            markup = response.read().decode("utf-8")
        assert "<script>alert(1)</script>" not in markup

@check("an unknown address gives a 404, not a traceback")
def _():
    with Serving() as serving:
        serving.upload()
        assert serving.get("/nope")[0] == 404

# ---------- excel ----------

# building a real .xlsx on the fly, the way a school would export one
def write_xlsx(rows, name="results.xlsx"):
    import openpyxl
    path = os.path.join(tempfile.mkdtemp(), name)
    workbook = openpyxl.Workbook()
    for row in rows:
        workbook.active.append(row)
    workbook.save(path)
    return path

@check("an excel sheet is read, with numbers arriving as plain marks")
def _():
    needs_openpyxl()
    path = write_xlsx([["roll", "name", "class", "Maths", "Science"],
                       [12, "Sanket", 10, 72, 65.0],
                       [13, "Mokshada", 10, 81, 90]])
    sheet = sheet_module.from_table(loaders.load_table(path), "results.xlsx")
    assert sheet.identityColumns == ["roll", "name", "class"]
    assert sheet.markColumns == ["Maths", "Science"]
    found = sheet_module.find(sheet, {"roll": "12"})
    # 65.0 must not be shown as "65.0", and 12 must match the text typed into the form
    assert sheet_module.marks_for(sheet, found[0]) == [("Maths", "72"), ("Science", "65")]

@check("blank trailing rows in a workbook are ignored")
def _():
    needs_openpyxl()
    path = write_xlsx([["roll", "Maths"], [12, 72], [None, None], [None, None]])
    assert len(loaders.load_table(path).rows) == 1

@check("an excel sheet can be uploaded and handed out as links")
def _():
    needs_openpyxl()
    path = write_xlsx([["roll", "name", "Maths", "Science"], [12, "Sanket", 72, 65]])
    with open(path, "rb") as workbook:
        contents = workbook.read()
    with Serving() as serving:
        status, markup = serving.upload_bytes(contents, "results.xlsx")
        assert status == 200
        tokens = student_tokens(markup)
        assert len(tokens) == 1
        results = results_section(serving.get(f"/s/{tokens[0]}")[1])
        assert "72" in results and "65" in results and "137" in results

@check("without openpyxl, an excel upload is refused with an install hint")
def _():
    try:
        import openpyxl                     # noqa: F401
        raise Skipped("openpyxl is installed, so the missing case can't be shown")
    except ImportError:
        pass
    with Serving() as serving:
        status, markup = serving.upload_bytes(b"PK\x03\x04 not really", "results.xlsx")
        assert status == 400
        assert "openpyxl" in markup

if __name__ == '__main__':
    failures = skipped = 0
    for name, function in CHECKS:
        try:
            function()
            print(f"  ok   {name}")
        except Skipped as reason:
            skipped += 1
            print(f"  skip {name} ({reason})")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error or 'assertion failed'}")
    passed = len(CHECKS) - failures - skipped
    tail = f", {skipped} skipped" if skipped else ""
    print(f"\n{passed}/{len(CHECKS) - skipped} checks passed{tail}")
    raise SystemExit(1 if failures else 0)
