# Find your marks

A small web page for handing out marks. Upload a class mark sheet, get one
link per student, and give each student theirs. Their link shows their own row
and nothing else.

Python 3.10 or newer. CSV needs nothing installed. Excel needs `openpyxl`.

## Running it

```bash
python3 -m marks.web          # then open http://127.0.0.1:8000
python3 -m marks.web 9000     # on a different port
```

For Excel files, install the one dependency first:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m marks.web
```

Without it, CSV still works and an Excel upload is refused with a message
saying what to install.

## The sheet

One row per student, one column per subject:

```csv
roll,name,class,section,Maths,Science,English
12,Sanket,10,A,72,65,80
13,Mokshada,10,A,81,90,77
14,Sanket,10,B,55,60,58
```

Columns named like `roll`, `name`, `class`, `section`, `id`, `grade` or
`division` are read as saying *who* a row is about. Every other column is
taken to be a subject. If none of the headings are recognised, the first
column is used as the identity column.

`.csv`, `.xlsx` and `.xlsm` are read, along with `.tsv` and markdown tables.
Excel is read from the first worksheet, and a formula such as `=SUM(E2:G2)`
arrives as the number it worked out — as long as the file was saved by a
spreadsheet program, which is what stores that number in the file.

## Two kinds of address

Uploading a sheet lands you on its own page at `/sheet/<id>`, which lists
every student together with a link of their own:

```
12 Sanket 10 A      http://…/s/7036e3c6a24eb29fc1c7
13 Mokshada 10 A    http://…/s/dca1b0892af83e760e87
14 Priya 10 B       http://…/s/cf03ceb7012cceb6d3f5
```

**Keep the `/sheet/<id>` address to yourself.** It shows the whole class.
**Hand out the `/s/<token>` links.** Each one shows a single row, and carries
no way to reach the sheet or any other student.

Each sheet is held separately, so uploading a second one does not disturb the
first, and links already handed out keep working.

A student's link is worked out from a secret kept in `uploads/.link-secret`,
not stored per student, so the links survive a restart. Delete that file and
every link changes.

There is also a lookup form on the sheet page for finding one student quickly.
It is built from whatever identity columns your sheet has — fill in as many
boxes as you need, since empty boxes are ignored, so a roll number on its own
works and so does a name with a class and a section. Matching ignores case and
surrounding spaces. If more than one student matches, no marks are shown and
the page asks for more detail.

## Totals

If your sheet already has a `Total` or `Percentage` column, its figures are
shown as they are and nothing is added on top. If it has none, a total and an
average are worked out from the marks that are numbers; a column holding a
grade or a remark is left out of both.

## A note on privacy

A student's link is 80 bits of unguessable text, so it cannot be found by
trying. It is still a link: whoever holds it sees those marks, so it is only
as private as the way you send it.

There is no login, and no attempt to prove who is opening a link. Uploaded
sheets are written unencrypted to `uploads/`, which is gitignored so real
student data is never committed. The server speaks plain HTTP and listens on
`127.0.0.1`; putting it anywhere public means putting HTTPS in front of it.

## Layout

```
marks/
  loaders.py   reads a CSV, Excel or markdown file into a Table
  table.py     rows as {column: [values]}
  sheet.py     tells who-columns from subject-columns, finds a student
  links.py     the unguessable part of a per-student link
  web.py       the upload page, the sheet page, and one page per student
tests/
  run_all.py   runs every suite
```

## Tests

```bash
python3 tests/run_all.py
```
