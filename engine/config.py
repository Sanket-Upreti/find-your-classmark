""" building a Dataset out of a config file, so a new dataset needs no new python """
import os

from . import loaders
from .dataset import Dataset, Link, Search

try:
    import yaml
except ImportError:
    raise SystemExit("this needs PyYAML; install it with:  pip install -r requirements.txt")

# reading a config file and loading every table it names
def load_config(configPath):
    configPath = os.path.abspath(configPath)
    configDirectory = os.path.dirname(configPath)

    with open(configPath) as configFile:
        config = yaml.safe_load(configFile) or {}

    for required in ("tables", "searches"):
        if required not in config:
            raise ValueError(f"{configPath} is missing its '{required}' section")

    # file paths are written relative to the config, so the app works from any directory
    tables = {}
    for tableName, tableConfig in config["tables"].items():
        filePath = os.path.join(configDirectory, tableConfig["file"])
        tables[tableName] = loaders.load_table(filePath, tableName)

    links = {}
    for linkName, linkConfig in (config.get("links") or {}).items():
        links[linkName] = Link(
            name=linkName,
            table=linkConfig["table"],
            fromColumn=linkConfig["from"],
            toColumn=linkConfig["to"],
            lowercase=linkConfig.get("lowercase", False),
        )

    searches = [
        Search(
            kind=searchConfig["kind"],
            label=searchConfig["label"],
            question=searchConfig.get("question"),
            follow=searchConfig.get("follow"),
            choices=searchConfig.get("choices"),
            wording=searchConfig.get("wording"),
        )
        for searchConfig in config["searches"]
    ]

    # a link named by a search has to exist, otherwise the failure comes much later
    for search in searches:
        for linkName in search.follow:
            if linkName not in links:
                raise ValueError(f"search {search.kind!r} follows unknown link {linkName!r}")

    return Dataset(tables, links=links, searches=searches, name=config.get("name", ""))

# the dataset this app ships with
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "datasets", "classmark.yaml")

def load_default():
    return load_config(DEFAULT_CONFIG)
