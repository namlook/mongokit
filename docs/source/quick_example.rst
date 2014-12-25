Quick Example
=============

A quick example

Documents are enhanced python dictionaries with a `validate()` method.
A Document declaration look as follows::

    >>> # Python 3
    >>> from mongokit import *
    >>> import datetime

    >>> connection = Connection()

    >>> @connection.register
    ... class BlogPost(Document):
    ...     structure = {
    ...             'title':str,
    ...             'body':str,
    ...             'author':str,
    ...             'date_creation':datetime.datetime,
    ...             'rank':int
    ...     }
    ...     required_fields = ['title','author', 'date_creation']
    ...     default_values = {'rank':0, 'date_creation':datetime.datetime.utcnow}

    >>> # Python 2
    >>> from mongokit import *
    >>> import datetime

    >>> connection = Connection()

    >>> @connection.register
    ... class BlogPost(Document):
    ...     structure = {
    ...             'title':unicode,
    ...             'body':unicode,
    ...             'author':unicode,
    ...             'date_creation':datetime.datetime,
    ...             'rank':int
    ...     }
    ...     required_fields = ['title','author', 'date_creation']
    ...     default_values = {'rank':0, 'date_creation':datetime.datetime.utcnow}


We establish a connection and register our objects. ::

    >>> blogpost = con.test.example.BlogPost() # this uses the database "test" and the collection "example"
    >>> blogpost['title'] = 'my title'
    >>> blogpost['body'] = 'a body'
    >>> blogpost['author'] = 'me'
    >>> blogpost
    {'body': 'a body', 'title': 'my title', 'date_creation': datetime.datetime(...), 'rank': 0, 'author': 'me'}
    >>> blogpost.save()


Saving the object will call the `validate()` method.

And you can use a more complex structure as follows:

    >>>  @connection.register
    ...  class ComplexDoc(Document):
    ...     __database__ = 'test'
    ...     __collection__ = 'example'
    ...     structure = {
    ...         "foo" : {"content":int},
    ...         "bar" : {
    ...             'bla':{'spam':int}
    ...         }
    ...     }
    ...     required_fields = ['foo.content', 'bar.bla.spam']