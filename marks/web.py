""" 
    a small local web page for looking up marks.

    someone uploads a wide mark sheet, then a student types in what they know
    about themselves and gets their own marks back.

    run it with:  python3 -m marks.web [port]
    then open the address it prints. it uses only the standard library
"""
import email.parser
import email.policy
import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import loaders
from marks import sheet as sheet_module

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(PROJECT_DIR, "uploads")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

STYLE = """
:root { --ink:#1b1b1f; --paper:#fdfdfb; --card:#fff; --line:#dcdce2; --soft:#6b6b76; --accent:#2f5fd0; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e9e9ee; --paper:#141418; --card:#1c1c22; --line:#33333c; --soft:#a0a0ac; --accent:#8fb0ff; }
}
* { box-sizing:border-box; }
body { margin:0; padding:2.5rem 1.25rem 4rem; background:var(--paper); color:var(--ink);
       font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:44rem; margin:0 auto; }
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
table { border-collapse:collapse; width:100%; margin-top:.5rem; }
th,td { text-align:left; padding:.5rem .6rem; border-bottom:1px solid var(--line); }
th { color:var(--soft); font-weight:600; font-size:.85rem; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
tr.totals td { font-weight:600; border-bottom:0; }
.note { color:var(--soft); font-size:.9rem; }
.warn { color:#b3261e; }
@media (prefers-color-scheme: dark) { .warn { color:#ffb4ab; } }
.who { margin:.2rem 0 0; color:var(--soft); font-size:.94rem; }
"""

def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><main>{body}</main></body></html>"""

def escape(value):
    return html.escape(str(value))

class Store:
    """ the one sheet the page is currently working from """
    def __init__(self):
        self.sheet = None

    def load_file(self, filePath, fileName=""):
        table = loaders.load_table(filePath)
        self.sheet = sheet_module.from_table(table, fileName or os.path.basename(filePath))
        return self.sheet

    # picking up a sheet uploaded on an earlier run, so a restart doesn't lose it
    def load_saved(self):
        if not os.path.isdir(UPLOAD_DIR):
            return None
        saved = [name for name in sorted(os.listdir(UPLOAD_DIR)) if name.lower().endswith(".csv")]
        if not saved:
            return None
        return self.load_file(os.path.join(UPLOAD_DIR, saved[-1]), saved[-1])

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
    return f"""<h1>Find your marks</h1>
<p class="sub">Upload a mark sheet to get started. One row per student, one column per subject.</p>
<div class="card">
  <form action="/upload" method="post" enctype="multipart/form-data">
    <label for="sheet">Mark sheet (.csv)</label>
    <input id="sheet" type="file" name="sheet" accept=".csv,text/csv" required>
    <button type="submit">Upload</button>
  </form>
  {warning}
</div>"""

def lookup_form(sheet, values=None, message="", isError=False):
    values = values or {}
    boxes = "".join(
        f'<div><label for="f{position}">{escape(column)}</label>'
        f'<input id="f{position}" name="{escape(column)}" value="{escape(values.get(column, ""))}" '
        f'autocomplete="off"></div>'
        for position, column in enumerate(sheet.identityColumns)
    )
    warning = f'<p class="note {"warn" if isError else ""}">{escape(message)}</p>' if message else ""
    return f"""<h1>Find your marks</h1>
<p class="sub">{len(sheet.rows)} student(s) in <strong>{escape(sheet.fileName)}</strong> &middot;
subjects: {escape(", ".join(sheet.markColumns))}</p>
<div class="card">
  <form action="/lookup" method="get">
    <div class="fields">{boxes}</div>
    <button type="submit">Show my marks</button>
  </form>
  {warning}
</div>
<p class="sub" style="margin-top:1.5rem"><a href="/upload">Upload a different sheet</a></p>"""

def marks_table(sheet, row):
    marks = sheet_module.marks_for(sheet, row)
    rows = "".join(
        f"<tr><td>{escape(subject)}</td><td class='num'>{escape(value) or '&mdash;'}</td></tr>"
        for subject, value in marks
    )

    total, average = sheet_module.total_and_average(marks)
    if total is not None:
        rows += (f"<tr class='totals'><td>Total</td><td class='num'>{escape(total)}</td></tr>"
                 f"<tr class='totals'><td>Average</td><td class='num'>{average:.1f}</td></tr>")

    who = " &middot; ".join(f"{escape(column)}: <strong>{escape(value)}</strong>"
                            for column, value in sheet_module.identity_of(sheet, row) if value)
    return f"""<h2>Your marks</h2>
<p class="who">{who}</p>
<div class="card" style="margin-top:.75rem">
<table><thead><tr><th>Subject</th><th class="num">Mark</th></tr></thead><tbody>{rows}</tbody></table>
</div>"""

def lookup_page(sheet, criteria):
    filled = {column: value for column, value in criteria.items() if value.strip()}

    if not filled:
        return page("Find your marks",
                    lookup_form(sheet, criteria, "Fill in at least one box so we know who you are.", True))

    matched = sheet_module.find(sheet, criteria)

    if not matched:
        described = ", ".join(f"{column} {value}" for column, value in filled.items())
        return page("Not found",
                    lookup_form(sheet, criteria, f"No student found for {described}.", True))

    """ 
        more than one student matches, so no marks are shown; asking for more
        detail is both clearer and avoids showing someone else's results
    """
    if len(matched) > 1:
        return page("Which one?", lookup_form(
            sheet, criteria,
            f"{len(matched)} students match that. Please fill in more boxes to narrow it down.", True))

    return page("Your marks", lookup_form(sheet, criteria) + marks_table(sheet, matched[0]))

def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *arguments):
            pass

        def reply(self, status, markup):
            encoded = markup.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def go_home(self):
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)

            if parsed.path == "/upload":
                self.reply(200, page("Upload a mark sheet", upload_form()))
                return

            if store.sheet is None:
                self.reply(200, page("Find your marks", upload_form()))
                return

            if parsed.path == "/":
                self.reply(200, page("Find your marks", lookup_form(store.sheet)))
            elif parsed.path == "/lookup":
                fields = urllib.parse.parse_qs(parsed.query)
                criteria = {column: fields.get(column, [""])[0]
                            for column in store.sheet.identityColumns}
                self.reply(200, lookup_page(store.sheet, criteria))
            else:
                self.reply(404, page("Not found", '<h1>Not found</h1><p><a href="/">Back</a></p>'))

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/upload":
                self.reply(404, page("Not found", '<h1>Not found</h1><p><a href="/">Back</a></p>'))
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
            if not fileName.lower().endswith(".csv"):
                self.reply(400, page("Not a CSV", upload_form(
                    "That doesn't look like a .csv file. Excel sheets aren't supported yet, "
                    "so please export as CSV first.", True)))
                return

            os.makedirs(UPLOAD_DIR, exist_ok=True)
            savedPath = os.path.join(UPLOAD_DIR, safe_name(fileName))
            with open(savedPath, "wb") as savedFile:
                savedFile.write(contents)

            try:
                store.load_file(savedPath, safe_name(fileName))
            except Exception as error:
                os.remove(savedPath)
                self.reply(400, page("Could not read", upload_form(
                    f"That file could not be read: {error}", True)))
                return

            if not store.sheet.rows:
                self.reply(400, page("Empty", upload_form("That sheet has no students in it.", True)))
                store.sheet = None
                return

            self.go_home()

    return Handler

# built separately from serve_forever so a test can drive it without a browser
def make_server(store, port=8000, host="127.0.0.1"):
    return HTTPServer((host, port), make_handler(store))

def main(arguments):
    port = int(arguments[0]) if arguments else 8000
    store = Store()
    store.load_saved()

    server = make_server(store, port)
    if store.sheet:
        print(f"using the sheet uploaded earlier: {store.sheet.fileName}")
    print(f"open http://127.0.0.1:{port}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")

if __name__ == "__main__":
    main(sys.argv[1:])
