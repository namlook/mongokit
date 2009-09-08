-*- restructuredtext -*-

========
MongoKit
========

MongoDB_ is a great schema-less document oriented database. It have a lot of
driver for many langages (python, ruby, perl, java, php...).

.. _MongoDB : http://www.mongodb.org/display/DOCS/Home

MongoKit is a python module that brings structured schema and validation layer
on top of the great pymongo driver. It has be written to be simpler and lighter
as possible with the KISS and DRY principles in mind.

Features
========

 * schema validation (wich use simple python type for the declaration)
 * doted notation
 * nested and complex schema declaration
 * required fields validation
 * default values
 * custom validators
 * inheritance and polymorphisme support
 * versionized document support (still in alpha stage)
 * partial auth support (it brings a simple User model) 
 * Pylons Web Framework integration support
 * Operator for validation (currently : OR, NOT and IS)
 * Mongodb auth support

A quick example
===============

MongoDocument are enhanced python dictionnary with a ``validate()`` method.
A MongoDocument declaration look like that::

    >>> from mongokit import MongoDocument
    >>> import datetime

    >>> class BlogPost(MongoDocument):
    ...     db_name = 'test'
    ...     collection_name = 'tutorial'
    ...     structure = {
    ...             'title':unicode,
    ...             'body':unicode,
    ...             'author':unicode,
    ...             'date_creation':datetime.datetime,
    ...             'rank':int
    ...     }
    ...     required_fields = ['title','author', 'date_creation']
    ...     default_values = {'rank':0, 'date_creation':datetime.datetime.utcnow}
    ... 
    >>> blogpost = BlogPost()
    >>> blogpost['title'] = u'my title'
    >>> blogpost['body'] = u'a body'
    >>> blogpost['author'] = u'me'
    >>> blogpost.validate()
    >>> blogpost # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    {'body': u'a body', 'title': u'my title', 'date_creation': datetime.datetime(...), 'rank': 0, 'author': u'me'}
    >>> blogpost.save()
   
And you can use more complex structure::

    >>> class ComplexDoc(MongoDocument):
    ...     db_name = 'test'
    ...     collection_name = 'tutorial'
    ...     structure = {
    ...         "foo" : {"content":int},
    ...         "bar" : {
    ...             int:{unicode:int}
    ...         }
    ...     }
    ...     required_fields = ['foo.content', 'bar.$int']
     
Please, see the tutorial_ for more examples.

.. _tutorial : http://bitbucket.org/namlook/mongokit/wiki/Home

Suggestion and patches are really welcome. If you find mistakes in the documentation
(english is not my primary langage) feel free to contact me. You can find me (namlook) 
on the freenode #mongodb irc channel.

