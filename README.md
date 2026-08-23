# Find your marks

A small web page for looking up a student's marks. Someone uploads a mark
sheet, a student types in what they know about themselves, and they get their
own marks back.

Python 3.10 or newer. No dependencies — it uses only the standard library.

## Running it

```bash
python3 -m marks.web          # then open http://127.0.0.1:8000
python3 -m marks.web 9000     # on a different port
```

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

Only `.csv` is read at the moment. Export from Excel first.

## Looking yourself up

The form is built from whatever identity columns your sheet has. Fill in as
many boxes as you need — empty boxes are ignored, so a roll number on its own
works, and so does a name together with a class and a section. Matching
ignores case and surrounding spaces.

If more than one student matches, no marks are shown and the page asks for
more detail, so nobody is shown someone else's results by accident.

Total and average are worked out from the marks that are numbers; a column
holding a grade or a remark is left out of both.

## A note on privacy

There is no login. Anyone who knows a roll number, or a full name, can read
that student's marks. That is fine for trying this out on your own machine
and not fine for putting on the open internet.

Uploaded sheets are written to `uploads/`, which is gitignored so real student
data is never committed.

## Layout

```
marks/
  loaders.py   reads a file into a Table
  table.py     rows as {column: [values]}
  sheet.py     tells who-columns from subject-columns, finds a student
  web.py       the upload and lookup pages
tests/
  run_all.py   runs every suite
```

## Tests

```bash
python3 tests/run_all.py
```
