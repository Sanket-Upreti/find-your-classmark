""" answering the three questions the app can ask; these return data, never text """
from . import results

# what a subject's classes are, and where each of them sits
def find_by_subject(dataset, subject):
    placements = []
    for classmark in dataset.classmarks_for_subject(subject):
        locations = dataset.locations_for_classmark(classmark)
        # a class with no location recorded still counts as a result
        if not locations:
            placements.append(results.ClassPlacement(classmark, None))
        else:
            # a class can sit in more than one location, so each pair is its own result
            for location in locations:
                placements.append(results.ClassPlacement(classmark, location))

    return results.SubjectResult(query=subject, placements=tuple(placements))

# where a class is, and every subject taught on it
def find_by_classmark(dataset, classmark):
    return results.ClassmarkResult(
        query=classmark,
        locations=tuple(dataset.locations_for_classmark(classmark)),
        subjects=tuple(dataset.subjects_for_classmark(classmark)),
    )

# every class in a location, with the subjects taught on each of them
def find_by_location(dataset, choice, locationOptions):
    locationSelected = locationOptions.get(choice)
    # error handling when the choice isn't one of the locations on offer
    if locationSelected is None:
        return results.LocationResult(query=choice)

    classes = tuple(
        results.ClassSubjects(classmark, tuple(dataset.subjects_for_classmark(classmark)))
        for classmark in dataset.classmarks_in_location(locationSelected)
    )
    return results.LocationResult(query=choice, location=locationSelected, classes=classes)
