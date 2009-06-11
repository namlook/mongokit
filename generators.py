
class MongoDocumentCursor(object):
    def __init__(self, cursor, cls):
        self._cursor = cursor
        self._class_object = cls

    def where(self, *args, **kwargs):
        return self.__class__(self._cursor.where(*args, **kwargs), self._class_object)

    def sort(self, *args, **kwargs):
        return self.__class__(self._cursor.sort(*args, **kwargs), self._class_object)

    def limit(self, *args, **kwargs):
        return self.__class__(self._cursor.limit(*args, **kwargs), self._class_object)

    def hint(self, *args, **kwargs):
        return self.__class__(self._cursor.hint(*args, **kwargs), self._class_object)

    def count(self, *args, **kwargs):
        return self._cursor.count(*args, **kwargs)
        
    def explain(self, *args, **kwargs):
        return self._cursor.explain(*args, **kwargs)

    def next(self, *args, **kwargs):
        return self._class_object(self._cursor.next(*args, **kwargs), process_signals=False)

    def skip(self, *args, **kwargs):
        return self.__class__(self._cursor.skip(*args, **kwargs), self._class_object)

    def __iter__(self, *args, **kwargs):
        for obj in self._cursor:
            yield self._class_object(obj, process_signals=False)

