""" 
    checks on organisations, who is allowed where, and signing in

    run it with: python3 tests/test_accounts.py
"""
import os
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marks import accounts
from marks import web
from marks.database import Database
from harness import (SHEET_CSV, Serving, headings, invites, join_code, registry,
                     results_section, run, sheet_id, warning)

CHECKS, check = registry()

SECOND_TERM = ("roll,name,class,section,Maths,Science,English\n"
               "12,Sanket,10,A,90,88,84\n"
               "13,Mokshada,10,A,70,75,72\n"
               "14,Sanket,10,B,61,64,66\n")

# ---------- passwords and sessions on their own ----------

@check("a password can be checked but not read back")
def _():
    stored = accounts.hash_password("correct horse battery")
    assert "correct horse battery" not in stored
    assert accounts.check_password("correct horse battery", stored)
    assert not accounts.check_password("Correct horse battery", stored)
    # the same password hashed twice looks different, because the salt differs
    assert stored != accounts.hash_password("correct horse battery")

@check("a stored password that has been damaged never matches")
def _():
    for broken in ["", "nonsense", "scrypt$notahexsalt$00", "md5$aa$bb"]:
        assert not accounts.check_password("anything", broken)

@check("a password has to be long enough, and typed the same twice")
def _():
    assert accounts.password_problem("short", "short")
    assert accounts.password_problem("longenough1", "longenough2")
    assert accounts.password_problem("longenough1", "longenough1") == ""

@check("a session says who it belongs to, and cannot be edited")
def _():
    secret = os.urandom(32)
    cookie = accounts.make_session(secret, "teacher", "person-1", "org-1")
    read = accounts.read_session(secret, cookie)
    assert read["kind"] == "teacher" and read["id"] == "person-1" and read["org"] == "org-1"
    # changed text, another server's secret, or an expired one are all refused
    assert accounts.read_session(secret, cookie[:-2] + "zz") is None
    assert accounts.read_session(os.urandom(32), cookie) is None
    assert accounts.read_session(secret, cookie, now=time.time() + accounts.SESSION_SECONDS + 1) is None
    assert accounts.read_session(secret, "") is None

@check("a join code is read back however it was typed")
def _():
    code = accounts.new_join_code()
    assert accounts.tidy_join_code(code.lower()) == code
    assert accounts.tidy_join_code(code.replace("-", " ")) == code
    assert accounts.tidy_join_code("abc") == ""
    # the confusable characters are never handed out in the first place
    assert not set(code.replace("-", "")) & set("OI015S")

# ---------- the database on its own ----------

@check("an organisation is made together with the teacher who runs it")
def _():
    db = Database(os.path.join(tempfile.mkdtemp(), "t.db"))
    org, complaint = db.create_org("Springfield High", "miss_hoover", "longenough1")
    assert complaint == "" and org["name"] == "Springfield High"
    assert db.sign_in_teacher("miss_hoover", "longenough1")["orgId"] == org["id"]
    assert db.sign_in_teacher("miss_hoover", "wrong") is None
    # a name already in use does not quietly make a second organisation
    assert db.create_org("Other", "miss_hoover", "longenough1")[0] is None
    db.close()

@check("a student account is remembered against the organisation, not a sheet")
def _():
    db = Database(os.path.join(tempfile.mkdtemp(), "t.db"))
    org, _ = db.create_org("Springfield High", "miss_hoover", "longenough1")
    student, complaint = db.enrol_student(org["id"], " 12 ", "Sanket", "longenough1")
    assert complaint == "" and student["keyValue"] == "12"
    assert db.enrol_student(org["id"], "12", "Sanket", "longenough1")[0] is None
    assert db.sign_in_student(org["id"], "12", "longenough1")
    assert db.sign_in_student(org["id"], "12", "wrong") is None
    db.close()

# ---------- who is allowed where ----------

@check("the teacher's pages need a teacher signed in")
def _():
    with Serving() as serving:
        _, _, sheetId, _ = serving.teaching()
        stranger = serving.browser()
        assert stranger.get("/teacher")[0] == 403
        assert stranger.get(f"/teacher/sheet/{sheetId}")[0] == 403
        assert stranger.upload()[0] == 403
        assert stranger.get("/me")[0] == 403

@check("a made up session cookie counts as signed out")
def _():
    with Serving() as serving:
        serving.teaching()
        stranger = serving.browser()
        request = urllib.request.Request(f"{serving.base}/teacher")
        request.add_header("Cookie", f"{web.SESSION_COOKIE}=made.up")
        try:
            stranger.opener.open(request)
            assert False, "a forged cookie was accepted"
        except urllib.error.HTTPError as error:
            assert error.code == 403

@check("signing out puts the teacher back outside")
def _():
    with Serving() as serving:
        teacher, _, _, _ = serving.teaching()
        assert teacher.get("/teacher")[0] == 200
        teacher.post("/signout", {})
        assert teacher.get("/teacher")[0] == 403

@check("a teacher name already taken is refused")
def _():
    with Serving() as serving:
        serving.browser().start_org()
        status, markup = serving.browser().post("/org/new", {
            "orgName": "Another", "username": "miss_hoover",
            "password": "longenough1", "again": "longenough1"})
        assert status == 400 and "already taken" in markup

@check("a wrong teacher name and a wrong password are told apart by nobody")
def _():
    with Serving() as serving:
        serving.teaching()
        wrongName = serving.browser().post(
            "/signin/teacher", {"username": "nobody", "password": "longenough1"})[1]
        wrongPassword = serving.browser().post(
            "/signin/teacher", {"username": "miss_hoover", "password": "wrongwrong"})[1]
        # the pages differ only where they echo back what was typed
        assert "do not match" in warning(wrongName)
        assert warning(wrongName) == warning(wrongPassword)

@check("a teacher signs back in and finds their organisation")
def _():
    with Serving() as serving:
        teacher, code, sheetId, _ = serving.teaching()
        again = serving.browser()
        status, markup = again.post("/signin/teacher",
                                    {"username": "miss_hoover", "password": "longenough1"})
        assert status == 200 and join_code(markup) == code
        assert again.get(f"/teacher/sheet/{sheetId}")[0] == 200

# ---------- one organisation cannot see another ----------

@check("a teacher cannot open another organisation's sheet")
def _():
    with Serving() as serving:
        _, _, sheetId, _ = serving.teaching()
        other = serving.browser()
        other.start_org(orgName="Other School", username="mr_other")
        # not a 403: another organisation's sheet is simply not there
        assert other.get(f"/teacher/sheet/{sheetId}")[0] == 404
        assert other.get(f"/teacher/sheet/{sheetId}/lookup?roll=12")[0] == 404

@check("a student sees only the sheets of their own organisation")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        student = serving.browser()
        student.post(f"/s/{invites(markup)[0]}/enrol",
                     {"password": "longenough1", "again": "longenough1"})

        other = serving.browser()
        other.start_org(orgName="Other School", username="mr_other")
        other.upload("roll,name,Maths\n12,Someone Else,99\n", "elsewhere.csv")

        theirs = student.get("/me")[1]
        assert "results.csv" in theirs
        assert "elsewhere.csv" not in theirs and "Someone Else" not in theirs

@check("a student cannot reach the teacher's pages")
def _():
    with Serving() as serving:
        _, _, sheetId, markup = serving.teaching()
        student = serving.browser()
        student.post(f"/s/{invites(markup)[0]}/enrol",
                     {"password": "longenough1", "again": "longenough1"})
        assert student.get("/teacher")[0] == 403
        assert student.get(f"/teacher/sheet/{sheetId}")[0] == 403
        assert student.upload()[0] == 403

# ---------- becoming a student ----------

@check("an invite offers a password, and setting it signs the student in")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        student = serving.browser()
        invite = student.get(f"/s/{invites(markup)[0]}")[1]
        assert "Set a password" in invite

        status, home = student.post(f"/s/{invites(markup)[0]}/enrol",
                                    {"password": "longenough1", "again": "longenough1"})
        assert status == 200
        assert headings(home) == ["results.csv"]
        results = results_section(home, "results.csv")
        assert "72" in results and "65" in results and "80" in results

@check("a password that is too short is refused, and no account is made")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        student = serving.browser()
        status, again = student.post(f"/s/{invites(markup)[0]}/enrol",
                                     {"password": "short", "again": "short"})
        assert "at least" in again
        assert student.get("/me")[0] == 403

@check("an invite already used says so instead of making a second account")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching()
        token = invites(markup)[0]
        serving.browser().post(f"/s/{token}/enrol",
                               {"password": "longenough1", "again": "longenough1"})
        # somebody else opening the same invite cannot take it over
        thief = serving.browser()
        assert "already have a password" in thief.get(f"/s/{token}")[1]
        assert "already set a password" in thief.post(
            f"/s/{token}/enrol", {"password": "different1", "again": "different1"})[1]
        assert thief.get("/me")[0] == 403

@check("a row with no roll number cannot become an account")
def _():
    with Serving() as serving:
        _, _, _, markup = serving.teaching("roll,name,Maths\n,Nameless,50\n", "blank.csv")
        student = serving.browser()
        answer = student.post(f"/s/{invites(markup)[0]}/enrol",
                              {"password": "longenough1", "again": "longenough1"})[1]
        assert "no roll number" in answer
        assert student.get("/me")[0] == 403

# ---------- signing in as a student ----------

@check("a student signs in with the join code, however it was typed")
def _():
    with Serving() as serving:
        _, code, _, markup = serving.teaching()
        serving.browser().post(f"/s/{invites(markup)[0]}/enrol",
                               {"password": "longenough1", "again": "longenough1"})
        again = serving.browser()
        status, home = again.post("/signin/student", {
            "joinCode": code.lower().replace("-", " "), "keyValue": " 12 ",
            "password": "longenough1"})
        assert status == 200 and headings(home) == ["results.csv"]

@check("a wrong join code, roll number or password all get the same refusal")
def _():
    with Serving() as serving:
        _, code, _, markup = serving.teaching()
        serving.browser().post(f"/s/{invites(markup)[0]}/enrol",
                               {"password": "longenough1", "again": "longenough1"})
        wrong = [{"joinCode": "ZZZZ-9999", "keyValue": "12", "password": "longenough1"},
                 {"joinCode": code, "keyValue": "99", "password": "longenough1"},
                 {"joinCode": code, "keyValue": "12", "password": "wrongwrong"}]
        answers = [serving.browser().post("/signin/student", fields) for fields in wrong]
        assert all(status == 400 for status, _ in answers)
        assert len({warning(markup) for _, markup in answers}) == 1

@check("signing in shows this student's row and nobody else's")
def _():
    with Serving() as serving:
        _, code, _, markup = serving.teaching()
        serving.browser().post(f"/s/{invites(markup)[0]}/enrol",
                               {"password": "longenough1", "again": "longenough1"})
        home = serving.browser().post("/signin/student", {
            "joinCode": code, "keyValue": "12", "password": "longenough1"})[1]
        assert "Mokshada" not in home
        results = results_section(home, "results.csv")
        assert "72" in results and "65" in results and "80" in results
        assert "81" not in results and "90" not in results

@check("an account made this term also finds next term's sheet")
def _():
    with Serving() as serving:
        teacher, code, _, markup = serving.teaching()
        student = serving.browser()
        student.post(f"/s/{invites(markup)[0]}/enrol",
                     {"password": "longenough1", "again": "longenough1"})
        assert headings(student.get("/me")[1]) == ["results.csv"]

        # the teacher uploads again, without touching anybody's account
        teacher.upload(SECOND_TERM, "term2.csv")
        assert sorted(headings(student.get("/me")[1])) == ["results.csv", "term2.csv"]

        later = serving.browser().post("/signin/student", {
            "joinCode": code, "keyValue": "12", "password": "longenough1"})[1]
        # their own row on the new sheet, and still nobody else's
        assert "90" in results_section(later, "term2.csv")
        assert "70" not in results_section(later, "term2.csv")

@check("a student with nothing uploaded for them is told so, not shown a blank page")
def _():
    with Serving() as serving:
        teacher, code, _, markup = serving.teaching()
        student = serving.browser()
        student.post(f"/s/{invites(markup)[0]}/enrol",
                     {"password": "longenough1", "again": "longenough1"})
        # every sheet the account could match is taken away again
        for record in serving.store.db.all_sheets():
            serving.store.forget(record["id"])
            serving.store.db.remove_sheet(record["id"])
        assert "Nothing has been uploaded for you yet" in student.get("/me")[1]

# ---------- surviving a restart ----------

@check("organisations, accounts and invites all survive a restart")
def _():
    with Serving() as serving:
        _, code, sheetId, markup = serving.teaching()
        token = invites(markup)[0]
        serving.browser().post(f"/s/{token}/enrol",
                               {"password": "longenough1", "again": "longenough1"})

        # a brand new store over the same folder, the way a restart does
        restarted = web.Store(serving.folder)
        try:
            assert restarted.load_saved() == 1
            assert restarted.token_for(sheetId, 0) == token
            org = restarted.db.org_by_code(code)
            assert org and restarted.db.sign_in_teacher("miss_hoover", "longenough1")
            assert restarted.db.sign_in_student(org["id"], "12", "longenough1")
        finally:
            restarted.close()

if __name__ == '__main__':
    run(CHECKS)
