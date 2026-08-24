# Marks

A small web app for handing out results. An organisation uploads a mark sheet
and gets one invite link per student. A student opens their invite, sets a
password, and from then on signs in to see their own marks — and only their
own — on every sheet that organisation publishes.

Python 3.10 or newer, standard library only. CSV needs nothing installed;
Excel needs `openpyxl`.

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

## How it fits together

**Create an organisation.** Whoever does this becomes its teacher and gets a
join code — something like `K4BU-A2FH`, safe to write on a board.

**Upload a mark sheet.** One row per student, one column per subject. The app
works out which column identifies a student (a roll or admission number if
there is one, otherwise the first identity column) and gives every row an
invite link of its own.

**Hand out the invites.** An invite shows that student's marks and offers them
a password. Holding the link is the proof of who they are — which is why the
teacher hands them out individually rather than posting one address.

**After that they just sign in** with the join code, their roll number and
their password. They see their row on every sheet the organisation has
uploaded, including ones added later.

## Two kinds of address

```
/teacher/sheet/<id>     every student on one sheet — teacher only
/s/<token>              one student's invite — hand these out
/me                     a signed-in student's own marks
```

`/teacher/...` needs a teacher signed in, and a sheet belonging to another
organisation is simply not there. `/s/<token>` needs no account: the token is
80 bits of unguessable text.

## The sheet

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

If your sheet already has a `Total` or `Percentage` column, its figures are
shown as they are and nothing is added on top. If it has none, a total and an
average are worked out from the marks that are numbers; a column holding a
grade or a remark is left out of both.

Accounts are remembered against **(organisation, roll number)**, not against a
row in one file. Next term's upload therefore appears for students who signed
up last term, with no re-enrolment — as long as their roll number has not
changed.

## What is kept, and where

Everything lives under `uploads/`, which is gitignored so real student data is
never committed:

```
uploads/
  marks.db          organisations, teachers, students, which sheet is whose
  .link-secret      the secret invites are derived from (mode 600)
  <id>__sheet.csv   the uploaded sheets themselves
```

Passwords are stored as scrypt hashes with a per-password salt, never as
text. Sessions are a signed cookie — `HttpOnly`, `SameSite=Lax` — carrying who
you are and when that stops being true.

## A note on privacy

This is a real access boundary, and it is worth being clear about its edges.

- **Invites are links.** Whoever holds one sees those marks. They cannot be
  guessed, but they can be forwarded. Send each one to one person.
- **The first person to open an invite claims that account.** After that the
  link says so and refuses. So hand invites out promptly.
- **Signing out clears the cookie but does not invalidate it**, because
  sessions are self-contained rather than stored. A cookie copied off a
  machine stays usable until it expires.
- **This serves plain HTTP and listens on `127.0.0.1`.** Over a network,
  passwords and invite tokens would travel in the clear. Anywhere public needs
  HTTPS in front of it, and the session cookie should then be marked `Secure`.

There is no password reset. If a student forgets theirs, remove their row from
`students` in `marks.db` and send them a fresh invite.

## Layout

```
marks/
  loaders.py    reads a CSV, Excel or markdown file into a Table
  table.py      rows as {column: [values]}
  sheet.py      tells who-columns from subject-columns, finds a student
  links.py      the unguessable part of an invite
  accounts.py   passwords, sessions and join codes
  database.py   organisations, teachers, students, sheets
  web.py        the pages and who is allowed on them
tests/
  harness.py    a throwaway server and a browser that keeps its cookies
  run_all.py    runs every suite
```

## Tests

```bash
python3 tests/run_all.py
```
