from pymongo import Connection as PymongoConnection
from database import Database

class Connection(PymongoConnection):

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        self._mongo_docs = {}
    
    def register(self, obj_list):
        for obj in obj_list:
            self._mongo_docs[obj.__name__] = obj

    def __getattr__(self, key):
        return Database(self, key)


