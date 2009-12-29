from pymongo.collection import Collection as PymongoCollection

class Collection(PymongoCollection):

    indexes = []

    def __init__(self, *args, **kwargs):
        super(Collection, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        if key in self.database.connection._mongo_docs:
            return self.database.connection._mongo_docs[key](collection=self)
        if key in self.__dict__:
            return self.__dict__[key]

    def generate_index(self):
        # creating index if needed
        for index in self.indexes:
            unique = False
            if 'unique' in index.keys():
                unique = index['unique']
            ttl = 300
            if 'ttl' in index.keys():
                ttl = index['ttl']
            if isinstance(index['fields'], dict):
                fields = [(name, direction) for (name, direction) in sorted(index['fields'].items())]
            elif hasattr(index['fields'], '__iter__'):
                if isinstance(index['fields'][0], tuple):
                    fields = [(name, direction) for name, direction in index['fields']]
                else:
                    fields = [(name, 1) for name in index['fields']]
            else:
                fields = index['fields']
            log.debug('Creating index for %s' % index['fields'])
            self.ensure_index(fields, unique=unique, ttl=ttl)


    def get_from_id(self, id):
        """
        return the document wich has the id
        """
        return self.find_one({"_id":id})


