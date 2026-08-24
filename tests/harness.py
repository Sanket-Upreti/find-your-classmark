""" 
    the shared parts of the web checks: a server on a throwaway folder, and a
    browser that keeps its cookies the way a real one does
"""
import http.cookiejar
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
from marks import web

class Skipped(Exception):
    """ raised by a check that can't run here, rather than failing it """

# excel checks only run when openpyxl is installed; csv must work without it
def needs_openpyxl():
    try:
        import openpyxl                     # noqa: F401
    except ImportError:
        raise Skipped("openpyxl is not installed")

def registry():
    checks = []
    def check(name):
        def keep(function):
            checks.append((name, function))
            return function
        return keep
    return checks, check

def run(checks):
    failures = skipped = 0
    for name, function in checks:
        try:
            function()
            print(f"  ok   {name}")
        except Skipped as reason:
            skipped += 1
            print(f"  skip {name} ({reason})")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error or 'assertion failed'}")
    passed = len(checks) - failures - skipped
    tail = f", {skipped} skipped" if skipped else ""
    print(f"\n{passed}/{len(checks) - skipped} checks passed{tail}")
    raise SystemExit(1 if failures else 0)

# ---------- sample sheets ----------

SHEET_CSV = ("roll,name,class,section,Maths,Science,English\n"
             "12,Sanket,10,A,72,65,80\n"
             "13,Mokshada,10,A,81,90,77\n"
             "14,Sanket,10,B,55,60,58\n")

TEACHER = {"orgName": "Springfield High", "username": "miss_hoover",
           "password": "longenough1", "again": "longenough1"}

def write_csv(contents=SHEET_CSV, name="results.csv"):
    path = os.path.join(tempfile.mkdtemp(), name)
    with open(path, "w") as handle:
        handle.write(contents)
    return path

# ---------- reading pages ----------

""" 
    only the marks table itself, so neither a number in the stylesheet nor two
    digits that happen to fall inside a link token can fool a check
"""
def results_section(markup, heading="Your marks"):
    marker = f"<h2>{heading}</h2>"
    if marker not in markup:
        return ""
    return markup.split(marker, 1)[1].split("</table>", 1)[0]

SHEET_ADDRESS = re.compile(r"/teacher/sheet/([0-9a-f]{16})")
INVITE_ADDRESS = re.compile(r"/s/([0-9a-f]{%d})" % links.TOKEN_LENGTH)
JOIN_CODE = re.compile(r'class="code">([A-Z0-9-]+)<')

def sheet_id(markup):
    found = SHEET_ADDRESS.search(markup)
    assert found, "that page is not a sheet page"
    return found.group(1)

def join_code(markup):
    found = JOIN_CODE.search(markup)
    assert found, "that page does not show a join code"
    return found.group(1)

# every invite on a page, in the order they appear, without repeats
def invites(markup):
    seen = []
    for token in INVITE_ADDRESS.findall(markup):
        if token not in seen:
            seen.append(token)
    return seen

# the warning a page is showing, on its own
def warning(markup):
    found = re.search(r'<p class="note warn">(.*?)</p>', markup, re.S)
    return found.group(1).strip() if found else ""

def headings(markup):
    return re.findall(r"<h2>(.*?)</h2>", markup)

# ---------- driving it ----------

class Browser:
    """ one person's browser: it keeps whatever cookie it was given """
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def _send(self, request):
        try:
            with self.opener.open(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

    def get(self, path):
        return self._send(urllib.request.Request(self.base + path))

    def post(self, path, fields):
        return self._send(urllib.request.Request(
            self.base + path, data=urllib.parse.urlencode(fields).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"}))

    # posting a file the way a browser's upload form does
    def upload(self, contents=SHEET_CSV, fileName="results.csv"):
        return self.upload_bytes(contents.encode(), fileName)

    def upload_bytes(self, contents, fileName="results.csv"):
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="sheet"; filename="{fileName}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n").encode() + contents + \
               f"\r\n--{boundary}--\r\n".encode()
        return self._send(urllib.request.Request(
            self.base + "/teacher/upload", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}))

    # signing up as a teacher and landing on the organisation's own page
    def start_org(self, **changes):
        fields = dict(TEACHER, **changes)
        status, markup = self.post("/org/new", fields)
        assert status == 200, f"could not create the organisation ({status})"
        return markup

class Serving:
    """ a server with its own folder and database, so a check touches no real data """
    def __enter__(self):
        self.folder = tempfile.mkdtemp()
        self.previousDir = web.UPLOAD_DIR
        web.UPLOAD_DIR = self.folder

        self.store = web.Store(self.folder)
        self.server = web.make_server(self.store, port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *details):
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        web.UPLOAD_DIR = self.previousDir
        shutil.rmtree(self.folder, ignore_errors=True)

    def browser(self):
        return Browser(self.base)

    # the common opening move: a teacher with an organisation and a sheet in it
    def teaching(self, contents=SHEET_CSV, fileName="results.csv"):
        teacher = self.browser()
        home = teacher.start_org()
        markup = teacher.upload(contents, fileName)[1]
        return teacher, join_code(home), sheet_id(markup), markup
