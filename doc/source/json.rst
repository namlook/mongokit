JSON support
------------

While building web application, you might want to create a REST API with JSON
support. Then, you may need to convert all your Documents into a JSON format
in order to pass it via the REST API. Unfortunately (or fortunately), MongoDB
supports field format which is not supported by JSON. This is the case for `datetime`
but also for all your `CustomTypes` you may have built and your embedded objects.

``Document`` supports the JSON import/export.

to_json()
~~~~~~~~~
is a simple method which exports your document into a JSON format::

    >>> # Python 3
    >>> class MyDoc(Document):
    ...         structure = {
    ...             "bla":{
    ...                 "foo":str,
    ...                 "bar":int,
    ...             },
    ...             "spam":[],
    ...         }
    >>> con.register([MyDoc])
    >>> mydoc = tutorial.MyDoc()
    >>> mydoc['_id'] = 'mydoc'
    >>> mydoc["bla"]["foo"] = "bar"
    >>> mydoc["bla"]["bar"] = 42
    >>> mydoc['spam'] = range(10)
    >>> mydoc.save()
    >>> json = mydoc.to_json()
    >>> json
    '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'

    >>> # Python 2
    >>> class MyDoc(Document):
    ...         structure = {
    ...             "bla":{
    ...                 "foo":unicode,
    ...                 "bar":int,
    ...             },
    ...             "spam":[],
    ...         }
    >>> con.register([MyDoc])
    >>> mydoc = tutorial.MyDoc()
    >>> mydoc['_id'] = u'mydoc'
    >>> mydoc["bla"]["foo"] = u"bar"
    >>> mydoc["bla"]["bar"] = 42
    >>> mydoc['spam'] = range(10)
    >>> mydoc.save()
    >>> json = mydoc.to_json()
    >>> json
    u'{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'


from_json()
~~~~~~~~~~~
To load a JSON string into a ``Document``, use the `from_json` class method::

    >>> # Python 3
    >>> class MyDoc(Document):
    ...     structure = {
    ...         "bla":{
    ...             "foo":str,
    ...             "bar":int,
    ...         },
    ...         "spam":[],
    ...     }
    >>> json = '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
    >>> mydoc = tutorial.MyDoc.from_json(json)
    >>> mydoc
    {'_id': 'mydoc', 'bla': {'foo': 'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}

    >>> # Python 2
    >>> class MyDoc(Document):
    ...     structure = {
    ...         "bla":{
    ...             "foo":unicode,
    ...             "bar":int,
    ...         },
    ...         "spam":[],
    ...     }
    >>> json = '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
    >>> mydoc = tutorial.MyDoc.from_json(json)
    >>> mydoc
    {'_id': 'mydoc', 'bla': {'foo': 'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}

Note that `from_json` will take care of all your embedded `Document`\ s if you used the `to_json()` method to
generate the JSON. Indeed, some extra value has to be set : the database and the collection where
the embedded document lives. This is added by the `to_json()` method::

    >>> # Python 3
    >>> class EmbedDoc(Document):
    ...     db_name = "test"
    ...     collection_name = "mongokit"
    ...     structure = {
    ...         "foo":str
    ...     }
    >>> class MyDoc(Document):
    ...    db_name = "test"
    ...    collection_name = "mongokit"
    ...    structure = {
    ...        "doc":{
    ...            "embed":EmbedDoc,
    ...        },
    ...    }
    ...    use_autorefs = True
    >>> con.register([EmbedDoc, MyDoc])

    >>> # Python 2
    >>> class EmbedDoc(Document):
    ...     db_name = "test"
    ...     collection_name = "mongokit"
    ...     structure = {
    ...         "foo":unicode
    ...     }
    >>> class MyDoc(Document):
    ...    db_name = "test"
    ...    collection_name = "mongokit"
    ...    structure = {
    ...        "doc":{
    ...            "embed":EmbedDoc,
    ...        },
    ...    }
    ...    use_autorefs = True
    >>> con.register([EmbedDoc, MyDoc])

Let's create an embedded doc::

    >>> # Python 3
    >>> embed = tutorial.EmbedDoc()
    >>> embed['_id'] = "embed"
    >>> embed['foo'] = "bar"
    >>> embed.save()

    >>> # Python 2
    >>> embed = tutorial.EmbedDoc()
    >>> embed['_id'] = u"embed"
    >>> embed['foo'] = u"bar"
    >>> embed.save()

and embed this doc to another doc::

    >>> # Python 3
    >>> mydoc = tutorial.MyDoc()
    >>> mydoc['_id'] = u'mydoc'
    >>> mydoc['doc']['embed'] = embed
    >>> mydoc.save()

    >>> # Python 2
    >>> mydoc = tutorial.MyDoc()
    >>> mydoc['_id'] = 'mydoc'
    >>> mydoc['doc']['embed'] = embed
    >>> mydoc.save()


Now let's see how the generated json looks like::

    >>> json = mydoc.to_json()
    >>> json
    u'{"doc": {"embed": {"_collection": "tutorial", "_database": "test", "_id": "embed", "foo": "bar"}}, "_id": "mydoc"}'

As you can see, two new fields have been added : `_collection` and `_database`
which represent respectively the collection and the database where the embedded
doc has been saved. That information is needed to generate the embedded
document. These are removed when calling the `from_json()` method::

    >>> # Python 3
    >>> mydoc = tutorial.MyDoc.from_json(json)
    >>> mydoc
    {u'doc': {u'embed': {u'_id': u'embed', u'foo': u'bar'}}, u'_id': u'mydoc'}

    >>> # Python 2
    >>> mydoc = tutorial.MyDoc.from_json(json)
    >>> mydoc
    {'doc': {'embed': {'_id': 'embed', 'foo': 'bar'}}, '_id': 'mydoc'}


An the embedded document is an instance of EmbedDoc::

    >>> isinstance(mydoc['doc']['embed'], EmbedDoc)
    True

ObjectId support
~~~~~~~~~~~~~~~~

`from_json()` can detect if the `_id` is an ``ObjectId`` instance or a simple string. When you serialize an object
with ``ObjectId`` instance to json, the generated json object looks like this::

    '{"_id": {"$oid": "..."}, ...}'

.. code-block:: pycon
    >>> embed = tutorial.EmbedDoc()
    >>> embed['foo'] = u"bar"
    >>> embed.save()
    >>> embed.to_json()
    u'{"foo": "bar", "_id": {"$oid": "4b5ec47390bce737e5000002"}}'

The "$oid" field is added to tell `from_json()` that '_id' is an ``ObjectId`` instance.
The same happens with embedded docs::

    >>> mydoc = tutorial.MyDoc()
    >>> mydoc['doc']['embed'] = embed
    >>> mydoc.save()
    >>> mydoc.to_json()
    {'doc': {'embed': {u'_id': ObjectId('4b5ec45090bce737cb000002'), u'foo': u'bar'}}, '_id': ObjectId('4b5ec45090bce737cb000003')}

