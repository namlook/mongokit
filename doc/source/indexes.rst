Indexes
=======

Sometimes, it's desirable to have indexes on your dataset - especially unique ones.
In order to do that, you must fill the `indexes` attribute. The `indexes` attribute
is a list of dictionary with the following structure:

:"fields":
    # take a list of fields or a field name (required)
:"unique":
    should this index guarantee uniqueness? (optional, False by default)
:"ttl":
    (optional, 300 by default) time window (in seconds) during which this index will be recognized by subsequent calls to `ensure_index` - see pymongo documentation for `ensure_index` for details.
:"check:
    (optional, True by default) don't check if the field name is present in the structure. Useful if you don't know the field name.

Example:

>>> class MyDoc(Document):
...     structure = {
...         'standard':unicode,
...         'other':{
...             'deep':unicode,
...         },
...         'notindexed':unicode,
...     }
...     
...     indexes = [
...         {
...             'fields':['standard', 'other.deep'],
...             'unique':True,
...         },
...     ]

or if you have more than one index:

>>> class Movie(Document):
...     db_name = 'test'
...     collection_name = 'mongokit'
...     structure = {
...         'standard':unicode,
...         'other':{
...             'deep':unicode,
...         },
...         'alsoindexed':unicode,
...     }
... 
...     indexes = [
...         {
...             'fields':'standard',
...             'unique':True,
...         },
...         {
...             'fields': ['alsoindexed', 'other.deep']
...         },
...     ]


By default, the index direction is set to 1. You can change the direction by
passing a list of tuple.  Direction must be one of `INDEX_ASCENDING` (or 1),
`INDEX_DESCENDING` (or -1), `INDEX_OFF` (or 0), `INDEX_ALL` (or 2) or `INDEX_GEO2D` (or '2d'):

>>> class MyDoc(Document):
...     structure = {
...         'standard':unicode,
...         'other':{
...             'deep':unicode,
...         },
...         'notindexed':unicode,
...     }
...     
...     indexes = [
...         {
...             'fields':[('standard',INDEX_ASCENDING), ('other.deep',INDEX_DESCENDING)],
...             'unique':True,
...         },
...     ]

To prevent adding an index on the wrong field (misspelled for instance),
MongoKit will check by default the `indexes` descriptor. In some cases
may want to disable this. To do so, add ``"check":True``::

    >>> class MyDoc(Document):
    ...    structure = {
    ...        'foo': dict,
    ...        'bar': int
    ...    }
    ...    indexes = [
    ...        # I know this field is not in the document structure, don't check it
    ...        {'fields':['foo.title'], 'check':False}
    ...    ]

In this example, we index the field `foo.title` which is not explicitly specified in the structure.


