""" 
    replays every path through cli.py and compares the output against tests/expected_cli.txt

    run it with:      python3 tests/golden_cli.py
    re-record with:   python3 tests/golden_cli.py --record

    the point is that refactoring must not change what a user sees, so anything
    that shows up in the diff is either a bug or a change you meant to make
"""
import difflib
import os
import re
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_FILE = os.path.join(PROJECT_DIR, 'tests', 'expected_cli.txt')

# every choice worth replaying, including the ones that used to crash
INPUTS = [
    '1\nArt\n', '1\nAmerican History\n', '1\nAMERICAN HISTORY\n', '1\nzzz\n', '1\nsubject\n', '1\n\n',
    '2\nQH\n', '2\nJX\n', '2\nqh\n', '2\nAA\n', '2\nZZ\n', '2\nclassmark\n', '2\n\n',
    '3\n1\n', '3\n2\n', '3\n5\n', '3\n6\n', '3\n99\n', '3\n0\n', '3\nabc\n',
    '4\n', '0\n', '-1\n', 'abc\n', '2.5\n', '',
]

# a traceback's line numbers move whenever the code moves, so only the type is kept
def collapse_traceback(output):
    head, separator, tail = output.partition('Traceback (most recent call last):')
    if not separator:
        return output
    exception = re.search(r'^([A-Za-z_.]*(?:Error|Exception|Interrupt))', tail, re.M)
    return head + f"<<TRACEBACK: {exception.group(1) if exception else '?'}>>\n"

def run_all():
    sections = []
    for userInput in INPUTS:
        finished = subprocess.run([sys.executable, 'cli.py'], input=userInput, capture_output=True,
                                  text=True, timeout=60, cwd=PROJECT_DIR)
        sections.append(f"===== INPUT: {userInput!r}\n" + collapse_traceback(finished.stdout + finished.stderr))
    return "\n".join(sections)

if __name__ == '__main__':
    actual = run_all()

    if '--record' in sys.argv:
        with open(EXPECTED_FILE, 'w') as expected_file:
            expected_file.write(actual)
        print(f"recorded {len(INPUTS)} scenarios to {EXPECTED_FILE}")
        raise SystemExit(0)

    if not os.path.exists(EXPECTED_FILE):
        raise SystemExit(f"no baseline yet; run: python3 {sys.argv[0]} --record")

    with open(EXPECTED_FILE) as expected_file:
        expected = expected_file.read()

    if actual == expected:
        print(f"OK: all {len(INPUTS)} scenarios match tests/expected_cli.txt")
        raise SystemExit(0)

    print("\n".join(difflib.unified_diff(expected.splitlines(), actual.splitlines(),
                                         'expected', 'actual', lineterm='')))
    raise SystemExit("FAILED: cli.py output changed")
