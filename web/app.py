""" 
    a small local web page for searching a dataset.

    run it with:  python3 -m web.app [config.yaml] [port]
    then open the address it prints. it uses only the standard library
"""
import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import config, query, summarize
from render import text

STYLE = """
:root { --ink:#1b1b1f; --paper:#fdfdfb; --line:#dcdce2; --soft:#6b6b76; --accent:#2f5fd0; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e9e9ee; --paper:#17171b; --line:#33333c; --soft:#a0a0ac; --accent:#8fb0ff; }
}
* { box-sizing:border-box; }
body { margin:0; padding:2rem 1.25rem 4rem; background:var(--paper); color:var(--ink);
       font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:60rem; margin:0 auto; }
h1 { font-size:1.5rem; margin:0 0 .25rem; }
h2 { font-size:1.05rem; margin:2rem 0 .6rem; font-weight:600; }
.sub { color:var(--soft); margin:0 0 2rem; }
a { color:var(--accent); }
form { display:flex; flex-wrap:wrap; gap:.5rem; align-items:center; margin:0 0 .75rem; }
label { min-width:11rem; color:var(--soft); font-size:.9rem; }
input,select { padding:.5rem .6rem; border:1px solid var(--line); border-radius:6px;
               background:var(--paper); color:var(--ink); font:inherit; min-width:14rem; }
button { padding:.5rem .9rem; border:0; border-radius:6px; background:var(--accent);
         color:#fff; font:inherit; cursor:pointer; }
ul.answers { padding-left:1.1rem; margin:.5rem 0 1.5rem; }
ul.answers li { margin:.15rem 0; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:.92rem; }
th,td { text-align:left; padding:.45rem .6rem; border-bottom:1px solid var(--line);
        vertical-align:top; white-space:nowrap; }
th { color:var(--soft); font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
.bar { display:inline-block; height:.6rem; border-radius:3px; background:var(--accent); min-width:2px; }
.empty { color:var(--soft); font-style:italic; }
"""

def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><main>{body}</main></body></html>"""

def escape(value):
    return html.escape(str(value))

# a field may hold one value, several, or nothing at all
def show_value(value):
    if value is None or value == []:
        return '<span class="empty">none</span>'
    if isinstance(value, (list, tuple)):
        return escape(", ".join(str(part) for part in value))
    return escape(value)

# one search box, or a dropdown when the search offers a fixed list of choices
def search_form(position, search):
    if search.choices:
        options = "".join(
            f'<option value="{number}">{escape(choice)}</option>'
            for number, choice in search.numbered_choices().items()
        )
        field = f'<select name="q">{options}</select>'
    else:
        field = f'<input name="q" placeholder="{escape(search.label)}" autocomplete="off">'
    return (f'<form action="/search"><input type="hidden" name="i" value="{position}">'
            f'<label>{escape(search.question)}</label>{field}'
            f'<button type="submit">Search</button></form>')

def home(dataset):
    forms = "".join(search_form(position, search) for position, search in enumerate(dataset.searches))
    body = [f"<h1>{escape(dataset.name or 'Search')}</h1>",
            f'<p class="sub">{len(dataset.tables)} table(s): '
            f"{escape(', '.join(dataset.tables))}</p>",
            "<h2>Search</h2>", forms]

    if dataset.summaries:
        links = "".join(
            f'<li><a href="/summary?i={position}">{escape(summary.label)}</a></li>'
            for position, summary in enumerate(dataset.summaries)
        )
        body.append(f"<h2>Summaries</h2><ul class='answers'>{links}</ul>")

    return page(dataset.name or "Search", "".join(body))

# the rows a search produced, shown as a table
def rows_table(rows):
    if not rows:
        return '<p class="empty">No rows.</p>'

    columns = []
    for row in rows:
        for column in row:
            if column not in columns:
                columns.append(column)

    head = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{show_value(row.get(column))}</td>" for column in columns) + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

def search_page(dataset, position, rawValue):
    search = dataset.searches[position]
    # a search offering choices is answered by the number of the choice
    value = int(rawValue) if search.choices and rawValue.isdigit() else rawValue

    result = query.run(dataset, search, value)
    answers = "".join(f"<li>{escape(line)}</li>" for line in text.lines_for(search, result))
    rows = query.rows_for(dataset, search, value)

    body = [f"<h1>{escape(dataset.name or 'Search')}</h1>",
            f'<p class="sub"><a href="/">&larr; another search</a></p>',
            f"<h2>{escape(search.label)}: {escape(rawValue)}</h2>",
            f'<ul class="answers">{answers}</ul>',
            "<h2>Rows</h2>", rows_table(rows)]
    return page(f"{search.label}: {rawValue}", "".join(body))

def summary_page(dataset, position):
    summary = dataset.summaries[position]
    result = summarize.summarize(dataset, summary)

    rows = "".join(
        f"<tr><td>{escape(entry.value)}</td>"
        f'<td class="num">{entry.count}</td>'
        f'<td class="num">{entry.share:.0%}</td>'
        f'<td style="width:40%"><span class="bar" style="width:{entry.share * 100:.1f}%"></span></td></tr>'
        for entry in result.counts
    )
    body = [f"<h1>{escape(dataset.name or 'Search')}</h1>",
            '<p class="sub"><a href="/">&larr; back</a></p>',
            f"<h2>{escape(result.label)}</h2>",
            f'<p class="sub">{result.total} response(s)</p>',
            '<div class="scroll"><table><thead><tr><th>value</th><th class="num">count</th>'
            f'<th class="num">share</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>']
    return page(result.label, "".join(body))

def make_handler(dataset):
    class Handler(BaseHTTPRequestHandler):
        # keeping the console quiet apart from what this file prints itself
        def log_message(self, *arguments):
            pass

        def reply(self, status, markup):
            encoded = markup.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            fields = urllib.parse.parse_qs(parsed.query)
            position = int(fields.get("i", ["0"])[0] or 0)

            try:
                if parsed.path == "/":
                    self.reply(200, home(dataset))
                elif parsed.path == "/search":
                    if not 0 <= position < len(dataset.searches):
                        self.reply(404, page("Not found", "<h1>No such search</h1>"))
                    else:
                        self.reply(200, search_page(dataset, position, fields.get("q", [""])[0]))
                elif parsed.path == "/summary":
                    if not 0 <= position < len(dataset.summaries):
                        self.reply(404, page("Not found", "<h1>No such summary</h1>"))
                    else:
                        self.reply(200, summary_page(dataset, position))
                else:
                    self.reply(404, page("Not found", '<h1>Not found</h1><p><a href="/">Back</a></p>'))
            except (ValueError, KeyError) as error:
                self.reply(400, page("Bad request", f"<h1>Bad request</h1><p>{escape(error)}</p>"))

    return Handler

# built separately from serve_forever so a test can drive it without a real browser
def make_server(dataset, port=8000, host="127.0.0.1"):
    return HTTPServer((host, port), make_handler(dataset))

def main(arguments):
    configPath = next((argument for argument in arguments if not argument.isdigit()), None)
    port = int(next((argument for argument in arguments if argument.isdigit()), 8000))

    dataset = config.load_config(configPath) if configPath else config.load_default()
    server = make_server(dataset, port)
    print(f"{dataset.name or 'dataset'} is being served at http://127.0.0.1:{port}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")

if __name__ == "__main__":
    main(sys.argv[1:])
