""" 
    walking a dataset by following the steps a search declares.

    every search produces rows: a row is a dictionary of named fields, built up
    one step at a time. a step either splits a row into one row per value it
    finds (each: true), or gathers every value into a single field (each: false)
"""

# a field may hold one value or several; both are walked the same way
def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]

# following one step for one row, returning the rows it becomes
def _apply_step(dataset, step, row):
    sourceField = step.get("from", "query")
    targetField = step["as"]

    found = []
    for sourceValue in as_list(row.get(sourceField)):
        found.extend(dataset.follow(step["follow"], sourceValue))

    # gathering everything into one field leaves the row whole
    if not step.get("each"):
        return [{**row, targetField: found}]

    # splitting gives one row per value found
    if found:
        return [{**row, targetField: value} for value in found]

    """ 
        nothing was found; the row is either dropped, or kept with an empty field
        so the wording can say that this part of the answer is missing
    """
    if step.get("keep_empty"):
        return [{**row, targetField: None}]
    return []

# walking every step in order, starting from the fields the caller supplies
def run_steps(dataset, steps, seed):
    rows = [dict(seed)]
    for step in steps:
        nextRows = []
        for row in rows:
            nextRows.extend(_apply_step(dataset, step, row))
        rows = nextRows
    return rows
