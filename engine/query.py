""" 
    answering the questions a search offers; these return data, never text.
    the walk itself is declared by the config, so this file only shapes the answer
"""
from . import results, traverse

# what a subject's classes are, and where each of them sits
def find_by_subject(dataset, search, subject):
    rows = traverse.run_steps(dataset, search.steps, {"query": subject})
    placements = tuple(
        results.ClassPlacement(row["classmark"], row["location"]) for row in rows
    )
    return results.SubjectResult(query=subject, placements=placements)

# where a class is, and every subject taught on it
def find_by_classmark(dataset, search, classmark):
    rows = traverse.run_steps(dataset, search.steps, {"query": classmark})
    row = rows[0] if rows else {}
    return results.ClassmarkResult(
        query=classmark,
        locations=tuple(row.get("locations") or ()),
        subjects=tuple(row.get("subjects") or ()),
    )

# every class in a location, with the subjects taught on each of them
def find_by_location(dataset, search, choice):
    locationSelected = search.numbered_choices().get(choice)
    # error handling when the choice isn't one of the locations on offer
    if locationSelected is None:
        return results.LocationResult(query=choice)

    rows = traverse.run_steps(dataset, search.steps, {"query": choice, "location": locationSelected})
    classes = tuple(
        results.ClassSubjects(row["classmark"], tuple(row.get("subjects") or ()))
        for row in rows
    )
    return results.LocationResult(query=choice, location=locationSelected, classes=classes)

# picking the right question for a search, so callers don't switch on the kind themselves
BY_KIND = {
    "subject": find_by_subject,
    "classmark": find_by_classmark,
    "location": find_by_location,
}

def run(dataset, search, value):
    return BY_KIND[search.kind](dataset, search, value)

# the rows a search produces, before any wording is applied; used by the web page
def rows_for(dataset, search, value):
    seed = {"query": value}
    if search.choices:
        chosen = search.numbered_choices().get(value)
        if chosen is None:
            return []
        seed[search.kind] = chosen
    return traverse.run_steps(dataset, search.steps, seed)
