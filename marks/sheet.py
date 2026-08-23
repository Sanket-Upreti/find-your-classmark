""" 
    making sense of a wide mark sheet: one row per student, one column per subject.

        roll,name,class,section,Maths,Science,English
        12,Sanket,10,A,72,65,80

    the columns that say who a student is are told apart from the columns that
    hold their marks, so a student can be found and their marks read off the row
"""

"""
    column names that describe a student rather than a mark.
    anything not in here is treated as a subject
"""
IDENTITY_HINTS = {
    "roll", "rollno", "rollnumber", "rollno.", "no", "number",
    "id", "studentid", "admissionno", "admissionnumber",
    "name", "student", "studentname", "fullname", "firstname", "lastname",
    "class", "grade", "standard", "year",
    "section", "div", "division", "stream", "house",
}

"""
    column names that already hold a worked out figure.
    these are shown like any other column, but adding them into our own total
    would count the same marks twice, so they are left out of it
"""
SUMMARY_HINTS = {
    "total", "totals", "totalmarks", "grandtotal", "sum", "subtotal",
    "percentage", "percent", "pct", "average", "avg", "mean", "aggregate",
    "result", "rank", "position", "cgpa", "gpa", "outof", "maxmarks",
}

# comparing column names without caring about spaces, case or punctuation
def normalise(text):
    return "".join(character for character in str(text).lower() if character.isalnum())

# reading one cell as a single piece of text
def cell(row, column):
    values = row.get(column) or []
    return ", ".join(str(value) for value in values)

class Sheet:
    """ a loaded mark sheet, with its columns sorted into who and what """
    def __init__(self, table, fileName=""):
        self.table = table
        self.fileName = fileName
        self.columns = list(table.columns)
        self.identityColumns = [column for column in self.columns
                                if normalise(column) in IDENTITY_HINTS]
        # everything that isn't describing the student is taken to be a subject
        self.markColumns = [column for column in self.columns
                            if column not in self.identityColumns]

        """ 
            a sheet with headings we don't recognise still has to be searchable,
            so the first column is taken to be who the row is about
        """
        if not self.identityColumns and self.columns:
            self.identityColumns = [self.columns[0]]
            self.markColumns = self.columns[1:]

        # the sheet's own totals, kept apart so they aren't added up again
        self.summaryColumns = [column for column in self.markColumns
                               if normalise(column) in SUMMARY_HINTS]

    @property
    def rows(self):
        return self.table.rows

    def __repr__(self):
        return (f"Sheet({self.fileName!r}, students={len(self.rows)}, "
                f"identity={self.identityColumns}, marks={self.markColumns})")

# building a sheet from a file already read by the loaders
def from_table(table, fileName=""):
    return Sheet(table, fileName)

"""
    finding the students matching what was typed in.

    only the boxes that were filled in are compared, so a student can be found
    by a roll number on its own, or by a name together with class and section
"""
def find(sheet, criteria):
    wanted = {column: value.strip().lower()
              for column, value in criteria.items()
              if value and value.strip()}
    if not wanted:
        return []

    matched = []
    for row in sheet.rows:
        if all(cell(row, column).strip().lower() == value for column, value in wanted.items()):
            matched.append(row)
    return matched

# the subject and mark pairs on one student's row
def marks_for(sheet, row):
    return [(column, cell(row, column)) for column in sheet.markColumns]

# who the row belongs to, for showing back to the student
def identity_of(sheet, row):
    return [(column, cell(row, column)) for column in sheet.identityColumns]

"""
    the total and average of the marks that are numbers.
    a column holding something else, a grade or a remark, is left out of both,
    and so is any column named in skip, which is how a sheet's own Total
    column avoids being counted a second time
"""
def total_and_average(marks, skip=()):
    numbers = []
    for column, value in marks:
        if column in skip:
            continue
        try:
            numbers.append(float(value))
        except (TypeError, ValueError):
            continue

    if not numbers:
        return None, None
    total = sum(numbers)
    # whole numbers read better without a trailing .0
    if total == int(total):
        total = int(total)
    return total, sum(numbers) / len(numbers)
