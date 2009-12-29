from pymongo.database import Database as PymongoDatabase
from collection import Collection

class Database(PymongoDatabase):

    def __init__(self, *args, **kwargs):
        super(Database, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        return Collection(self, key)


