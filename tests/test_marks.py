""" 
    checks on reading a mark sheet and showing one student's marks

    run it with: python3 tests/test_marks.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marks import links
from marks import loaders
from marks import sheet as sheet_module
from marks import web
from harness import (SHEET_CSV, Serving, Skipped, invites, needs_openpyxl, registry,
                     results_section, run, write_csv)

CHECKS, check = registry()

def load_sheet(contents=SHEET_CSV):
    path = write_csv(contents)
    return sheet_module.from_table(loaders.load_table(path), os.path.basename(path))

# ---------- telling the columns apart ----------

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

@check("a roll number is preferred as the column a student is known by")
def _():
    assert sheet_module.key_column(load_sheet()) == "roll"
    assert sheet_module.key_column(load_sheet(
        "Admission No.,Name,Maths\nA-1,Sanket,72\n")) == "Admission No."
    # a sheet with no number at all falls back to whatever comes first
    assert sheet_module.key_column(load_sheet("name,class,Maths\nSanket,10,72\n")) == "name"

@check("a student is found by their key however it was typed")
def _():
    sheet = load_sheet()
    found = sheet_module.rows_for_key(sheet, "roll", "  12 ")
    assert len(found) == 1 and sheet_module.cell(found[0], "name") == "Sanket"
    assert sheet_module.rows_for_key(sheet, "roll", "99") == []
    assert sheet_module.rows_for_key(sheet, "roll", "") == []

# ---------- finding and adding up ----------

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

# ---------- the tokens behind the invites ----------

@check("an invite token is unguessable and tied to one row of one sheet")
def _():
    secret = os.urandom(32)
    first = links.student_token(secret, "aaaaaaaaaaaaaaaa", 0)
    assert len(first) == links.TOKEN_LENGTH
    # the same row always gives the same invite, so a handed out address keeps working
    assert first == links.student_token(secret, "aaaaaaaaaaaaaaaa", 0)
    # a different row, a different sheet, or a different secret gives a different one
    assert first != links.student_token(secret, "aaaaaaaaaaaaaaaa", 1)
    assert first != links.student_token(secret, "bbbbbbbbbbbbbbbb", 0)
    assert first != links.student_token(os.urandom(32), "aaaaaaaaaaaaaaaa", 0)

@check("the secret behind the invites is made once and then reused")
def _():
    import shutil
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

# ---------- what a page shows ----------

@check("uploading a sheet leads to a page of invites")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        assert "3 student(s)" in markup
        for column in ["roll", "name", "class", "section"]:
            assert f'name="{column}"' in markup
        assert len(invites(markup)) == 3

@check("an invite shows their own marks and their total")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        results = results_section(serving.browser().get(f"/s/{invites(markup)[0]}")[1])
        assert "72" in results and "65" in results and "80" in results
        assert "Total" in results and "217" in results

@check("an invite shows nobody else, and no way to reach them")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        tokens = invites(markup)
        status, theirs = serving.browser().get(f"/s/{tokens[0]}")
        assert status == 200
        assert "Mokshada" not in theirs
        results = results_section(theirs)
        assert "81" not in results and "90" not in results and "77" not in results
        # nothing on the page walks back up to the sheet that holds everyone
        assert "/teacher/sheet/" not in theirs
        assert [token for token in invites(theirs) if token != tokens[0]] == []

@check("a made up invite is not found")
def _():
    with Serving() as serving:
        serving.teaching()
        assert serving.browser().get("/s/" + "0" * links.TOKEN_LENGTH)[0] == 404

@check("a teacher finds one student through the sheet's own form")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        results = results_section(teacher.get(
            f"/teacher/sheet/{sheetId}/lookup?roll=13&name=&class=&section=")[1])
        assert "81" in results and "90" in results and "77" in results
        assert "Total" in results and "248" in results

@check("a lookup shows only the student that was asked for")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        results = results_section(teacher.get(
            f"/teacher/sheet/{sheetId}/lookup?roll=12&name=&class=&section=")[1])
        assert "72" in results and "65" in results and "80" in results
        assert "81" not in results and "90" not in results and "77" not in results

@check("a sheet's own totals are shown once, not alongside worked out ones")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching(
            "roll,name,Maths,Science,Total\n12,Sanket,72,65,137\n", "withtotal.csv")
        results = results_section(teacher.get(
            f"/teacher/sheet/{sheetId}/lookup?roll=12&name=")[1])
        assert results.count("Total") == 1
        assert "137" in results
        # nothing is worked out on top of the sheet's own figures
        assert "Average" not in results

@check("a sheet with no totals of its own gets them worked out")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching(
            "roll,name,Maths,Science\n12,Sanket,72,65\n", "plain.csv")
        results = results_section(teacher.get(
            f"/teacher/sheet/{sheetId}/lookup?roll=12&name=")[1])
        assert "Total" in results and "137" in results
        assert "Average" in results and "68.5" in results

@check("an ambiguous match asks for more detail instead of showing marks")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        markup = teacher.get(f"/teacher/sheet/{sheetId}/lookup?roll=&name=Sanket&class=&section=")[1]
        assert "2 students match" in markup
        # no marks table at all, so neither student's results are shown
        assert results_section(markup) == ""

@check("an unknown student is told so")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        assert "No student found" in teacher.get(
            f"/teacher/sheet/{sheetId}/lookup?roll=99&name=&class=&section=")[1]

@check("submitting an empty form asks for something to go on")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        assert "at least one box" in teacher.get(
            f"/teacher/sheet/{sheetId}/lookup?roll=&name=&class=&section=")[1]

# ---------- what is refused ----------

@check("a file type that isn't read is refused with an explanation")
def _():
    with Serving() as serving:
        teacher = serving.browser()
        teacher.start_org()
        status, markup = teacher.upload("nonsense", "results.pdf")
        assert status == 400
        assert ".csv" in markup and ".xlsx" in markup

@check("an empty sheet is refused, and leaves nothing behind")
def _():
    with Serving() as serving:
        teacher = serving.browser()
        teacher.start_org()
        status, markup = teacher.upload("roll,name,Maths\n", "empty.csv")
        assert status == 400 and "no students" in markup
        assert serving.store.sheets == {} and serving.store.students == {}
        assert serving.store.db.all_sheets() == []
        assert [name for name in os.listdir(serving.folder) if name.endswith(".csv")] == []

@check("an uploaded name cannot escape the uploads folder")
def _():
    assert web.safe_name("../../etc/passwd") == "passwd"
    assert web.safe_name("") == "sheet.csv"
    assert "/" not in web.safe_name("a/b/c.csv")

@check("a name containing html is escaped on the page")
def _():
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        markup = teacher.get(f"/teacher/sheet/{sheetId}/lookup?"
                             "roll=%3Cscript%3Ealert(1)%3C/script%3E&name=")[1]
        assert "<script>alert(1)</script>" not in markup
        assert "&lt;script&gt;" in markup

@check("a host header cannot smuggle markup into an invite")
def _():
    import urllib.request
    with Serving() as serving:
        teacher, _, sheetId, _ = serving.teaching()
        request = urllib.request.Request(f"{serving.base}/teacher/sheet/{sheetId}")
        request.add_header("Host", '127.0.0.1"><script>alert(1)</script>')
        with teacher.opener.open(request) as response:
            markup = response.read().decode("utf-8")
        assert "<script>alert(1)</script>" not in markup

@check("an unknown address gives a 404, not a traceback")
def _():
    with Serving() as serving:
        assert serving.browser().get("/nope")[0] == 404

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

@check("an excel sheet can be uploaded and handed out as invites")
def _():
    needs_openpyxl()
    path = write_xlsx([["roll", "name", "Maths", "Science"], [12, "Sanket", 72, 65]])
    with open(path, "rb") as workbook:
        contents = workbook.read()
    with Serving() as serving:
        teacher = serving.browser()
        teacher.start_org()
        status, markup = teacher.upload_bytes(contents, "results.xlsx")
        assert status == 200
        tokens = invites(markup)
        assert len(tokens) == 1
        results = results_section(serving.browser().get(f"/s/{tokens[0]}")[1])
        assert "72" in results and "65" in results and "137" in results

@check("without openpyxl, an excel upload is refused with an install hint")
def _():
    try:
        import openpyxl                     # noqa: F401
        raise Skipped("openpyxl is installed, so the missing case can't be shown")
    except ImportError:
        pass
    with Serving() as serving:
        teacher = serving.browser()
        teacher.start_org()
        status, markup = teacher.upload_bytes(b"PK\x03\x04 not really", "results.xlsx")
        assert status == 400
        assert "openpyxl" in markup

if __name__ == '__main__':
    run(CHECKS)
