""" 
    reading a mark sheet into a Table.

    CSV, TSV, Excel and markdown pipe tables are understood, and the first row
    names the columns. cells are taken exactly as they are written, so a name
    like "Smith;John" stays one value
"""
import csv
import os
import re

from .table import Table

# reading one cell; only splits when a caller asks for a separator
def cell_to_list(cellValue, delimiter=None):
    cellValue = cellValue.strip()
    if not cellValue:
        return []
    if delimiter and delimiter in cellValue:
        return [part.strip() for part in cellValue.split(delimiter) if part.strip()]
    return [cellValue]

# reading a CSV or TSV file into its column names and its raw rows
def read_delimited(filePath):
    separator = "\t" if filePath.lower().endswith(".tsv") else ","
    with open(filePath, 'r', newline="") as fileToRead:
        allRows = list(csv.reader(fileToRead, delimiter=separator))
    if not allRows:
        return [], []
    return [column.strip() for column in allRows[0]], allRows[1:]

"""
    reading the first sheet of an Excel workbook.

    openpyxl is only imported when an Excel file is actually opened, so the
    app still runs for CSV without it being installed
"""
def read_excel(filePath):
    try:
        import openpyxl
    except ImportError:
        raise ValueError(
            "reading Excel files needs openpyxl; install it with "
            "'pip install -r requirements.txt', or save the sheet as CSV instead")

    """
        data_only asks for the value a formula worked out rather than the
        formula itself, so a =SUM() total column arrives as a number
    """
    workbook = openpyxl.load_workbook(filePath, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        rows = [[excel_cell(value) for value in row]
                for row in worksheet.iter_rows(values_only=True)]
    finally:
        workbook.close()

    # trailing blank rows and columns are common in a saved workbook
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return [], []

    columns = [column.strip() for column in rows[0]]
    while columns and not columns[-1]:
        columns.pop()
    return columns, rows[1:]

"""
    turning one Excel value into text.

    a mark typed as 72 arrives as a number, and would otherwise be shown as
    72.0, so whole numbers lose their decimal part
"""
def excel_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()

# splitting one line of a markdown table into its cells
def _markdown_cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]

# the |---|---| line under a markdown table's headings carries no data
def _is_markdown_separator(cells):
    return bool(cells) and all(re.fullmatch(r":?-+:?", cell) for cell in cells if cell)

# reading the first pipe table in a markdown file into its column names and its raw rows
def read_markdown(filePath):
    with open(filePath, 'r') as fileToRead:
        lines = fileToRead.read().splitlines()

    tableLines = []
    for line in lines:
        if "|" in line:
            tableLines.append(line)
        elif tableLines:
            # the table ends at the first line that isn't part of it
            break

    if not tableLines:
        return [], []

    columns = _markdown_cells(tableLines[0])
    rows = [_markdown_cells(line) for line in tableLines[1:]]
    return columns, [row for row in rows if not _is_markdown_separator(row)]

READERS = {
    ".csv": read_delimited,
    ".tsv": read_delimited,
    ".txt": read_delimited,
    ".xlsx": read_excel,
    ".xlsm": read_excel,
    ".md": read_markdown,
    ".markdown": read_markdown,
}

# reading any supported file into a Table
def load_table(filePath, name=None, delimiter=None):
    suffix = os.path.splitext(filePath)[1].lower()
    reader = READERS.get(suffix)
    if reader is None:
        raise ValueError(f"don't know how to read {filePath!r}; supported: {', '.join(sorted(READERS))}")

    columns, rawRows = reader(filePath)
    rows = []
    for rawRow in rawRows:
        # skipping rows that hold nothing at all so they cannot break a search
        if not any(cell.strip() for cell in rawRow):
            continue
        row = {}
        for position, column in enumerate(columns):
            cell = rawRow[position] if position < len(rawRow) else ""
            row[column] = cell_to_list(cell, delimiter)
        rows.append(row)

    return Table(name or os.path.splitext(os.path.basename(filePath))[0], columns, rows)
