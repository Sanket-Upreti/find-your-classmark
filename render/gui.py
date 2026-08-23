""" 
    putting a result onto the tkinter widgets;
    the widgets are handed in, so this file never has to import tkinter itself
"""
from .text import say

"""
    the wording, with the app's own sentences as the default.
    two of these read differently from the terminal's, which is why the
    window keeps its own set; a config can override any of them by name
"""
DEFAULT_WORDING = {
    "subject_not_found": "Thank you for answering, but no class was found for subject {query}",
    "location_header": "Thank you for answering, There are some classes and subjects taught in location {location}.\n Scroll inside the list to check more search results",
}

# the window falls back to the terminal's wording for everything it doesn't override
def _wording(configured):
    return {**DEFAULT_WORDING, **(configured or {})}

# joining several values into one readable phrase, or None when there are none
def _joined(values):
    return ", ".join(values) if values else None

# showing a single sentence on the result label
def _show_message(widgets, message):
    widgets['searchResult'].pack()
    widgets['searchResult'].config(text=message)

# starting a fresh list for results that don't fit in one sentence
def _start_list(widgets, pady):
    widgets['listbox'].delete(0, widgets['end'])
    widgets['listbox'].pack(pady=pady)

# adding one line to the list
def _add_to_list(widgets, message):
    widgets['listbox'].insert(widgets['end'], message)

# option 1, a subject search
def show_subject(result, widgets, wording=None):
    wording = _wording(wording)
    if not result.found:
        _show_message(widgets, say(wording, "subject_not_found", query=result.query))
        return

    # a single result reads better as one sentence, anything more gets listed
    if len(result.placements) == 1:
        placement = result.placements[0]
        if placement.location is None:
            _show_message(widgets, say(wording, "subject_single_no_location", query=result.query, classmark=placement.classmark))
        else:
            _show_message(widgets, say(wording, "subject_single", query=result.query, classmark=placement.classmark, location=placement.location))
        return

    _start_list(widgets, pady=2)
    widgets['listbox'].config(font=("Arial, 12"))
    for placement in result.placements:
        if placement.location is None:
            _add_to_list(widgets, say(wording, "subject_line_no_location", query=result.query, classmark=placement.classmark))
        else:
            _add_to_list(widgets, say(wording, "subject_line", query=result.query, classmark=placement.classmark, location=placement.location))

# option 2, a classmark search
def show_classmark(result, widgets, wording=None):
    wording = _wording(wording)
    locationFound = _joined(result.locations)
    subjectFound = _joined(result.subjects)

    # error handling when nothing was found, with the help of if...else
    if locationFound is None:
        if subjectFound is None:
            _show_message(widgets, say(wording, "classmark_none", query=result.query))
        else:
            _show_message(widgets, say(wording, "classmark_no_location", query=result.query, subjects=subjectFound))
        return

    if subjectFound is None:
        _show_message(widgets, say(wording, "classmark_no_subject", query=result.query, locations=locationFound))
    else:
        _show_message(widgets, say(wording, "classmark_found", query=result.query, subjects=subjectFound, locations=locationFound))

# option 3, a location search
def show_location(result, widgets, wording=None):
    wording = _wording(wording)
    if result.location is None:
        _show_message(widgets, say(wording, "location_invalid", query=result.query))
        return

    if not result.classes:
        _show_message(widgets, say(wording, "location_empty", query=result.query, location=result.location))
        return

    _show_message(widgets, say(wording, "location_header", query=result.query, location=result.location))
    _start_list(widgets, pady=20)
    for entry in result.classes:
        subjectFound = _joined(entry.subjects)
        if subjectFound is None:
            # a line for when some class out of many doesn't have a subject
            _add_to_list(widgets, say(wording, "location_line_no_subject", classmark=entry.classmark, location=result.location))
        else:
            _add_to_list(widgets, say(wording, "location_line", classmark=entry.classmark, location=result.location, subjects=subjectFound))

# picking the right wording for a search, so callers don't switch on the kind themselves
BY_KIND = {
    "subject": show_subject,
    "classmark": show_classmark,
    "location": show_location,
}

def show(search, result, widgets):
    return BY_KIND[search.kind](result, widgets, search.wording.get("gui"))
