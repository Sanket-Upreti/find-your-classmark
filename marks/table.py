""" a loaded table; nothing here knows what the columns mean """

class Table:
    """ 
        rows of a tabular file, one dictionary per row: column name -> list of values.
        every cell is a list because a cell is allowed to hold more than one value
    """
    def __init__(self, name, columns, rows):
        self.name = name
        self.columns = list(columns)
        self.rows = list(rows)
        # lookups are built the first time a column is searched, then kept
        self._indexes = {}

    def _index_for(self, column):
        if column not in self._indexes:
            index = {}
            for row in self.rows:
                for value in row.get(column, []):
                    index.setdefault(value.lower(), []).append(row)
            self._indexes[column] = index
        return self._indexes[column]

    # every row whose column holds the searched value, in file order
    def rows_where(self, column, value):
        return self._index_for(column).get(str(value).lower(), [])

    # the values one row holds in a column
    def values(self, row, column):
        return row.get(column, [])

    # every value that appears in a column, in file order, without repeats
    def distinct(self, column):
        seen = []
        for row in self.rows:
            for value in row.get(column, []):
                if value not in seen:
                    seen.append(value)
        return seen

    def __repr__(self):
        return f"Table({self.name!r}, columns={self.columns}, rows={len(self.rows)})"
