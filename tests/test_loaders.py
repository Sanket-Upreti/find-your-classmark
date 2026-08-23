""" 
    checks on the file reading behind an uploaded mark sheet

    run it with: python3 tests/test_loaders.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marks import loaders
from marks.table import Table

CHECKS = []

def check(name):
    def keep(function):
        CHECKS.append((name, function))
        return function
    return keep

# writing a temporary file for one check to read
def temp_file(suffix, contents):
    handle = tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False)
    handle.write(contents)
    handle.close()
    return handle.name

@check("a cell holding one value")
def _():
    assert loaders.cell_to_list("HF") == ["HF"]

@check("a cell is taken exactly as written, so a name with a semicolon survives")
def _():
    assert loaders.cell_to_list("Smith;John") == ["Smith;John"]
    assert loaders.cell_to_list("['E', 'F']") == ["['E', 'F']"]

@check("a cell is only split when a separator is asked for")
def _():
    assert loaders.cell_to_list("E;F", delimiter=";") == ["E", "F"]
    assert loaders.cell_to_list(" E ; F ", delimiter=";") == ["E", "F"]

@check("an empty cell holds nothing")
def _():
    assert loaders.cell_to_list("") == []
    assert loaders.cell_to_list("   ") == []

@check("a cell can never run code")
def _():
    assert loaders.cell_to_list("[__import__('os').getcwd()]") == ["[__import__('os').getcwd()]"]

@check("a mark sheet's cells are never split by default")
def _():
    path = temp_file(".csv", "name,Maths\nSmith;John,72\n")
    assert loaders.load_table(path).rows == [{"name": ["Smith;John"], "Maths": ["72"]}]

@check("CSV: first row names the columns")
def _():
    path = temp_file(".csv", "student,mark\nSanket,72\n")
    table = loaders.load_table(path)
    assert table.columns == ["student", "mark"]
    assert table.rows == [{"student": ["Sanket"], "mark": ["72"]}]

@check("CSV: more than two columns")
def _():
    path = temp_file(".csv", "a,b,c,d\n1,2,3,4\n")
    table = loaders.load_table(path)
    assert table.columns == ["a", "b", "c", "d"]
    assert table.rows[0]["d"] == ["4"]

@check("CSV: a short row leaves the missing columns empty")
def _():
    path = temp_file(".csv", "a,b,c\n1,2\n")
    assert loaders.load_table(path).rows[0] == {"a": ["1"], "b": ["2"], "c": []}

@check("CSV: blank rows are skipped")
def _():
    path = temp_file(".csv", "a,b\n1,2\n\n,\n3,4\n")
    assert len(loaders.load_table(path).rows) == 2

@check("TSV is read with tabs")
def _():
    path = temp_file(".tsv", "a\tb\n1\t2\n")
    assert loaders.load_table(path).rows == [{"a": ["1"], "b": ["2"]}]

@check("markdown: a pipe table is read")
def _():
    path = temp_file(".md", "| a | b |\n|---|---|\n| 1 | 2 |\n")
    table = loaders.load_table(path)
    assert table.columns == ["a", "b"]
    assert table.rows == [{"a": ["1"], "b": ["2"]}]

@check("markdown: prose around the table is ignored")
def _():
    path = temp_file(".md", "# Title\n\nwords\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nmore words\n")
    assert loaders.load_table(path).rows == [{"a": ["1"], "b": ["2"]}]

@check("markdown: alignment colons are not data")
def _():
    path = temp_file(".md", "| a | b |\n|:--|--:|\n| 1 | 2 |\n")
    assert len(loaders.load_table(path).rows) == 1

@check("markdown: outer pipes are optional")
def _():
    path = temp_file(".md", "a | b\n--|--\n1 | 2\n")
    assert loaders.load_table(path).rows == [{"a": ["1"], "b": ["2"]}]

@check("an unsupported file type is refused clearly")
def _():
    path = temp_file(".pdf", "nonsense")
    try:
        loaders.load_table(path)
    except ValueError as error:
        assert "don't know how to read" in str(error)
    else:
        raise AssertionError("expected a ValueError")

@check("excel is offered as a readable type")
def _():
    assert ".xlsx" in loaders.READERS and ".csv" in loaders.READERS

@check("searching a column ignores case")
def _():
    table = Table("t", ["a"], [{"a": ["Hello"]}])
    assert len(table.rows_where("a", "hELLO")) == 1

@check("searching finds every matching row, in file order")
def _():
    table = Table("t", ["a", "b"], [{"a": ["x"], "b": ["1"]}, {"a": ["y"], "b": ["2"]}, {"a": ["x"], "b": ["3"]}])
    assert [row["b"][0] for row in table.rows_where("a", "x")] == ["1", "3"]

@check("distinct values keep file order and drop repeats")
def _():
    table = Table("t", ["a"], [{"a": ["x"]}, {"a": ["y"]}, {"a": ["x"]}])
    assert table.distinct("a") == ["x", "y"]

if __name__ == '__main__':
    failures = 0
    for name, function in CHECKS:
        try:
            function()
            print(f"  ok   {name}")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error or 'assertion failed'}")
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    raise SystemExit(1 if failures else 0)
