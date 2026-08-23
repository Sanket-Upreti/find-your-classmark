""" 
    reading tabular files into Tables; nothing here knows about classmarks.
    CSV/TSV and markdown pipe tables are understood, and the first row names the columns
"""
import ast
import csv
import os
import re

from .table import Table

# the character that separates several values inside one cell
VALUE_DELIMITER = ";"

# reusuable function for reading a cell that can hold more than one value
def cell_to_list(cellValue, delimiter=VALUE_DELIMITER):
    cellValue = cellValue.strip()
    if not cellValue:
        return []

    """ 
        older files hold several values as a python list instead of a delimited cell;
        literal_eval only understands plain literals, so a file can never run code
    """
    if cellValue.startswith("[") and cellValue.endswith("]"):
        try:
            parsedValue = ast.literal_eval(cellValue)
        except (ValueError, SyntaxError):
            return [cellValue]
        if isinstance(parsedValue, list):
            return [str(value).strip() for value in parsedValue if str(value).strip()]
        return [str(parsedValue)]

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
    ".md": read_markdown,
    ".markdown": read_markdown,
}

# reading any supported file into a Table
def load_table(filePath, name=None, delimiter=VALUE_DELIMITER):
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
