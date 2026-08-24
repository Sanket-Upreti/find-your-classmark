""" 
    a small web page for handing out marks.

    someone uploads a wide mark sheet, as CSV or Excel, and gets back one link
    per student. a student opens their own link and sees their own row, and no
    part of the page will show them anyone else's.

    run it with:  python3 -m marks.web [port]
    then open the address it prints. CSV needs nothing installed; Excel needs
    openpyxl, which is in requirements.txt
"""
import email.parser
import email.policy
import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import links
from . import loaders
from marks import sheet as sheet_module

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(PROJECT_DIR, "uploads")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
# what a person is allowed to upload; anything else is refused with an explanation
ALLOWED_SUFFIXES = (".csv", ".xlsx", ".xlsm")

STYLE = """
:root { --ink:#1b1b1f; --paper:#fdfdfb; --card:#fff; --line:#dcdce2; --soft:#6b6b76;
        --accent:#2f5fd0; --warn:#8a5a00; --warnbg:#fdf3e0; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e9e9ee; --paper:#141418; --card:#1c1c22; --line:#33333c; --soft:#a0a0ac;
          --accent:#8fb0ff; --warn:#e8c07a; --warnbg:#2a2216; }
}
* { box-sizing:border-box; }
body { margin:0; padding:2.5rem 1.25rem 4rem; background:var(--paper); color:var(--ink);
       font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:50rem; margin:0 auto; }
h1 { font-size:1.6rem; margin:0 0 .3rem; }
h2 { font-size:1.05rem; margin:2rem 0 .7rem; font-weight:600; }
.sub { color:var(--soft); margin:0 0 2rem; font-size:.94rem; }
a { color:var(--accent); }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1.25rem; }
.fields { display:grid; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr)); gap:.85rem; }
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
.banner strong { color:var(--ink); }
.who { margin:.2rem 0 0; color:var(--soft); font-size:.94rem; }
textarea { width:100%; min-height:7rem; margin-top:.5rem; padding:.6rem; font-size:.78rem;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace; border:1px solid var(--line);
           border-radius:6px; background:var(--paper); color:var(--ink); }
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

def page(title, body, withScript=False):
    script = f"<script>{COPY_SCRIPT}</script>" if withScript else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><main>{body}</main>{script}</body></html>"""

def escape(value):
    return html.escape(str(value))

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
        every sheet the server has been given, each under its own id.

        holding them separately is what stops a second upload replacing the
        sheet somebody else is still looking at
    """
    def __init__(self):
        self.sheets = {}                      # sheet id -> Sheet
        self.students = {}                    # student token -> (sheet id, row position)
        self._secret = None

    @property
    def secret(self):
        if self._secret is None:
            self._secret = links.read_secret(UPLOAD_DIR)
        return self._secret

    def token_for(self, sheetId, position):
        return links.student_token(self.secret, sheetId, position)

    # reading a file in and giving every row on it a link of its own
    def add(self, sheetId, filePath, fileName=""):
        table = loaders.load_table(filePath)
        sheet = sheet_module.from_table(table, fileName or os.path.basename(filePath))
        self.sheets[sheetId] = sheet
        for position in range(len(sheet.rows)):
            self.students[self.token_for(sheetId, position)] = (sheetId, position)
        return sheet

    def sheet(self, sheetId):
        return self.sheets.get(sheetId)

    # the one row a student's link stands for
    def student(self, token):
        sheetId, position = self.students.get(token, (None, None))
        sheet = self.sheets.get(sheetId) if sheetId else None
        if sheet is None or position >= len(sheet.rows):
            return None, None
        return sheet, sheet.rows[position]

    # picking up sheets uploaded on an earlier run, so a restart doesn't break the links
    def load_saved(self):
        if not os.path.isdir(UPLOAD_DIR):
            return 0
        restored = 0
        for name in sorted(os.listdir(UPLOAD_DIR)):
            sheetId, original = split_saved(name)
            if not sheetId or not original.lower().endswith(ALLOWED_SUFFIXES):
                continue
            try:
                self.add(sheetId, os.path.join(UPLOAD_DIR, name), original)
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

def upload_form(message="", isError=False):
    warning = f'<p class="note {"warn" if isError else ""}">{escape(message)}</p>' if message else ""
    return f"""<h1>Hand out marks</h1>
<p class="sub">Upload a mark sheet and get one link per student. One row per student,
one column per subject.</p>
<div class="card">
  <form action="/upload" method="post" enctype="multipart/form-data">
    <label for="sheet">Mark sheet (.csv or .xlsx)</label>
    <input id="sheet" type="file" name="sheet"
           accept=".csv,.xlsx,.xlsm,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
           required>
    <button type="submit">Upload</button>
  </form>
  {warning}
</div>"""

# who a row is about, in one readable line
def describe(sheet, row):
    parts = [value for _, value in sheet_module.identity_of(sheet, row) if value]
    return " &middot; ".join(escape(part) for part in parts) or "(unnamed)"

def marks_table(sheet, row):
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
    return f"""<h2>Your marks</h2>
<p class="who">{who}</p>
<div class="card" style="margin-top:.75rem">
<div class="scroll">
<table><thead><tr><th>Subject</th><th class="num">Mark</th></tr></thead><tbody>{rows}</tbody></table>
</div></div>"""

def lookup_form(sheet, sheetId, values=None, message="", isError=False):
    values = values or {}
    boxes = "".join(
        f'<div><label for="f{position}">{escape(column)}</label>'
        f'<input id="f{position}" name="{escape(column)}" value="{escape(values.get(column, ""))}" '
        f'autocomplete="off"></div>'
        for position, column in enumerate(sheet.identityColumns)
    )
    warning = f'<p class="note {"warn" if isError else ""}">{escape(message)}</p>' if message else ""
    return f"""<h2>Find one student</h2>
<div class="card">
  <form action="/sheet/{escape(sheetId)}/lookup" method="get">
    <div class="fields">{boxes}</div>
    <button type="submit">Show their marks</button>
  </form>
  {warning}
</div>"""

# the table of links the person who uploaded the sheet hands out
def link_table(store, sheet, sheetId, baseUrl):
    rows = []
    plain = []
    for position, row in enumerate(sheet.rows):
        address = f"{baseUrl}/s/{store.token_for(sheetId, position)}"
        rows.append(
            f"<tr><td>{describe(sheet, row)}</td>"
            f"<td class='link'>{escape(address)}</td>"
            f"<td class='act'><button type='button' class='small' "
            f"data-copy='{escape(address)}'>Copy</button></td></tr>")
        plain.append(f"{' '.join(value for _, value in sheet_module.identity_of(sheet, row) if value)}\t{address}")

    return f"""<h2>One link per student</h2>
<p class="note">Send each student their own line. Their link shows their row and nothing else.</p>
<div class="card" style="margin-top:.75rem">
<div class="scroll">
<table><thead><tr><th>Student</th><th>Their link</th><th></th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</div>
<h2>All of them at once</h2>
<p class="note">Paste this into a spreadsheet or a mail merge.</p>
<textarea readonly aria-label="Every student and their link">{escape(chr(10).join(plain))}</textarea>
</div>"""

def sheet_page(store, sheet, sheetId, baseUrl, found="", formMessage="", isError=False, values=None):
    return page(f"{sheet.fileName} &mdash; links", f"""<h1>Hand out marks</h1>
<p class="sub">{len(sheet.rows)} student(s) in <strong>{escape(sheet.fileName)}</strong> &middot;
subjects: {escape(", ".join(sheet.markColumns))}</p>
<p class="banner"><strong>This page shows every student.</strong> Keep the address to yourself &mdash;
hand out the links below instead.</p>
{lookup_form(sheet, sheetId, values, formMessage, isError)}
{found}
{link_table(store, sheet, sheetId, baseUrl)}
<p class="sub" style="margin-top:1.5rem"><a href="/upload">Upload a different sheet</a></p>""",
                withScript=True)

def lookup_result(store, sheet, sheetId, baseUrl, criteria):
    filled = {column: value for column, value in criteria.items() if value.strip()}

    if not filled:
        return sheet_page(store, sheet, sheetId, baseUrl, "",
                          "Fill in at least one box so we know who to look for.", True, criteria)

    matched = sheet_module.find(sheet, criteria)

    if not matched:
        described = ", ".join(f"{column} {value}" for column, value in filled.items())
        return sheet_page(store, sheet, sheetId, baseUrl, "",
                          f"No student found for {described}.", True, criteria)

    """ 
        more than one student matches, so no marks are shown; asking for more
        detail is both clearer and avoids showing someone else's results
    """
    if len(matched) > 1:
        return sheet_page(
            store, sheet, sheetId, baseUrl, "",
            f"{len(matched)} students match that. Please fill in more boxes to narrow it down.",
            True, criteria)

    return sheet_page(store, sheet, sheetId, baseUrl, marks_table(sheet, matched[0]),
                      "", False, criteria)

# the page a student reaches through their own link
def student_page(sheet, row):
    return page("Your marks", f"""<h1>Your marks</h1>
<p class="sub">From <strong>{escape(sheet.fileName)}</strong>. This page is yours alone &mdash;
it holds no one else's results.</p>
{marks_table(sheet, row)}""")

def not_found(what="page"):
    return page("Not found", f"""<h1>Not found</h1>
<p class="sub">That {escape(what)} doesn't exist here. It may have been a typo, or the sheet
may have been removed.</p><p><a href="/">Start again</a></p>""")

"""
    the address the links are written with.
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

        def reply(self, status, markup):
            encoded = markup.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            # a student's link should not travel to anywhere they click on next
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(encoded)

        def go_to(self, address):
            self.send_response(303)
            self.send_header("Location", address)
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            parts = [piece for piece in parsed.path.split("/") if piece]

            if not parts or parts == ["upload"]:
                self.reply(200, page("Hand out marks", upload_form()))
                return

            # a student's own link: their row, and no way to reach any other
            if len(parts) == 2 and parts[0] == "s":
                sheet, row = store.student(parts[1])
                if sheet is None:
                    self.reply(404, not_found("link"))
                    return
                self.reply(200, student_page(sheet, row))
                return

            if parts[0] == "sheet" and len(parts) in (2, 3):
                sheet = store.sheet(parts[1])
                if sheet is None:
                    self.reply(404, not_found("sheet"))
                    return

                if len(parts) == 2:
                    self.reply(200, sheet_page(store, sheet, parts[1], base_url(self)))
                    return

                if parts[2] == "lookup":
                    fields = urllib.parse.parse_qs(parsed.query)
                    criteria = {column: fields.get(column, [""])[0]
                                for column in sheet.identityColumns}
                    self.reply(200, lookup_result(store, sheet, parts[1], base_url(self), criteria))
                    return

            self.reply(404, not_found())

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/upload":
                self.reply(404, not_found())
                return

            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD_BYTES:
                self.reply(413, page("Too big", upload_form(
                    f"That file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.", True)))
                return

            _, files = parse_upload(self.headers.get("Content-Type", ""), self.rfile.read(length))
            uploaded = files.get("sheet")

            if not uploaded or not uploaded[1]:
                self.reply(400, page("No file", upload_form("Please choose a file first.", True)))
                return

            fileName, contents = uploaded
            if not fileName.lower().endswith(ALLOWED_SUFFIXES):
                self.reply(400, page("Not a sheet", upload_form(
                    "That file type isn't read. Please upload a "
                    f"{' or a '.join(ALLOWED_SUFFIXES)} file.", True)))
                return

            cleanName = safe_name(fileName)
            sheetId = links.new_sheet_id()
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            savedPath = os.path.join(UPLOAD_DIR, saved_name(sheetId, cleanName))
            with open(savedPath, "wb") as savedFile:
                savedFile.write(contents)

            try:
                sheet = store.add(sheetId, savedPath, cleanName)
            except Exception as error:
                os.remove(savedPath)
                self.reply(400, page("Could not read", upload_form(
                    f"That file could not be read: {error}", True)))
                return

            # a sheet with nobody on it has no links to hand out, so it is dropped again
            if not sheet.rows:
                self.forget(sheetId, savedPath)
                self.reply(400, page("Empty", upload_form("That sheet has no students in it.", True)))
                return

            self.go_to(f"/sheet/{sheetId}")

        def forget(self, sheetId, savedPath):
            store.sheets.pop(sheetId, None)
            store.students = {token: where for token, where in store.students.items()
                              if where[0] != sheetId}
            if os.path.exists(savedPath):
                os.remove(savedPath)

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
        print(f"{restored} sheet(s) uploaded earlier are still served, with the same links")
    print(f"open http://127.0.0.1:{port}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")

if __name__ == "__main__":
    main(sys.argv[1:])
