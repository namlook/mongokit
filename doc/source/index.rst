MongoKit Documentation
======================

.. image:: https://github.com/namlook/mongokit/raw/devel/doc/mongokit_logo.png

|Build Status|

.. |Build Status| image:: https://travis-ci.org/namlook/mongokit.png

`MongoKit`_ is a python module that brings structured schema and validation layer
on top of the great pymongo driver. It has be written to be simpler and lighter
as possible with the KISS and DRY principles in mind.

.. _`MongoKit` : http://github.com/namlook/mongokit

Philosophy
==========

MongoKit is designed to be:

 * **Simple**: MongoKit use plain python type to describe document structure
 * **Fast**: MongoKit is fast but if you *really* need to be fast you have access to the raw pymongo layer without changing the API
 * **Powerful**: MongoKit brings many feature like document auto-reference, custom types or i18n support.

.. topic:: **Your data is clean**:

    "Tools change, not data". In order to follow this "credo", MongoKit won't
    add any information into your data saved into the database.
    So if you need to use other mongo tools or ODMs in other languages, your
    data won’t be polluted by MongoKit’s stuff.

Features
========

 * Schema validation (which uses simple python types for the declaration)
 * Schema-less feature
 * Dot notation
 * Nested and complex schema declaration
 * Untyped field support
 * Required fields validation
 * Default values
 * Custom validators
 * Cross database document reference
 * Random query support (which returns a random document from the database)
 * Inheritance and polymorphism support
 * Versionized document support (in beta stage)
 * Partial auth support (it brings a simple User model)
 * Operator for validation (currently : OR, NOT and IS)
 * Simple web framework integration
 * Import/export to json
 * I18n support
 * GridFS support
 * Document migration support

.. include:: quick_example.rst

Community
=========
Suggestions and patches are really welcome. If you find mistakes in the documentation
feel free to send a pull request or to contact us.

 * `Google Groups`_
 * `Github Issues`_
 * `Stackoverflow`_

.. _`Github Issues` : https://github.com/namlook/mongokit/issues
.. _`Google Groups` : http://groups.google.com/group/mongokit
.. _`Stackoverflow` : http://stackoverflow.com/questions/tagged/mongokit


Contents:
=========

.. toctree::
    :maxdepth: 3

    tutorial
    mapper
    crud
    features
    frameworks
    development
    api
    changelog
..    version_migration


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

