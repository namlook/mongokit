Using DBRef
===========

MongoKit has optional support for MongoDB's autoreferencing/dbref 
features. Autoreferencing allows you to embed MongoKit objects/instances
inside another MongoKit object.  With autoreferencing enabled, MongoKit and
the pymongo driver will translate the embedded MongoKit object
values into internal MongoDB DBRefs.  The (de)serialization is
handled automatically by the pymongo driver.

.. _autoref_sample: http://github.com/mongodb/mongo-python-driver/blob/cd47b2475c5fe567e98696e6bc5af3c402891d12/examples/auto_reference.py

Autoreferences allow you to pass other Documents as values.
pymongo_.  (with help from MongoKit) automatically
translates these object values into DBRefs before persisting to
Mongo.  When fetching, it translates them back, so that you have
the data values for your referenced object. See the autoref_sample_. for 
further details/internals  on this driver-level functionality. As for 
enabling it in your own MongoKit code, simply define the following class 
attribute upon your Document subclass::

        use_autorefs = True

With autoref enabled, MongoKit's connection management will attach the
appropriate BSON manipulators to your document's connection handles.  We 
require you to explicitly enable autoref for two reasons:

    * Using autoref and it's BSON manipulators (As well as DBRefs) can carry a performance penalty.  We opt for performance and simplicity first, so you must explicitly enable autoreferencing.
    * You may not wish to use auto-referencing in some cases where you're using DBRefs.

Once you have autoref enabled, MongoKit will allow you to define
any valid subclass of Document as part of your document
structure.  **If your class does not define `use_autorefs` as 
True, MongoKit's structure validation code will REJECT your 
structure.**

A detailed example
------------------

First let's create a simple doc:

>>> class DocA(Document):
...    structure = {
...        "a":{'foo':int},
...        "abis":{'bar':int},
...    }
...    default_values = {'a.foo':2}
...    required_fields = ['abis.bar']

>>> con.register([DocA])
>>> doca = tutorial.DocA()
>>> doca['_id'] = 'doca'
>>> doca['abis']['bar'] = 3
>>> doca.save()

Now, let's create a DocB which have a reference to DocA:

>>> class DocB(Document):
...    structure = {
...        "b":{"doc_a":DocA},
...    }
...    use_autorefs = True

Note that to be able to specify a Document into the structure, we must
set `use_autorefs` as `True`.

>>> con.register([DocB])
>>> docb = tutorial.DocB()

The default value for an embedded doc is None:

>>> docb
{'b': {'doc_a': None}}

The validation acts as expected:

>>> docb['b']['doc_a'] = 4
>>> docb.validate()
Traceback (most recent call last):
...
SchemaTypeError: b.doc_a must be an instance of DocA not int

>>> docb['_id'] = 'docb'
>>> docb['b']['doc_a'] = doca
>>> docb 
{'b': {'doc_a': {'a': {'foo': 2}, 'abis': {'bar': 3}, '_id': 'doca'}}, '_id': 'docb'}

Note that the reference can not only be cross collection but also cross database. So, it doesn't matter
where you save the DocA object as long as it can be fetch with the same connection.

Now the interesting part. If we change a field in an embedded doc, the change will be done
for all DocA which have the same '_id':

>>> docb['b']['doc_a']['a']['foo'] = 4
>>> docb.save()

>>> doca['a']['foo']
4

Required fields are also supported in embedded documents.
Remember DocA have the 'abis.bar' field required. If we set it to None
via the docb document, the RequireFieldError is raised:

>>> docb['b']['doc_a']['abis']['bar'] = None
>>> docb.validate()
Traceback (most recent call last):
...
RequireFieldError: abis.bar is required

About cross-database references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pymongo's DBRef doesn't take a database by default so MongoKit needs this
information to fetch the correct Document.

An example is better than thousand words. Let's create an ``EmbedDoc`` and a ``Doc`` object::

>>> class EmbedDoc(Document):
...   structure = {
...       "foo": unicode,
...   }

>>> class Doc(Document):
...   use_dot_notation=True
...   use_autorefs = True
...   structure = {
...       "embed": EmbedDoc,
...   }
>>> con.register([EmbedDoc, Doc])

>>> embed = tutorial.EmbedDoc()
>>> embed['foo'] = u'bar'
>>> embed.save()

Now let's insert a raw document with a DBRef but without specifying the database:

>>> raw_doc = {'embed':DBRef(collection='tutorial', id=embed['_id'])}
>>> doc_id = tutorial.insert(raw_doc)

Now what append when we want to load the data:

>>> doc = tutorial.Doc.get_from_id(doc_id)
Traceback (most recent call last):
...
RuntimeError: It appears that you try to use autorefs. I found a DBRef without database specified.
 If you do want to use the current database, you have to add the attribute `force_autorefs_current_db` as True. Please see the doc for more details.
 The DBRef without database is : DBRef(u'tutorial', ObjectId('4b6a949890bce72958000002'))

This mean that you may load data which could have been generated by map/reduce or raw data (like fixtures for instance)
and the database information is not set into the DBRef. The error message tells you that you can add turn the
`force_autorefs_current_db` as True to allow MongoKit to use the current collection by default (here 'test')::

>>> tutorial.database.name
u'test'

NOTE: You have to be very careful when you enable this option to be sure that you are using the correct database.
If you expect some strange behavior (like not document found), you may look at this first.

Reference and dereference
~~~~~~~~~~~~~~~~~~~~~~~~~

You can get the dbref of a document with the `get_dbref()` method. The
`dereference()` allow to get a Document from a dbref. You can pass a Document
to tell mongokit to what model it should dereferenced::

    >>> dbref = mydoc.get_dbref()
    >>> raw_doc = con.mydb.dereference(dbref) # the result is a regular dict
    >>> doc = con.mydb.dereference(dbref, MyDoc) # the result is a MyDoc instance
