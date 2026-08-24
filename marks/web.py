""" 
    a small web app for handing out marks.

    an organisation is made by whoever runs it, who becomes its teacher. the
    teacher uploads mark sheets and gets one invite link per student. a student
    opens their invite, sets a password, and from then on signs in to see their
    marks on every sheet the organisation uploads.

    run it with:  python3 -m marks.web [port]
    then open the address it prints. CSV needs nothing installed; Excel needs
    openpyxl, which is in requirements.txt
"""
import email.parser
import email.policy
import html
import http.cookies
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import accounts
from . import database
from . import links
from . import loaders
from marks import sheet as sheet_module

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(PROJECT_DIR, "uploads")
DATABASE_NAME = "marks.db"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_FORM_BYTES = 64 * 1024
# what a person is allowed to upload; anything else is refused with an explanation
ALLOWED_SUFFIXES = (".csv", ".xlsx", ".xlsm")
SESSION_COOKIE = "marks_session"

STYLE = """
:root { --ink:#1b1b1f; --paper:#fdfdfb; --card:#fff; --line:#dcdce2; --soft:#6b6b76;
        --accent:#2f5fd0; --warn:#8a5a00; --warnbg:#fdf3e0; --good:#1d6b3f; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e9e9ee; --paper:#141418; --card:#1c1c22; --line:#33333c; --soft:#a0a0ac;
          --accent:#8fb0ff; --warn:#e8c07a; --warnbg:#2a2216; --good:#7fd0a0; }
}
* { box-sizing:border-box; }
body { margin:0; padding:0 1.25rem 4rem; background:var(--paper); color:var(--ink);
       font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:50rem; margin:0 auto; }
nav { max-width:50rem; margin:0 auto; padding:1.1rem 0; display:flex; gap:1rem; align-items:baseline;
      border-bottom:1px solid var(--line); margin-bottom:2.2rem; flex-wrap:wrap; }
nav .who { font-weight:600; }
nav .rest { margin-left:auto; display:flex; gap:1rem; align-items:baseline; }
nav form { display:inline; }
nav button.link { background:none; border:0; color:var(--accent); padding:0; margin:0;
                  font:inherit; cursor:pointer; text-decoration:underline; }
h1 { font-size:1.6rem; margin:2rem 0 .3rem; }
h2 { font-size:1.05rem; margin:2rem 0 .7rem; font-weight:600; }
h3 { font-size:.95rem; margin:0 0 .5rem; font-weight:600; }
.sub { color:var(--soft); margin:0 0 2rem; font-size:.94rem; }
a { color:var(--accent); }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1.25rem;
        margin-bottom:1.25rem; }
.fields { display:grid; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr)); gap:.85rem; }
.stack { display:grid; gap:.85rem; }
label { display:block; font-size:.85rem; color:var(--soft); margin-bottom:.25rem; }
input { width:100%; padding:.55rem .65rem; border:1px solid var(--line); border-radius:6px;
        background:var(--paper); color:var(--ink); font:inherit; }
input[type=file] { padding:.45rem; }
button { margin-top:1rem; padding:.6rem 1.1rem; border:0; border-radius:6px; background:var(--accent);
         color:#fff; font:inherit; cursor:pointer; }
button.small { margin:0; padding:.3rem .6rem; font-size:.8rem; background:transparent;
               color:var(--accent); border:1px solid var(--line); }
button.small:hover { border-color:var(--accent); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; width:100%; margin-top:.5rem; }
th,td { text-align:left; padding:.5rem .6rem; border-bottom:1px solid var(--line); }
th { color:var(--soft); font-weight:600; font-size:.85rem; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
tr.totals td { font-weight:600; border-bottom:0; }
td.link { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.78rem;
          word-break:break-all; }
td.act { text-align:right; white-space:nowrap; }
.note { color:var(--soft); font-size:.9rem; }
.warn { color:#b3261e; }
@media (prefers-color-scheme: dark) { .warn { color:#ffb4ab; } }
.banner { background:var(--warnbg); border:1px solid var(--line); border-left:3px solid var(--warn);
          border-radius:6px; padding:.8rem 1rem; margin:0 0 1.5rem; font-size:.9rem; }
.code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:1.5rem;
        letter-spacing:.12em; font-weight:600; }
.who-line { margin:.2rem 0 0; color:var(--soft); font-size:.94rem; }
textarea { width:100%; min-height:7rem; margin-top:.5rem; padding:.6rem; font-size:.78rem;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace; border:1px solid var(--line);
           border-radius:6px; background:var(--paper); color:var(--ink); }
.two { display:grid; grid-template-columns:repeat(auto-fit,minmax(17rem,1fr)); gap:1.25rem; }
.two .card { margin:0; }
"""

# copying a link without having to select it by hand
COPY_SCRIPT = """
document.addEventListener('click', function (event) {
  var button = event.target.closest('[data-copy]');
  if (!button) return;
  var text = button.getAttribute('data-copy');
  var done = function () { var was = button.textContent; button.textContent = 'Copied';
                           setTimeout(function () { button.textContent = was; }, 1200); };
  if (navigator.clipboard) { navigator.clipboard.writeText(text).then(done, function () {}); }
});
"""

def escape(value):
    return html.escape(str(value))

def page(title, body, nav="", withScript=False):
    script = f"<script>{COPY_SCRIPT}</script>" if withScript else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{STYLE}</style></head>
<body>{nav}<main>{body}</main>{script}</body></html>"""

def signed_in_nav(who, where):
    return f"""<nav><span class="who">{escape(who)}</span>
<span class="note">{escape(where)}</span>
<span class="rest"><form action="/signout" method="post">
<button type="submit" class="link">Sign out</button></form></span></nav>"""

def message_html(message, isError=False):
    if not message:
        return ""
    return f'<p class="note {"warn" if isError else ""}">{escape(message)}</p>'

# ---------- what the server is holding ----------

# how a sheet is stored on disk, so its id survives a restart along with it
def saved_name(sheetId, fileName):
    return f"{sheetId}__{fileName}"

def split_saved(name):
    sheetId, separator, original = name.partition("__")
    if not separator or not links.is_sheet_id(sheetId):
        return None, None
    return sheetId, original

class Store:
    """ 
        the database of who is who, and the mark sheets themselves held in
        memory. sheets belong to an organisation, so one never shows up in
        another's pages
    """
    def __init__(self, directory=None):
        self.directory = directory or UPLOAD_DIR
        os.makedirs(self.directory, exist_ok=True)
        self.db = database.Database(os.path.join(self.directory, DATABASE_NAME))
        self.sheets = {}                      # sheet id -> Sheet
        self.students = {}                    # invite token -> (sheet id, row position)
        self._secret = None

    def close(self):
        self.db.close()

    @property
    def secret(self):
        if self._secret is None:
            self._secret = links.read_secret(self.directory)
        return self._secret

    def token_for(self, sheetId, position):
        return links.student_token(self.secret, sheetId, position)

    def path_for(self, savedAs):
        return os.path.join(self.directory, savedAs)

    # reading a file in and giving every row on it an invite of its own
    def hold(self, sheetId, filePath, fileName=""):
        table = loaders.load_table(filePath)
        sheet = sheet_module.from_table(table, fileName or os.path.basename(filePath))
        self.sheets[sheetId] = sheet
        for position in range(len(sheet.rows)):
            self.students[self.token_for(sheetId, position)] = (sheetId, position)
        return sheet

    def forget(self, sheetId):
        self.sheets.pop(sheetId, None)
        self.students = {token: where for token, where in self.students.items()
                         if where[0] != sheetId}

    def sheet(self, sheetId):
        return self.sheets.get(sheetId)

    # the one row an invite link stands for, along with the sheet it came from
    def invited(self, token):
        sheetId, position = self.students.get(token, (None, None))
        sheet = self.sheets.get(sheetId) if sheetId else None
        if sheet is None or position >= len(sheet.rows):
            return None, None, None
        return sheetId, sheet, sheet.rows[position]

    # reading back in every sheet the database still knows about
    def load_saved(self):
        restored = 0
        for record in self.db.all_sheets():
            path = self.path_for(record["savedAs"])
            if not os.path.exists(path):
                continue
            try:
                self.hold(record["id"], path, record["fileName"])
                restored += 1
            except Exception:
                continue                      # a file we can no longer read is left alone
        return restored

# keeping an uploaded name from escaping the uploads folder
def safe_name(fileName):
    fileName = os.path.basename(fileName or "").strip().replace("\\", "")
    cleaned = "".join(character for character in fileName
                      if character.isalnum() or character in "._- ")
    return cleaned or "sheet.csv"

""" 
    pulling the fields and the file out of an upload.
    the email parser understands the multipart format a browser sends
"""
def parse_upload(contentType, body):
    raw = (b"Content-Type: " + contentType.encode("utf-8") +
           b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    message = email.parser.BytesParser(policy=email.policy.default).parsebytes(raw)

    fields, files = {}, {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True) or b""
        fileName = part.get_filename()
        if fileName:
            files[name] = (fileName, payload)
        else:
            fields[name] = payload.decode("utf-8", "replace")
    return fields, files

# ---------- pages ----------

def landing(message="", isError=False):
    return page("Marks", f"""<h1>Marks</h1>
<p class="sub">Somewhere for a school, a class or a coaching centre to hand out results,
where each student sees only their own.</p>
{message_html(message, isError)}
<div class="two">
  <div class="card">
    <h3>I run an organisation</h3>
    <p class="note">Make one, upload a mark sheet, and hand each student their invite.</p>
    <p style="margin-top:1rem"><a href="/org/new">Create an organisation</a><br>
    <a href="/signin">Sign in as a teacher</a></p>
  </div>
  <div class="card">
    <h3>I am a student</h3>
    <p class="note">Open the invite link you were given to set a password. After that,
    sign in with your organisation's join code and your roll number.</p>
    <p style="margin-top:1rem"><a href="/signin">Sign in</a></p>
  </div>
</div>""")

def org_form(values=None, message="", isError=False):
    values = values or {}
    return page("Create an organisation", f"""<h1>Create an organisation</h1>
<p class="sub">You will be its teacher. Students join with a code this gives you.</p>
<div class="card">
  <form action="/org/new" method="post" class="stack">
    <div><label for="orgName">Organisation name</label>
      <input id="orgName" name="orgName" value="{escape(values.get("orgName", ""))}"
             placeholder="Springfield High" required></div>
    <div><label for="username">Your teacher name</label>
      <input id="username" name="username" value="{escape(values.get("username", ""))}"
             autocomplete="username" required></div>
    <div><label for="password">Password ({escape(accounts.PASSWORD_RULE)})</label>
      <input id="password" name="password" type="password" autocomplete="new-password" required></div>
    <div><label for="again">Password again</label>
      <input id="again" name="again" type="password" autocomplete="new-password" required></div>
    <div><button type="submit">Create it</button></div>
  </form>
  {message_html(message, isError)}
</div>
<p class="note"><a href="/">Back</a></p>""")

def signin_page(values=None, message="", isError=False):
    values = values or {}
    return page("Sign in", f"""<h1>Sign in</h1>
{message_html(message, isError)}
<div class="two">
  <div class="card">
    <h3>Teacher</h3>
    <form action="/signin/teacher" method="post" class="stack">
      <div><label for="tu">Teacher name</label>
        <input id="tu" name="username" value="{escape(values.get("username", ""))}"
               autocomplete="username" required></div>
      <div><label for="tp">Password</label>
        <input id="tp" name="password" type="password" autocomplete="current-password" required></div>
      <div><button type="submit">Sign in</button></div>
    </form>
  </div>
  <div class="card">
    <h3>Student</h3>
    <form action="/signin/student" method="post" class="stack">
      <div><label for="sc">Join code</label>
        <input id="sc" name="joinCode" value="{escape(values.get("joinCode", ""))}"
               placeholder="ABCD-2345" autocomplete="off" required></div>
      <div><label for="sk">Your roll number</label>
        <input id="sk" name="keyValue" value="{escape(values.get("keyValue", ""))}"
               autocomplete="off" required></div>
      <div><label for="sp">Password</label>
        <input id="sp" name="password" type="password" autocomplete="current-password" required></div>
      <div><button type="submit">Sign in</button></div>
    </form>
    <p class="note" style="margin-top:.8rem">No password yet? Open the invite link your
    teacher gave you.</p>
  </div>
</div>
<p class="note"><a href="/">Back</a></p>""")

# who a row is about, in one readable line
def describe(sheet, row):
    parts = [value for _, value in sheet_module.identity_of(sheet, row) if value]
    return " ".join(parts) or "(unnamed)"

def marks_table(sheet, row, heading="Your marks"):
    marks = sheet_module.marks_for(sheet, row)
    subjects = [(column, value) for column, value in marks
                if column not in sheet.summaryColumns]
    sheetTotals = [(column, value) for column, value in marks
                   if column in sheet.summaryColumns]

    rows = "".join(
        f"<tr><td>{escape(subject)}</td><td class='num'>{escape(value) or '&mdash;'}</td></tr>"
        for subject, value in subjects
    )

    """ 
        a sheet that already works out its own totals gets to keep them;
        only a sheet without any has them worked out here
    """
    if sheetTotals:
        rows += "".join(
            f"<tr class='totals'><td>{escape(column)}</td>"
            f"<td class='num'>{escape(value) or '&mdash;'}</td></tr>"
            for column, value in sheetTotals
        )
    else:
        total, average = sheet_module.total_and_average(subjects)
        if total is not None:
            rows += (f"<tr class='totals'><td>Total</td><td class='num'>{escape(total)}</td></tr>"
                     f"<tr class='totals'><td>Average</td><td class='num'>{average:.1f}</td></tr>")

    who = " &middot; ".join(f"{escape(column)}: <strong>{escape(value)}</strong>"
                            for column, value in sheet_module.identity_of(sheet, row) if value)
    return f"""<h2>{escape(heading)}</h2>
<p class="who-line">{who}</p>
<div class="card" style="margin-top:.75rem">
<div class="scroll">
<table><thead><tr><th>Subject</th><th class="num">Mark</th></tr></thead><tbody>{rows}</tbody></table>
</div></div>"""

def teacher_home(store, org, teacher, message="", isError=False):
    records = store.db.sheets_for_org(org["id"])
    listing = "".join(
        f'<tr><td><a href="/teacher/sheet/{escape(record["id"])}">{escape(record["fileName"])}</a></td>'
        f'<td class="note">{len(store.sheet(record["id"]).rows) if store.sheet(record["id"]) else 0}'
        f' student(s)</td>'
        f'<td class="note">recognised by {escape(record["keyColumn"])}</td></tr>'
        for record in records) or \
        '<tr><td colspan="3" class="note">Nothing uploaded yet.</td></tr>'

    return page(f"{org['name']} &mdash; marks", f"""<h1>{escape(org["name"])}</h1>
<p class="sub">Signed in as <strong>{escape(teacher["username"])}</strong>.</p>

<div class="card">
  <h3>Your join code</h3>
  <p class="note">Students type this when they sign in. It is safe to put on a board &mdash;
  it does not on its own let anybody see a mark.</p>
  <p class="code">{escape(org["joinCode"])}</p>
</div>

<div class="card">
  <h3>Upload a mark sheet</h3>
  <p class="note">One row per student, one column per subject. CSV or Excel.</p>
  <form action="/teacher/upload" method="post" enctype="multipart/form-data">
    <input id="sheet" type="file" name="sheet" style="margin-top:.6rem"
           accept=".csv,.xlsx,.xlsm,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
           required>
    <button type="submit">Upload</button>
  </form>
  {message_html(message, isError)}
</div>

<h2>Sheets in this organisation</h2>
<div class="card">
  <div class="scroll"><table><tbody>{listing}</tbody></table></div>
</div>""", signed_in_nav(teacher["username"], org["name"]))

# the table of invites the teacher hands out
def invite_table(store, sheet, sheetId, baseUrl):
    rows, plain = [], []
    for position, row in enumerate(sheet.rows):
        address = f"{baseUrl}/s/{store.token_for(sheetId, position)}"
        rows.append(
            f"<tr><td>{escape(describe(sheet, row))}</td>"
            f"<td class='link'>{escape(address)}</td>"
            f"<td class='act'><button type='button' class='small' "
            f"data-copy='{escape(address)}'>Copy</button></td></tr>")
        plain.append(f"{describe(sheet, row)}\t{address}")

    return f"""<h2>One invite per student</h2>
<p class="note">Send each student their own line. Opening it shows their marks and lets
them set a password; after that they sign in with the join code instead.</p>
<div class="card" style="margin-top:.75rem">
<div class="scroll">
<table><thead><tr><th>Student</th><th>Their invite</th><th></th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</div>
<h2>All of them at once</h2>
<p class="note">Paste this into a spreadsheet or a mail merge.</p>
<textarea readonly aria-label="Every student and their invite">{escape(chr(10).join(plain))}</textarea>
</div>"""

def lookup_form(sheet, sheetId, values=None, message="", isError=False):
    values = values or {}
    boxes = "".join(
        f'<div><label for="f{position}">{escape(column)}</label>'
        f'<input id="f{position}" name="{escape(column)}" value="{escape(values.get(column, ""))}" '
        f'autocomplete="off"></div>'
        for position, column in enumerate(sheet.identityColumns)
    )
    return f"""<h2>Find one student</h2>
<div class="card">
  <form action="/teacher/sheet/{escape(sheetId)}/lookup" method="get">
    <div class="fields">{boxes}</div>
    <button type="submit">Show their marks</button>
  </form>
  {message_html(message, isError)}
</div>"""

def sheet_page(store, org, teacher, sheet, sheetId, record, baseUrl,
               found="", message="", isError=False, values=None):
    return page(f"{sheet.fileName} &mdash; invites", f"""<h1>{escape(sheet.fileName)}</h1>
<p class="sub">{len(sheet.rows)} student(s) &middot; subjects:
{escape(", ".join(sheet.markColumns))} &middot; students recognised by
<strong>{escape(record["keyColumn"])}</strong></p>
<p class="banner"><strong>This page shows every student.</strong> Keep the address to
yourself &mdash; hand out the invites below instead.</p>
{lookup_form(sheet, sheetId, values, message, isError)}
{found}
{invite_table(store, sheet, sheetId, baseUrl)}
<p class="note"><a href="/teacher">Back to {escape(org["name"])}</a></p>""",
                signed_in_nav(teacher["username"], org["name"]), withScript=True)

# the page an invite link leads to: the student's marks, and a password to set
def invite_page(store, org, sheet, row, token, alreadyEnrolled, message="", isError=False):
    if alreadyEnrolled:
        setup = f"""<div class="card">
  <h3>You already have a password</h3>
  <p class="note">Sign in with join code <strong>{escape(org["joinCode"])}</strong>
  and your roll number.</p>
  {message_html(message, isError)}
  <p style="margin-top:.8rem"><a href="/signin">Sign in</a></p>
</div>"""
    else:
        setup = f"""<div class="card">
  <h3>Set a password</h3>
  <p class="note">Then you can sign in without this link, and see every sheet
  {escape(org["name"])} uploads.</p>
  <form action="/s/{escape(token)}/enrol" method="post" class="stack" style="margin-top:.8rem">
    <div><label for="p1">Password ({escape(accounts.PASSWORD_RULE)})</label>
      <input id="p1" name="password" type="password" autocomplete="new-password" required></div>
    <div><label for="p2">Password again</label>
      <input id="p2" name="again" type="password" autocomplete="new-password" required></div>
    <div><button type="submit">Set it</button></div>
  </form>
  {message_html(message, isError)}
</div>"""

    return page("Your marks", f"""<h1>Your marks</h1>
<p class="sub">From <strong>{escape(sheet.fileName)}</strong> at
<strong>{escape(org["name"])}</strong>. This page is yours alone &mdash; it holds no one
else's results.</p>
{marks_table(sheet, row)}
{setup}""")

def student_home(store, org, student):
    pieces = []
    for record in store.db.sheets_for_org(org["id"]):
        sheet = store.sheet(record["id"])
        if sheet is None:
            continue
        matched = sheet_module.rows_for_key(sheet, record["keyColumn"], student["keyValue"])
        for row in matched:
            pieces.append(marks_table(sheet, row, record["fileName"]))

    if not pieces:
        pieces.append('<div class="card"><p class="note">Nothing has been uploaded for you '
                      'yet. Check back after your next results are published.</p></div>')

    return page("Your marks", f"""<h1>Your marks</h1>
<p class="sub">Everything {escape(org["name"])} has published for you.</p>
{''.join(pieces)}""", signed_in_nav(student["displayName"], org["name"]))

def not_found(what="page"):
    return page("Not found", f"""<h1>Not found</h1>
<p class="sub">That {escape(what)} doesn't exist here. It may have been a typo, or it may
have been removed.</p><p><a href="/">Start again</a></p>""")

def not_allowed():
    return page("Sign in first", """<h1>Sign in first</h1>
<p class="sub">That page belongs to somebody's account.</p>
<p><a href="/signin">Sign in</a></p>""")

"""
    the address the invites are written with.
    it comes from the request, so a link works from whatever name the server was
    reached by, and is trimmed to host characters because the header is not ours
"""
def base_url(handler):
    host = handler.headers.get("Host") or ""
    host = "".join(character for character in host
                   if character.isalnum() or character in ".-:[]")
    if not host:
        host = f"127.0.0.1:{handler.server.server_address[1]}"
    return f"http://{host}"

def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *arguments):
            pass

        # ---------- plumbing ----------

        def reply(self, status, markup, cookie=None):
            encoded = markup.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            # an invite link should not travel to anywhere the student clicks next
            self.send_header("Referrer-Policy", "no-referrer")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(encoded)

        def go_to(self, address, cookie=None):
            self.send_response(303)
            self.send_header("Location", address)
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()

        """ 
            the cookie a signed-in browser carries.

            HttpOnly keeps it away from scripts and SameSite keeps another site
            from posting with it. Secure is not set because this serves plain
            HTTP; behind HTTPS it should be
        """
        def set_session(self, kind, personId, orgId):
            value = accounts.make_session(store.secret, kind, personId, orgId)
            return (f"{SESSION_COOKIE}={value}; Path=/; HttpOnly; SameSite=Lax; "
                    f"Max-Age={accounts.SESSION_SECONDS}")

        def clear_session(self):
            return f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"

        def session(self):
            jar = http.cookies.SimpleCookie()
            try:
                jar.load(self.headers.get("Cookie", ""))
            except http.cookies.CookieError:
                return None
            held = jar.get(SESSION_COOKIE)
            return accounts.read_session(store.secret, held.value) if held else None

        # the teacher this request belongs to, and the organisation they run
        def as_teacher(self):
            found = self.session()
            if not found or found.get("kind") != "teacher":
                return None, None
            teacher = store.db.teacher(found.get("id"))
            return (teacher, store.db.org(teacher["orgId"])) if teacher else (None, None)

        def as_student(self):
            found = self.session()
            if not found or found.get("kind") != "student":
                return None, None
            student = store.db.student(found.get("id"))
            return (student, store.db.org(student["orgId"])) if student else (None, None)

        def form(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_FORM_BYTES:
                return {}
            raw = self.rfile.read(length).decode("utf-8", "replace")
            return {key: values[0] for key, values
                    in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

        # ---------- reading ----------

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            parts = [piece for piece in parsed.path.split("/") if piece]

            if not parts:
                self.reply(200, landing())
                return

            if parts == ["org", "new"]:
                self.reply(200, org_form())
                return

            if parts == ["signin"]:
                self.reply(200, signin_page())
                return

            # an invite: no account needed, and it shows one row only
            if len(parts) == 2 and parts[0] == "s":
                self.show_invite(parts[1])
                return

            if parts == ["me"]:
                student, org = self.as_student()
                if not student:
                    self.reply(403, not_allowed())
                    return
                self.reply(200, student_home(store, org, student))
                return

            if parts and parts[0] == "teacher":
                self.teacher_get(parts, parsed)
                return

            self.reply(404, not_found())

        def show_invite(self, token, message="", isError=False):
            sheetId, sheet, row = store.invited(token)
            if sheet is None:
                self.reply(404, not_found("invite"))
                return
            record = store.db.sheet(sheetId)
            org = store.db.org(record["orgId"]) if record else None
            if org is None:
                self.reply(404, not_found("invite"))
                return
            keyValue = sheet_module.cell(row, record["keyColumn"])
            enrolled = store.db.student_in_org(org["id"], keyValue) is not None
            self.reply(200, invite_page(store, org, sheet, row, token, enrolled, message, isError))

        def teacher_get(self, parts, parsed):
            teacher, org = self.as_teacher()
            if not teacher:
                self.reply(403, not_allowed())
                return

            if parts == ["teacher"]:
                self.reply(200, teacher_home(store, org, teacher))
                return

            if len(parts) in (3, 4) and parts[1] == "sheet":
                record = store.db.sheet(parts[2])
                sheet = store.sheet(parts[2])
                # a sheet belonging to another organisation is simply not there
                if record is None or sheet is None or record["orgId"] != org["id"]:
                    self.reply(404, not_found("sheet"))
                    return

                if len(parts) == 3:
                    self.reply(200, sheet_page(store, org, teacher, sheet, parts[2], record,
                                               base_url(self)))
                    return

                if parts[3] == "lookup":
                    fields = urllib.parse.parse_qs(parsed.query)
                    criteria = {column: fields.get(column, [""])[0]
                                for column in sheet.identityColumns}
                    self.reply(200, self.lookup_result(org, teacher, sheet, parts[2], record,
                                                       criteria))
                    return

            self.reply(404, not_found())

        def lookup_result(self, org, teacher, sheet, sheetId, record, criteria):
            show = lambda found, message, isError: sheet_page(
                store, org, teacher, sheet, sheetId, record, base_url(self),
                found, message, isError, criteria)

            filled = {column: value for column, value in criteria.items() if value.strip()}
            if not filled:
                return show("", "Fill in at least one box so we know who to look for.", True)

            matched = sheet_module.find(sheet, criteria)
            if not matched:
                described = ", ".join(f"{column} {value}" for column, value in filled.items())
                return show("", f"No student found for {described}.", True)

            """ 
                more than one student matches, so no marks are shown; asking for
                more detail avoids showing someone else's results
            """
            if len(matched) > 1:
                return show("", f"{len(matched)} students match that. Please fill in more "
                                "boxes to narrow it down.", True)

            return show(marks_table(sheet, matched[0]), "", False)

        # ---------- writing ----------

        def do_POST(self):
            parts = [piece for piece in urllib.parse.urlparse(self.path).path.split("/") if piece]

            if parts == ["org", "new"]:
                self.create_org()
            elif parts == ["signin", "teacher"]:
                self.sign_in_teacher()
            elif parts == ["signin", "student"]:
                self.sign_in_student()
            elif parts == ["signout"]:
                self.go_to("/", self.clear_session())
            elif len(parts) == 3 and parts[0] == "s" and parts[2] == "enrol":
                self.enrol(parts[1])
            elif parts == ["teacher", "upload"]:
                self.upload()
            else:
                self.reply(404, not_found())

        def create_org(self):
            fields = self.form()
            orgName = (fields.get("orgName") or "").strip()
            username = (fields.get("username") or "").strip()
            kept = {"orgName": orgName, "username": username}

            if not orgName or not username:
                self.reply(400, org_form(kept, "Please fill in a name for both.", True))
                return

            problem = accounts.password_problem(fields.get("password", ""), fields.get("again", ""))
            if problem:
                self.reply(400, org_form(kept, problem, True))
                return

            org, complaint = store.db.create_org(orgName, username, fields["password"])
            if org is None:
                self.reply(400, org_form(kept, complaint, True))
                return

            teacher = store.db.teacher_by_username(username)
            self.go_to("/teacher", self.set_session("teacher", teacher["id"], org["id"]))

        def sign_in_teacher(self):
            fields = self.form()
            teacher = store.db.sign_in_teacher(fields.get("username", ""),
                                               fields.get("password", ""))
            if not teacher:
                # the same words either way, so a wrong name and a wrong password look alike
                self.reply(400, signin_page({"username": fields.get("username", "")},
                                            "That teacher name and password do not match.", True))
                return
            self.go_to("/teacher", self.set_session("teacher", teacher["id"], teacher["orgId"]))

        def sign_in_student(self):
            fields = self.form()
            kept = {"joinCode": fields.get("joinCode", ""), "keyValue": fields.get("keyValue", "")}
            org = store.db.org_by_code(accounts.tidy_join_code(fields.get("joinCode", "")))
            student = store.db.sign_in_student(org["id"], fields.get("keyValue", ""),
                                               fields.get("password", "")) if org else None
            if not student:
                self.reply(400, signin_page(
                    kept, "That join code, roll number and password do not match.", True))
                return
            self.go_to("/me", self.set_session("student", student["id"], student["orgId"]))

        # setting a password on an invite, which is what makes an account
        def enrol(self, token):
            fields = self.form()
            problem = accounts.password_problem(fields.get("password", ""), fields.get("again", ""))
            if problem:
                self.show_invite(token, problem, True)
                return

            sheetId, sheet, row = store.invited(token)
            if sheet is None:
                self.reply(404, not_found("invite"))
                return
            record = store.db.sheet(sheetId)
            org = store.db.org(record["orgId"]) if record else None
            if org is None:
                self.reply(404, not_found("invite"))
                return

            keyValue = sheet_module.cell(row, record["keyColumn"])
            if not keyValue.strip():
                self.show_invite(token, "This row has no roll number, so an account cannot "
                                        "be tied to it. Ask your teacher.", True)
                return

            student, complaint = store.db.enrol_student(
                org["id"], keyValue, describe(sheet, row), fields["password"])
            if student is None:
                self.show_invite(token, complaint, True)
                return
            self.go_to("/me", self.set_session("student", student["id"], org["id"]))

        def upload(self):
            teacher, org = self.as_teacher()
            if not teacher:
                self.reply(403, not_allowed())
                return

            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD_BYTES:
                self.reply(413, teacher_home(
                    store, org, teacher,
                    f"That file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.", True))
                return

            _, files = parse_upload(self.headers.get("Content-Type", ""), self.rfile.read(length))
            uploaded = files.get("sheet")
            complain = lambda words: self.reply(400, teacher_home(store, org, teacher, words, True))

            if not uploaded or not uploaded[1]:
                complain("Please choose a file first.")
                return

            fileName, contents = uploaded
            if not fileName.lower().endswith(ALLOWED_SUFFIXES):
                complain("That file type isn't read. Please upload a "
                         f"{' or a '.join(ALLOWED_SUFFIXES)} file.")
                return

            cleanName = safe_name(fileName)
            sheetId = links.new_sheet_id()
            savedAs = saved_name(sheetId, cleanName)
            savedPath = store.path_for(savedAs)
            with open(savedPath, "wb") as savedFile:
                savedFile.write(contents)

            def drop():
                store.forget(sheetId)
                store.db.remove_sheet(sheetId)
                if os.path.exists(savedPath):
                    os.remove(savedPath)

            try:
                sheet = store.hold(sheetId, savedPath, cleanName)
            except Exception as error:
                drop()
                complain(f"That file could not be read: {error}")
                return

            # a sheet with nobody on it has no invites to hand out, so it is dropped again
            if not sheet.rows:
                drop()
                complain("That sheet has no students in it.")
                return

            keyColumn = sheet_module.key_column(sheet)
            if not keyColumn:
                drop()
                complain("That sheet has no column naming the students.")
                return

            store.db.add_sheet(sheetId, org["id"], cleanName, savedAs, keyColumn)
            self.go_to(f"/teacher/sheet/{sheetId}")

    return Handler

# built separately from serve_forever so a test can drive it without a browser
def make_server(store, port=8000, host="127.0.0.1"):
    return HTTPServer((host, port), make_handler(store))

def main(arguments):
    port = int(arguments[0]) if arguments else 8000
    store = Store()
    restored = store.load_saved()

    server = make_server(store, port)
    if restored:
        print(f"{restored} sheet(s) uploaded earlier are still served, with the same invites")
    print(f"open http://127.0.0.1:{port}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        store.close()

if __name__ == "__main__":
    main(sys.argv[1:])
