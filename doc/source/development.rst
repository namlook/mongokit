Development
===========

Tests
-----
Software Testing is necessary because we all make mistakes. Some of those mistakes are
unimportant, but some of them are expensive or dangerous. To avoid that we write tests.

Package Building/Testing
~~~~~~~~~~~~~~~~~~~~~~~~
Package building/testing is what `Travis CI`_ does. It would be better and easier to have your own travis for your fork.
But if you want to almost simulate what it does locally here is steps::

    $ # change master to the branch you want to test, also don't forget to change the username
    $ git clone --depth=50 --branch=master git://github.com/username/mongokit.git
    $ make setup
    $ make test

.. note:: It's quite important to have appropriate Python environment. If your python
   version on your system or virtual environment is 2.7 it doesn't tests for other versions
   of python and you should create different enthronement your self to run the tests.

.. _`Travis CI` : https://travis-ci.org/


Tox Automated Test
~~~~~~~~~~~~~~~~~~
Another way to run tests is to use `Tox`_. The advantage of using tox is its automation of
creating different virtual environment for python versions that are described in ``tox.ini``.
For MongoKit we have Python 2.7, Python 3.3, and Python 3.4.

.. _`Tox` : https://testrun.org/tox/latest/

Make sure you have installed Tox. And if you haven't::

    pip install tox

To run all the tests in all defined environments simply run::

    $ tox

and to run test in a specified environment use::

    $ tox -e py34

.. note:: py34 is defined in ``tox.ini``. Other options are py33 and py27.

Nose Test
~~~~~~~~~
But if you ant run tests partially or run a single test `Nose`_ is the way to go.`Nose`_
extends unittest to make testing easier. To run all the
tests use::

    $ nosetests

and if you wanted to run test for specific feature/file use::

    $ nosetests test/test_api.py

.. note:: For further instructions please view `selecting test`_.

.. _`Nose` : https://nose.readthedocs.org/en/latest/
.. _`selecting test` : http://nose.readthedocs.org/en/latest/usage.html#selecting-tests



Documentation
-------------
As a developer, it’s always important to have reliable documentation to guide your work.
Here is brief overview of how to create local documentation server:

Local Documentation Server
~~~~~~~~~~~~~~~~~~~~~~~~~~
While you are writing documentation or you have slow internet connection
it would be nice to have local documentation server.

To create local documentation server clone the repo::

    $ git clone https://github.com/namlook/mongokit.git
    $ cd mongokit

or you can download the zip file::

    $ wget https://github.com/namlook/mongokit/archive/master.zip
    $ unzip master.zip


and to compile::

    $ cd mongokit/docs
    $ make html
    sphinx-build -b html -d build/doctrees   source build/html
    Making output directory...
    ...
    build succeeded, 51 warnings.

Sphinx would create a build/html directory, go into it::

    $ cd build/html

Run python http server ::

    $ # Python 3
    $ python -m http.server
    Serving HTTP on 0.0.0.0 port 8000 ...

    $ # Python 2
    $ python -m SimpleHTTPServer
    Serving HTTP on 0.0.0.0 port 8000 ...

Open your browser and go to http://localhost:8000 or http://127.0.0.1:8000 .

.. note:: It would be better to open a new terminal as documentation http server,
   that way you can see changes simultaneously each time html directory was updated.

If some unwanted results was produced, the quick fix would be deleting the cached build and
remaking it::

    $ cd ../.. && pwd
    /home/user/mongokit/docs
    $ make clean
    rm -rf build/*
    $ make html
    sphinx-build -b html -d build/doctrees   source build/html
    Making output directory...
    ...
    build succeeded, 51 warnings.

.. seealso:: It worth mentioning a very nice package called `sphinx-autobuild`_ which
   automates all the steps described. What it does is that it watches a Sphinx directory and rebuild the
   documentation when a change is detected. Also includes a livereload enabled web server.

.. _`sphinx-autobuild` : https://github.com/GaretJax/sphinx-autobuild