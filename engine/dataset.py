""" a set of loaded tables, and the links between them """
from . import loaders

class Dataset:
    """ 
        holds tables by name and answers questions about them.
        this class stays generic; it never mentions a subject, class or location
    """
    def __init__(self, tables):
        self.tables = dict(tables)

    def table(self, name):
        return self.tables[name]

    # every row of a table whose column holds the searched value
    def rows_where(self, tableName, column, value):
        return self.table(tableName).rows_where(column, value)

    """ 
        following a link: find the rows matching a value in one column, 
        then collect what those rows hold in another column
    """
    def values_where(self, tableName, keyColumn, keyValue, valueColumn):
        table = self.table(tableName)
        collected = []
        for row in table.rows_where(keyColumn, keyValue):
            collected.extend(table.values(row, valueColumn))
        return collected

    # every value a column holds, for building a list of choices
    def distinct(self, tableName, column):
        return self.table(tableName).distinct(column)

class ClassmarkDataset(Dataset):
    """ 
        the only place that knows this app's tables are called 'subjects' and 'rooms', 
        and that their columns are subject/classmark/location.
        a config file replaces this class in stage 3
    """
    SUBJECTS = "subjects"
    ROOMS = "rooms"

    def classmarks_for_subject(self, subject):
        return self.values_where(self.SUBJECTS, "subject", subject, "classmark")

    def locations_for_classmark(self, classmark):
        return self.values_where(self.ROOMS, "classmark", classmark, "location")

    def subjects_for_classmark(self, classmark):
        # lowercased to keep the wording the app has always used; drop .lower() to show real casing
        return [subject.lower() for subject in
                self.values_where(self.SUBJECTS, "classmark", classmark, "subject")]

    def classmarks_in_location(self, location):
        # lowercased to keep the wording the app has always used; drop .lower() to show real casing
        return [classmark.lower() for classmark in
                self.values_where(self.ROOMS, "location", location, "classmark")]

# building the dataset out of the two files the app ships with
def load_dataset(classmarkFile='classmark_location.csv', subjectFile='subject_classmark.csv'):
    return ClassmarkDataset({
        ClassmarkDataset.ROOMS: loaders.load_table(classmarkFile, ClassmarkDataset.ROOMS),
        ClassmarkDataset.SUBJECTS: loaders.load_table(subjectFile, ClassmarkDataset.SUBJECTS),
    })
