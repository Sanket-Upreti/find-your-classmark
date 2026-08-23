""" turning a result into the lines the terminal prints """

# joining several values into one readable phrase, or None when there are none
def _joined(values):
    return ", ".join(values) if values else None

# lines for option 1, a subject search
def subject_lines(result):
    if not result.found:
        return [f"Thank you for answering, but no class or location was found for subject {result.query}"]

    # a single result reads better as one sentence, anything more gets listed
    if len(result.placements) == 1:
        placement = result.placements[0]
        if placement.location is None:
            return [f"Thank you for answering, but no location was found for subject {result.query}"]
        return [f"Thank you for answering, Subject {result.query} happens on class {placement.classmark} which is located in {placement.location}"]

    lines = [f"Thank you for answering. There are multiple classes happening for Subject {result.query}"]
    for placement in result.placements:
        if placement.location is None:
            lines.append(f"No location was found for subject {placement.classmark}")
        else:
            lines.append(f"Subject {result.query} happens on class {placement.classmark} which is located in {placement.location}")
    return lines

# lines for option 2, a classmark search
def classmark_lines(result):
    locationFound = _joined(result.locations)
    subjectFound = _joined(result.subjects)

    # error handling when nothing was found, with the help of if...else
    if locationFound is None:
        if subjectFound is None:
            return [f"Thank you for answering, but no location or subject was found for class {result.query}"]
        return [f"Thank you for answering, but no location was found for class {result.query} which has {subjectFound} running on it"]

    if subjectFound is None:
        return [f"Thank you for answering, but no subject was found for class {result.query} which is in {locationFound}"]
    return [f"Thank you for answering, Subject {subjectFound} happens on class {result.query} which is located in {locationFound}"]

# lines for option 3, a location search
def location_lines(result):
    if result.location is None:
        return [f"Thank you for answering, but no class, subject or location was found for your search {result.query}"]

    if not result.classes:
        return [f"Thank you for answering, but no class, subject or location was found for your search {result.location}. Please make sure your location is similar to the options provided"]

    lines = [f"Thank you for answering, There are some classes and subjects taught in location {result.location}"]
    for entry in result.classes:
        subjectFound = _joined(entry.subjects)
        if subjectFound is None:
            lines.append(f"No subject was found for class {entry.classmark} in location {result.location}")
        else:
            lines.append(f"Subject {subjectFound} happens on class {entry.classmark} which is located in {result.location}")
    return lines
