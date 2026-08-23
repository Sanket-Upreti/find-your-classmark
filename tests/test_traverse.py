""" 
    checks on the step walking, which is what makes a search describable in config

    run it with: python3 tests/test_traverse.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import traverse
from engine.dataset import Dataset, Link
from engine.table import Table

CHECKS = []

def check(name):
    def keep(function):
        CHECKS.append((name, function))
        return function
    return keep

# a tiny dataset: people own pets, pets live in baskets
def sample():
    pets = Table("pets", ["person", "pet"],
                 [{"person": ["Ada"], "pet": ["cat", "dog"]},
                  {"person": ["Grace"], "pet": ["fish"]},
                  {"person": ["Alan"], "pet": ["snake"]}])
    baskets = Table("baskets", ["pet", "basket"],
                    [{"pet": ["cat"], "basket": ["by the fire"]},
                     {"pet": ["cat"], "basket": ["on the sill"]},
                     {"pet": ["dog"], "basket": ["by the door"]},
                     {"pet": ["fish"], "basket": ["the tank"]}])
    return Dataset({"pets": pets, "baskets": baskets}, links={
        "pets_of": Link("pets_of", "pets", "person", "pet"),
        "basket_of": Link("basket_of", "baskets", "pet", "basket"),
    })

@check("one step, split into a row per value")
def _():
    rows = traverse.run_steps(sample(), [{"follow": "pets_of", "as": "pet", "each": True}], {"query": "Ada"})
    assert [row["pet"] for row in rows] == ["cat", "dog"]

@check("one step, gathered into a single field")
def _():
    rows = traverse.run_steps(sample(), [{"follow": "pets_of", "as": "pets"}], {"query": "Ada"})
    assert len(rows) == 1
    assert rows[0]["pets"] == ["cat", "dog"]

@check("a second step reads the field the first one set")
def _():
    steps = [{"follow": "pets_of", "as": "pet", "each": True},
             {"follow": "basket_of", "from": "pet", "as": "basket", "each": True}]
    rows = traverse.run_steps(sample(), steps, {"query": "Ada"})
    assert [(row["pet"], row["basket"]) for row in rows] == [
        ("cat", "by the fire"), ("cat", "on the sill"), ("dog", "by the door")]

@check("a row is dropped when a step finds nothing")
def _():
    steps = [{"follow": "pets_of", "as": "pet", "each": True},
             {"follow": "basket_of", "from": "pet", "as": "basket", "each": True}]
    assert traverse.run_steps(sample(), steps, {"query": "Alan"}) == []

@check("keep_empty keeps the row and marks the field as missing")
def _():
    steps = [{"follow": "pets_of", "as": "pet", "each": True},
             {"follow": "basket_of", "from": "pet", "as": "basket", "each": True, "keep_empty": True}]
    rows = traverse.run_steps(sample(), steps, {"query": "Alan"})
    assert rows == [{"query": "Alan", "pet": "snake", "basket": None}]

@check("an unknown starting value produces no rows at all")
def _():
    rows = traverse.run_steps(sample(), [{"follow": "pets_of", "as": "pet", "each": True}], {"query": "nobody"})
    assert rows == []

@check("a gathering step on an unknown value leaves the field empty")
def _():
    rows = traverse.run_steps(sample(), [{"follow": "pets_of", "as": "pets"}], {"query": "nobody"})
    assert rows == [{"query": "nobody", "pets": []}]

@check("the seed fields stay on every row")
def _():
    rows = traverse.run_steps(sample(), [{"follow": "pets_of", "as": "pet", "each": True}],
                              {"query": "Ada", "note": "kept"})
    assert all(row["note"] == "kept" for row in rows)

@check("a gathered field can be followed by the next step")
def _():
    steps = [{"follow": "pets_of", "as": "pets"},
             {"follow": "basket_of", "from": "pets", "as": "baskets"}]
    rows = traverse.run_steps(sample(), steps, {"query": "Ada"})
    assert rows[0]["baskets"] == ["by the fire", "on the sill", "by the door"]

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
