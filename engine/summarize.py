""" 
    counting instead of looking up.

    a lookup answers 'where is this one thing'; a summary answers 'how many of
    each', which is the shape survey results and grade distributions need
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Count:
    """ one group, how many rows fell into it, and what share of the total that is """
    value: str
    count: int
    share: float

@dataclass(frozen=True)
class SummaryResult:
    label: str
    counts: tuple
    total: int

# counting how often each value appears in one column of one table
def summarize(dataset, summary):
    table = dataset.table(summary.table)

    tally = {}
    for row in table.rows:
        # a cell holding several values counts once for each of them
        for value in table.values(row, summary.group):
            tally[value] = tally.get(value, 0) + 1

    total = sum(tally.values())
    # biggest group first, then alphabetically so equal counts have a stable order
    ordered = sorted(tally.items(), key=lambda pair: (-pair[1], pair[0]))
    counts = tuple(
        Count(value, count, (count / total) if total else 0.0)
        for value, count in ordered
    )
    return SummaryResult(label=summary.label, counts=counts, total=total)
