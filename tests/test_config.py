""" 
    checks on the config driven dataset, so a new dataset really needs no new python

    run it with: python3 tests/test_config.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import config

CHECKS = []

def check(name):
    def keep(function):
        CHECKS.append((name, function))
        return function
    return keep

# writing a small dataset into its own directory, the way a real one is laid out
def temp_dataset(configText, files):
    directory = tempfile.mkdtemp()
    for fileName, contents in files.items():
        with open(os.path.join(directory, fileName), 'w') as dataFile:
            dataFile.write(contents)
    configPath = os.path.join(directory, "dataset.yaml")
    with open(configPath, 'w') as configFile:
        configFile.write(configText)
    return configPath

SIMPLE_FILES = {"people.csv": "person,pet\nAda,cat;dog\nGrace,fish\n"}
SIMPLE_CONFIG = """
name: Pets
tables:
  people:
    file: people.csv
links:
  pets_for_person: { table: people, from: person, to: pet }
  people_for_pet:  { table: people, from: pet,    to: person, lowercase: true }
searches:
  - kind: classmark
    label: person
    steps:
      - { follow: pets_for_person, as: locations }
      - { follow: people_for_pet, as: subjects }
"""

@check("a config loads its tables and links")
def _():
    dataset = config.load_config(temp_dataset(SIMPLE_CONFIG, SIMPLE_FILES))
    assert dataset.name == "Pets"
    assert list(dataset.tables) == ["people"]
    assert dataset.follow("pets_for_person", "Ada") == ["cat", "dog"]

@check("a link can lower case what it returns")
def _():
    dataset = config.load_config(temp_dataset(SIMPLE_CONFIG, SIMPLE_FILES))
    assert dataset.follow("people_for_pet", "cat") == ["ada"]

@check("file paths are read relative to the config, not the working directory")
def _():
    configPath = temp_dataset(SIMPLE_CONFIG, SIMPLE_FILES)
    here = os.getcwd()
    os.chdir(tempfile.mkdtemp())
    try:
        assert config.load_config(configPath).follow("pets_for_person", "Grace") == ["fish"]
    finally:
        os.chdir(here)

@check("a missing section is reported clearly")
def _():
    for broken, missing in [("name: x\nsearches: []\n", "tables"), ("name: x\ntables: {}\n", "searches")]:
        try:
            config.load_config(temp_dataset(broken, {}))
        except ValueError as error:
            assert missing in str(error), error
        else:
            raise AssertionError(f"expected a ValueError about {missing}")

@check("a search naming a link that doesn't exist is caught at load time")
def _():
    broken = SIMPLE_CONFIG.replace("follow: pets_for_person", "follow: nope")
    try:
        config.load_config(temp_dataset(broken, SIMPLE_FILES))
    except ValueError as error:
        assert "nope" in str(error), error
    else:
        raise AssertionError("expected a ValueError about the unknown link")

@check("choices are numbered from one, in config order")
def _():
    withChoices = SIMPLE_CONFIG + "    choices: [first, second, third]\n"
    dataset = config.load_config(temp_dataset(withChoices, SIMPLE_FILES))
    assert dataset.search_at(0).numbered_choices() == {1: "first", 2: "second", 3: "third"}

@check("a search falls back to a sensible question when none is given")
def _():
    dataset = config.load_config(temp_dataset(SIMPLE_CONFIG, SIMPLE_FILES))
    assert dataset.search_at(0).question == "Enter the person:"

@check("the shipped classmark dataset still loads and links up")
def _():
    dataset = config.load_default()
    assert dataset.follow("classmarks_for_subject", "American History") == ["E", "F"]
    assert dataset.follow("locations_for_classmark", "JX") == ["Top floor top left", "Bottom floor"]
    assert dataset.follow("subjects_for_classmark", "QH") == ["biology", "ecology"]
    assert [search.label for search in dataset.searches] == ["subject name or part-name", "classmark", "location"]

@check("wording from the config replaces the default sentence")
def _():
    from render import text
    from engine import query
    dataset = config.load_default()
    search = dataset.search_at(0)
    result = query.run(dataset, search, "Art")

    assert "Thank you for answering, Subject Art" in text.lines_for(search, result)[0]
    search.wording = {"text": {"subject_single": "{query} -> {classmark} @ {location}"}}
    assert text.lines_for(search, result)[0] == "Art -> N @ Top floor top left"

if __name__ == '__main__':
    failures = 0
    for name, function in CHECKS:
        try:
            function()
            print(f"  ok   {name}")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error or 'assertion failed'}")
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    raise SystemExit(1 if failures else 0)
