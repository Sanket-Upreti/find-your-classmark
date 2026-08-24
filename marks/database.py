""" 
    what has to outlive a restart: organisations, the people in them, and which
    sheets belong to which.

    the mark sheets themselves stay as files; this only records who they belong
    to and how a student is recognised on them
"""
import os
import sqlite3
from datetime import datetime, timezone

from . import accounts

SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    joinCode    TEXT NOT NULL UNIQUE,
    createdAt   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teachers (
    id           TEXT PRIMARY KEY,
    orgId        TEXT NOT NULL REFERENCES orgs(id),
    username     TEXT NOT NULL UNIQUE,
    passwordHash TEXT NOT NULL,
    createdAt    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sheets (
    id          TEXT PRIMARY KEY,
    orgId       TEXT NOT NULL REFERENCES orgs(id),
    fileName    TEXT NOT NULL,
    savedAs     TEXT NOT NULL,
    keyColumn   TEXT NOT NULL,
    uploadedAt  TEXT NOT NULL
);
/* one row per student per organisation, not per sheet, so an account made this
   term still works against next term's upload */
CREATE TABLE IF NOT EXISTS students (
    id           TEXT PRIMARY KEY,
    orgId        TEXT NOT NULL REFERENCES orgs(id),
    keyValue     TEXT NOT NULL,
    displayName  TEXT NOT NULL,
    passwordHash TEXT NOT NULL,
    createdAt    TEXT NOT NULL,
    UNIQUE (orgId, keyValue)
);
"""

def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# how a roll number is compared, so "  12 " and "12" are the same student
def tidy_key(value):
    return " ".join(str(value or "").split()).lower()

class Database:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        if folder:
            os.makedirs(folder, exist_ok=True)
        # one thread serves every request, so a single connection is enough
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def _run(self, statement, values=()):
        cursor = self.connection.execute(statement, values)
        self.connection.commit()
        return cursor

    def _one(self, statement, values=()):
        return self.connection.execute(statement, values).fetchone()

    def _all(self, statement, values=()):
        return self.connection.execute(statement, values).fetchall()

    # ---------- organisations ----------

    """
        making an organisation and the teacher who runs it together, so an
        organisation is never left with nobody able to sign in to it
    """
    def create_org(self, name, username, password):
        if self.teacher_by_username(username):
            return None, "That teacher name is already taken."

        orgId, teacherId = accounts.new_id(), accounts.new_id()
        # a fresh code on a collision, rather than handing back a duplicate
        for _ in range(10):
            joinCode = accounts.new_join_code()
            if not self.org_by_code(joinCode):
                break
        else:
            return None, "Could not make a join code. Please try again."

        self._run("INSERT INTO orgs (id, name, joinCode, createdAt) VALUES (?,?,?,?)",
                  (orgId, name.strip(), joinCode, now_text()))
        self._run("INSERT INTO teachers (id, orgId, username, passwordHash, createdAt)"
                  " VALUES (?,?,?,?,?)",
                  (teacherId, orgId, username.strip(),
                   accounts.hash_password(password), now_text()))
        return self.org(orgId), ""

    def org(self, orgId):
        return self._one("SELECT * FROM orgs WHERE id = ?", (orgId,))

    def org_by_code(self, joinCode):
        return self._one("SELECT * FROM orgs WHERE joinCode = ?", (joinCode,))

    # ---------- teachers ----------

    def teacher_by_username(self, username):
        return self._one("SELECT * FROM teachers WHERE username = ?", ((username or "").strip(),))

    def teacher(self, teacherId):
        return self._one("SELECT * FROM teachers WHERE id = ?", (teacherId,))

    def sign_in_teacher(self, username, password):
        found = self.teacher_by_username(username)
        if not found or not accounts.check_password(password, found["passwordHash"]):
            return None
        return found

    # ---------- sheets ----------

    def add_sheet(self, sheetId, orgId, fileName, savedAs, keyColumn):
        self._run("INSERT INTO sheets (id, orgId, fileName, savedAs, keyColumn, uploadedAt)"
                  " VALUES (?,?,?,?,?,?)",
                  (sheetId, orgId, fileName, savedAs, keyColumn, now_text()))
        return self.sheet(sheetId)

    def sheet(self, sheetId):
        return self._one("SELECT * FROM sheets WHERE id = ?", (sheetId,))

    def sheets_for_org(self, orgId):
        return self._all("SELECT * FROM sheets WHERE orgId = ? ORDER BY uploadedAt DESC, fileName",
                         (orgId,))

    def all_sheets(self):
        return self._all("SELECT * FROM sheets")

    def remove_sheet(self, sheetId):
        self._run("DELETE FROM sheets WHERE id = ?", (sheetId,))

    # ---------- students ----------

    def student_in_org(self, orgId, keyValue):
        return self._one("SELECT * FROM students WHERE orgId = ? AND keyValue = ?",
                         (orgId, tidy_key(keyValue)))

    def student(self, studentId):
        return self._one("SELECT * FROM students WHERE id = ?", (studentId,))

    """
        enrolling the student an invite link stands for.

        the link is the proof: it was handed to them by whoever holds the sheet.
        an organisation and a roll number are all that is kept, so the account
        still finds them on a sheet uploaded later
    """
    def enrol_student(self, orgId, keyValue, displayName, password):
        if self.student_in_org(orgId, keyValue):
            return None, "That student has already set a password. Sign in instead."
        studentId = accounts.new_id()
        self._run("INSERT INTO students (id, orgId, keyValue, displayName, passwordHash, createdAt)"
                  " VALUES (?,?,?,?,?,?)",
                  (studentId, orgId, tidy_key(keyValue), displayName,
                   accounts.hash_password(password), now_text()))
        return self.student(studentId), ""

    def sign_in_student(self, orgId, keyValue, password):
        found = self.student_in_org(orgId, keyValue)
        if not found or not accounts.check_password(password, found["passwordHash"]):
            return None
        return found
