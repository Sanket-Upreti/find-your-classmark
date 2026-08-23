""" 
    putting a result onto the tkinter widgets;
    the widgets are handed in, so this file never has to import tkinter itself
"""

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
def show_subject(result, widgets):
    if not result.found:
        _show_message(widgets, f"Thank you for answering, but no class was found for subject {result.query}")
        return

    # a single result reads better as one sentence, anything more gets listed
    if len(result.placements) == 1:
        placement = result.placements[0]
        if placement.location is None:
            _show_message(widgets, f"Thank you for answering, but no location was found for subject {result.query}")
        else:
            _show_message(widgets, f"Thank you for answering, Subject {result.query} happens on class {placement.classmark} which is located in {placement.location}")
        return

    _start_list(widgets, pady=2)
    widgets['listbox'].config(font=("Arial, 12"))
    for placement in result.placements:
        if placement.location is None:
            _add_to_list(widgets, f"No location was found for subject {placement.classmark}")
        else:
            _add_to_list(widgets, f"Subject {result.query} happens on class {placement.classmark} which is located in {placement.location}")

# option 2, a classmark search
def show_classmark(result, widgets):
    locationFound = _joined(result.locations)
    subjectFound = _joined(result.subjects)

    # error handling when nothing was found, with the help of if...else
    if locationFound is None:
        if subjectFound is None:
            _show_message(widgets, f"Thank you for answering, but no location or subject was found for class {result.query}")
        else:
            _show_message(widgets, f"Thank you for answering, but no location was found for class {result.query} which has {subjectFound} running on it")
        return

    if subjectFound is None:
        _show_message(widgets, f"Thank you for answering, but no subject was found for class {result.query} which is in {locationFound}")
    else:
        _show_message(widgets, f"Thank you for answering, Subject {subjectFound} happens on class {result.query} which is located in {locationFound}")

# option 3, a location search
def show_location(result, widgets):
    if result.location is None:
        _show_message(widgets, f"Thank you for answering, but no class, subject or location was found for your search {result.query}")
        return

    if not result.classes:
        _show_message(widgets, f"Thank you for answering, but no class, subject or location was found for your search {result.location}. Please make sure your location is similar to the options provided")
        return

    _show_message(widgets, f"Thank you for answering, There are some classes and subjects taught in location {result.location}.\n Scroll inside the list to check more search results")
    _start_list(widgets, pady=20)
    for entry in result.classes:
        subjectFound = _joined(entry.subjects)
        if subjectFound is None:
            # a line for when some class out of many doesn't have a subject
            _add_to_list(widgets, f"No subject was found for class {entry.classmark} in location {result.location}")
        else:
            _add_to_list(widgets, f"Subject {subjectFound} happens on class {entry.classmark} which is located in {result.location}")
