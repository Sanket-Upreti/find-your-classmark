""" a set of loaded tables, the links between them, and what can be searched """

class Link:
    """ 'find the rows where fromColumn holds a value, then take their toColumn' """
    def __init__(self, name, table, fromColumn, toColumn, lowercase=False):
        self.name = name
        self.table = table
        self.fromColumn = fromColumn
        self.toColumn = toColumn
        # some wording expects lower case values; the config decides, not the code
        self.lowercase = lowercase

    def __repr__(self):
        return f"Link({self.name!r}: {self.table}.{self.fromColumn} -> {self.toColumn})"

class Search:
    """ one thing a user is allowed to search for """
    def __init__(self, kind, label, question=None, steps=None, choices=None, wording=None):
        self.kind = kind
        self.label = label
        self.question = question or f"Enter the {label}:"
        # the walk this search performs, declared by the config
        self.steps = list(steps or [])
        self.choices = list(choices or [])
        # per interface message overrides, e.g. {"text": {...}, "gui": {...}}
        self.wording = dict(wording or {})

    # the numbered list a user picks from, when this search offers choices
    def numbered_choices(self):
        return {number: choice for number, choice in enumerate(self.choices, start=1)}

    def __repr__(self):
        return f"Search({self.kind!r}, {self.label!r})"

class Summary:
    """ a count of how often each value appears in one column """
    def __init__(self, label, table, group):
        self.label = label
        self.table = table
        self.group = group

    def __repr__(self):
        return f"Summary({self.label!r}: {self.table}.{self.group})"

class Dataset:
    """ 
        holds tables by name and answers questions about them.
        it never mentions a subject, a class or a location; the config supplies those names
    """
    def __init__(self, tables, links=None, searches=None, summaries=None, name=""):
        self.name = name
        self.tables = dict(tables)
        self.links = dict(links or {})
        self.searches = list(searches or [])
        self.summaries = list(summaries or [])

    def table(self, name):
        return self.tables[name]

    # every row of a table whose column holds the searched value
    def rows_where(self, tableName, column, value):
        return self.table(tableName).rows_where(column, value)

    # the rows matching a value in one column, read back through another column
    def values_where(self, tableName, keyColumn, keyValue, valueColumn):
        table = self.table(tableName)
        collected = []
        for row in table.rows_where(keyColumn, keyValue):
            collected.extend(table.values(row, valueColumn))
        return collected

    # following a named link from the config
    def follow(self, linkName, value):
        link = self.links[linkName]
        collected = self.values_where(link.table, link.fromColumn, value, link.toColumn)
        if link.lowercase:
            collected = [found.lower() for found in collected]
        return collected

    # every value a column holds, for building a list of choices
    def distinct(self, tableName, column):
        return self.table(tableName).distinct(column)

    # the search a user picked, by its position in the config
    def search_at(self, position):
        return self.searches[position]
