""" turning a result into the lines the terminal prints """

"""
    the wording, with the app's own sentences as the default.
    a config can override any of these by name, which is how a different
    dataset gets to talk about students and marks instead of subjects and classes
"""
DEFAULT_WORDING = {
    # a subject search
    "subject_not_found": "Thank you for answering, but no class or location was found for subject {query}",
    "subject_single": "Thank you for answering, Subject {query} happens on class {classmark} which is located in {location}",
    "subject_single_no_location": "Thank you for answering, but no location was found for subject {query}",
    "subject_header": "Thank you for answering. There are multiple classes happening for Subject {query}",
    "subject_line": "Subject {query} happens on class {classmark} which is located in {location}",
    "subject_line_no_location": "No location was found for subject {classmark}",
    # a classmark search
    "classmark_none": "Thank you for answering, but no location or subject was found for class {query}",
    "classmark_no_location": "Thank you for answering, but no location was found for class {query} which has {subjects} running on it",
    "classmark_no_subject": "Thank you for answering, but no subject was found for class {query} which is in {locations}",
    "classmark_found": "Thank you for answering, Subject {subjects} happens on class {query} which is located in {locations}",
    # a location search
    "location_invalid": "Thank you for answering, but no class, subject or location was found for your search {query}",
    "location_empty": "Thank you for answering, but no class, subject or location was found for your search {location}. Please make sure your location is similar to the options provided",
    "location_header": "Thank you for answering, There are some classes and subjects taught in location {location}",
    "location_line": "Subject {subjects} happens on class {classmark} which is located in {location}",
    "location_line_no_subject": "No subject was found for class {classmark} in location {location}",
}

# filling in one message, letting the config override the default wording
def say(wording, key, **values):
    template = (wording or {}).get(key, DEFAULT_WORDING[key])
    return template.format(**values)

# joining several values into one readable phrase, or None when there are none
def _joined(values):
    return ", ".join(values) if values else None

# lines for a subject search
def subject_lines(result, wording=None):
    if not result.found:
        return [say(wording, "subject_not_found", query=result.query)]

    # a single result reads better as one sentence, anything more gets listed
    if len(result.placements) == 1:
        placement = result.placements[0]
        if placement.location is None:
            return [say(wording, "subject_single_no_location", query=result.query, classmark=placement.classmark)]
        return [say(wording, "subject_single", query=result.query,
                    classmark=placement.classmark, location=placement.location)]

    lines = [say(wording, "subject_header", query=result.query)]
    for placement in result.placements:
        if placement.location is None:
            lines.append(say(wording, "subject_line_no_location", query=result.query, classmark=placement.classmark))
        else:
            lines.append(say(wording, "subject_line", query=result.query,
                             classmark=placement.classmark, location=placement.location))
    return lines

# lines for a classmark search
def classmark_lines(result, wording=None):
    locationFound = _joined(result.locations)
    subjectFound = _joined(result.subjects)

    # error handling when nothing was found, with the help of if...else
    if locationFound is None:
        if subjectFound is None:
            return [say(wording, "classmark_none", query=result.query)]
        return [say(wording, "classmark_no_location", query=result.query, subjects=subjectFound)]

    if subjectFound is None:
        return [say(wording, "classmark_no_subject", query=result.query, locations=locationFound)]
    return [say(wording, "classmark_found", query=result.query,
                subjects=subjectFound, locations=locationFound)]

# lines for a location search
def location_lines(result, wording=None):
    if result.location is None:
        return [say(wording, "location_invalid", query=result.query)]

    if not result.classes:
        return [say(wording, "location_empty", query=result.query, location=result.location)]

    lines = [say(wording, "location_header", query=result.query, location=result.location)]
    for entry in result.classes:
        subjectFound = _joined(entry.subjects)
        if subjectFound is None:
            lines.append(say(wording, "location_line_no_subject",
                             classmark=entry.classmark, location=result.location))
        else:
            lines.append(say(wording, "location_line", classmark=entry.classmark,
                             location=result.location, subjects=subjectFound))
    return lines

# picking the right wording for a search, so callers don't switch on the kind themselves
BY_KIND = {
    "subject": subject_lines,
    "classmark": classmark_lines,
    "location": location_lines,
}

def lines_for(search, result):
    return BY_KIND[search.kind](result, search.wording.get("text"))
