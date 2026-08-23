""" 
    answering the questions a search offers; these return data, never text.
    which links get followed comes from the config, not from this file
"""
from . import results

# what a subject's classes are, and where each of them sits
def find_by_subject(dataset, search, subject):
    toClasses, toLocations = search.follow

    placements = []
    for classmark in dataset.follow(toClasses, subject):
        locations = dataset.follow(toLocations, classmark)
        # a class with no location recorded still counts as a result
        if not locations:
            placements.append(results.ClassPlacement(classmark, None))
        else:
            # a class can sit in more than one location, so each pair is its own result
            for location in locations:
                placements.append(results.ClassPlacement(classmark, location))

    return results.SubjectResult(query=subject, placements=tuple(placements))

# where a class is, and every subject taught on it
def find_by_classmark(dataset, search, classmark):
    toLocations, toSubjects = search.follow

    return results.ClassmarkResult(
        query=classmark,
        locations=tuple(dataset.follow(toLocations, classmark)),
        subjects=tuple(dataset.follow(toSubjects, classmark)),
    )

# every class in a location, with the subjects taught on each of them
def find_by_location(dataset, search, choice):
    toClasses, toSubjects = search.follow

    locationSelected = search.numbered_choices().get(choice)
    # error handling when the choice isn't one of the locations on offer
    if locationSelected is None:
        return results.LocationResult(query=choice)

    classes = tuple(
        results.ClassSubjects(classmark, tuple(dataset.follow(toSubjects, classmark)))
        for classmark in dataset.follow(toClasses, locationSelected)
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
