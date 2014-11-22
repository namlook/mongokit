# MongoKit [![Build Status](https://travis-ci.org/namlook/mongokit.png)](https://travis-ci.org/namlook/mongokit.png)

[MongoDB](http://www.mongodb.org/display/DOCS/Home) is a great schema-less document oriented database. It has a lot of drivers for many languages (python, ruby, perl, java, php...).

MongoKit is a python module that brings a structured schema and validation layer
on top of the great pymongo driver. It has been written to be as simple and light
as possible with the KISS and DRY principles in mind.

## Philosophy

MongoKit is designed to be:

 * **simple**: MongoKit uses plain python types to describe document structure
 * **fast**: MongoKit is fast but if you *really* need to be fast you have
   access to the raw pymongo layer without changing the API
 * **powerful**: MongoKit brings many features like document auto-reference, 
   custom types or i18n support.

**Your data is clean:**

> "Tools change, not data". In order to follow this "credo", MongoKit won't
> add any information into your data saved into the database.
> So if you need to use other mongo tools or ODMs in other languages, your
> data won't be polluted by MongoKit's stuff.

## Features

 * schema validation (which uses simple python types for the declaration)
 * schema-less feature
 * dot notation
 * nested and complex schema declaration
 * untyped field support
 * required fields validation
 * default values
 * custom validators
 * cross database document reference
 * random query support (which returns a random document from the database)
 * inheritance and polymorphism support
 * versionized document support (in beta stage)
 * partial auth support (it brings a simple User model)
 * operator for validation (currently : OR, NOT and IS)
 * simple web framework integration
 * import/export to json
 * i18n support
 * GridFS support
 * document migration support

Go to the full [documentation](http://github.com/namlook/mongokit/wiki)

## A quick example

Documents are enhanced python dictionaries with a `validate()` method.
A Document declaration look as follows:

```python
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
...
```

We establish a connection and register our objects.

```python
>>> blogpost = con.test.example.BlogPost() # this uses the database "test" and the collection "example"
>>> blogpost['title'] = u'my title'
>>> blogpost['body'] = u'a body'
>>> blogpost['author'] = u'me'
>>> blogpost
{'body': u'a body', 'title': u'my title', 'date_creation': datetime.datetime(...), 'rank': 0, 'author': u'me'}
>>> blogpost.save()
```

Saving the object will call the `validate()` method.

And you can use a more complex structure as follows:

```python
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
```

Please see the [tutorial](https://github.com/namlook/mongokit/wiki/Tutorial) for more examples.

Suggestions and patches are really welcome. If you find mistakes in the documentation
(English is not my primary language) feel free to contact me. You can find me (namlook)
on the freenode #mongodb irc channel or on [twitter](http://twitter.com/namlook)


## Recent Change Log

### v0.9.1

 * fixed #131 - Use PEP8 recommendation for import
 * fixed tests (thanks @JohnBrodie and @bneron)
 * Added a Makefile for running tests in venv (thanks to @gulbinas)
 * fixed pep8 error (thanks to @gulbinas)
 * added support for MongoReplicaSetClient (thanks to @inabhi9)
 * Added `__getstate__` and `__setstate__` to DotedDict and i18nDotedDict. Problems appeared here when pickling mongokit documents due to apparent lack of these functions. (thanks to @petersng)
 * Fixed english mistake and typos into the documentation (thanks to @biow0lf, @SeyZ, @gianpaj and @1123)
 * Fixed inherited queries when accessing cursor by index (thanks to @asivokon)
 * changed the namespace on schema document errors (thanks to @rtjoseph11)

### v0.9.0

 * now MongoKit requires PyMongo >= 2.5
 * find_and_modify returns None if the query fails (thanks to @a1gucis)
 * Fix off-by-one error on SchemaDocument (thanks to @John Brodie)
 * Fix inherited queries (issue #106) (thanks to @effem-git)
 * Fix for serialization of nested structures with type validation (thanks to @LK4D4)
 * Remove unnecessary path arguments in to_json._convert_to_python (thanks to @Alexandr Morozov)
 * big refactorization by using multiple inheritance for DRYness (thanks to @liyanchang)
 * Add find_fulltext method for convenience (thanks to @astronouth7303) (not official and not documented yet)
 * Allow text indexes in document definitions (thanks to @astronouth7303)
 * Adding replica set support (thanks to @liyanchang)
 * Fix typos on README (thanks to @girasquid)
 * add pagination helper (not yet documented)(thanks to @jarrodb) https://github.com/namlook/mongokit/blob/master/mongokit/paginator.py

### v0.8.3

 * allow keyword arguments (like read_preferences, slave_okay, etc) to be set in Connection (thanks to @petersng)
 * Add find_and_modify again. It was removed by an unexpected rollback.
 * use MongoClient with MasterSlaveConnection

### v0.8.2

 * fix #101 - validators condition fix
 * fix #110 - support PyMongo >= 2.4 (import MongoClient) -- thanks to @mattbodman and @zavatskiy
 * Fixed some spelling/grammar (thanks to @gekitsuu)

### v0.8.1

 * support python 2.3
 * small updates to validation messages (Merge pull request #94 from unpluggd/master)
 * Fixes formatting error when throwing MaxDocumentSizeError in Document.validate() (Merge pull request #99 from apavlo/master)
 * Fixed typo when throwing MaxDocumentSizeError in validate() (thanks to Andy Pavlo)
 * added fix for unconditional access to `__wrap on cursors (thanks to David T. Lehmann)
 * added test for `__getitem__` on cursor with undefined `__wrap` (thanks to David T. Lehmann)
 * `__getitem__` on unwrapped cursor checks if `__wrap` is None (Merge pull request #97 from dtl/fix-getitem-on-unwrapped-cursor)
 * Add .travis.yml for Travis CI (http://travis-ci.org/) (Merge pull request #96 from msabramo/travis)
 * Fixed a very minor rendering issue in the docs (Merge pull request #95 from d0ugal/master)
 * Fixed rendering issue in the docs. (thanks to Dougal Matthews)
 * tweaked the error messages in validation for missing and unknown fields to aid in debugging projects (thanks to Phillip B Oldham)

### v0.8.0

 * Add spec file for rpm-based distributions (Merge pull request #63 from linuxnow/master)
 * change document size limitation for mongodb 1.8 or later. Thanks to Aleksey Sivokon (Merge pull request #74 from key/master)
 * validation of "" for an int (Merge pull request #79 from barnybug/master)
 * Fix exception when loading documents with a custom type field missing (Merge pull request #80 from barnybug/master)
 * Big documentation restructuring made by Sean Lynch (Merge pull request #82 from sean-lynch/master)
 * Using rename no longer causes migrations throw an exception (Merge pull request #86 from matthewh/master)
 * Some test is modified and added tox (Merge pull request #91 from aircastle/modifiytest)
 * Replace pymongo.objectid with bson.objectid (Merge pull request #88 from behackett/master)
 * Added Support for additional keyword-arguments for index-creation (Merge pull request #85 from mfelsche/master)
 * Remove anyjson dependency and use builtin json instead

Thank you all for all your patches !

### v0.7.2

 * add inherited queries support (please see http://github.com/namlook/mongokit/wiki/Inherited-queries for more details)


### v0.7.1

 * change MongokitMasterSlaveConnection to MasterSlaveConnection for consistency
 * fix #57 -- support pymongo > 1.9 in grid.py
 * fix #45 -- remove automatic index creation
 * fix #43 -- slicing a cursor should return a mongokit document, not dict
 * Dont try to convert None struct to json (patch from @mLewisLogic thanks !)
 * fix schemaless issue (thanks to Mihai Pocorschi for reporting it)

### v0.7

 * add `use_schemaless` feature ! please see the documentation for more information
 * Add equality test for mongokit operators (thanks to @allancaffee)
    This allows developers to write unit tests on the structure
    of their document classes when operators are used
 * roll back find_and_modify for master branch (need pymongo 1.10 for that)
 * many documentation fixes
 * fix #55 -- Bug in VersionedDocument remove() method
 * fix #53 -- Fixed a few spelling errors in README
 * fix #52 -- Advanced bulk migration docs example is broken
 * fix #51 -- pymongo.dbref is deprecated, use bson.dbref instead
 * fix #49 -- Can't specify default values for lists of embedded objects
 * fix #48 -- uuid.UUID support
 * fix #41 -- add basestring to authorized types
 * fix #40 -- Made some enhancements
 * fix #39 -- KeyError when saving partially loaded documents
 * fix #34 -- add find_and_modify method to Document
 * fix #32 -- allow the structure to be empty (was: document.to_json())
 * fix #24 -- Don't handle `__database__` and `__collection__` attributes for virtual documents
