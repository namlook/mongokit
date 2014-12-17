=================
Using `Paginator`
=================

Implementing pagination in the project is made easy with ``mongokit.paginator.Paginator``.
``Paginator`` actually converts query-result-cursor into Paginator object and provides useful properties on it.

Using `Paginator` is consists of following two logical steps:

1. Importing `paginator.Paginator` module.
2. Applying it on your query-result-cursor.

Lets apply this steps with following detailed example.

-------------------

A detailed Example:
-------------------

Consider following as a sample model class:

>>> from mongokit import Document, Connection
...
... connection = Connection()
...
... @connection.register
... class Wiki(Document):
...
...    __collection__ = 'wiki'
...    __database__ = 'db_test_pagination'
...
...    structure = {
...        "name": unicode,  # name of wiki
...        "description": unicode,  # content of wiki
...        "created_by": basestring,  # username of user
...    }
...
...    required_fields = ['name', 'created_by']

Now let's consider that you have created 55 instances of class Wiki. And while querying you are getting all the instances in a query-result-cursor or resultant cursor.

.. Query to fetch all the 55 instances of Wiki class.

>>> wiki_collection = connection['db_test_pagination']
>>> total_wikis = wiki_collection.Wiki.find()
>>> total_wikis.count()
... 55

-----

**Now let's paginate the resultant cursor:** ``total_wikis``

As stated previously, we will first import the ``Paginator`` and then apply pagination on the resultant cursor.
 
>>> from mongokit.paginator import Paginator

>>> page_no = 2  # page number
>>> no_of_objects_pp = 10  # total no of objects or items per page

Keyword arguments required for ``Paginator`` class are as follows:
 1. ``cursor`` -- Cursor of a returned query   (``total_wikis`` in our example)
 2. ``page``   -- The page number requested    (``page_no`` in our example)
 3. ``limit``  -- The number of items per page (``no_of_objects_pp`` in our example) 

>>> paged_wiki = Paginator(total_wikis, page_no, no_of_objects_pp)

We had applied the pagination on ``total_wikis`` cursor and stored it's result in ``paged_wiki``, which is a Paginated object.

:Note:
	  The cursor (``total_wikis``) which we passed as an argument for ``Paginator``, also gets limit to ``no_of_objects_pp`` (``10`` in our case). And looping it would loop for ``no_of_objects_pp`` (``10``) times.

------

**Paginated object properties:**

.. We are going to work with `paged_wiki`, (no. of pages = 2) and (no. of item's per page = 10).
.. (Continuing the same above example.) 

Let's move ahead and try properties on ``paged_wiki``. There are total of 11 properties provided by mongokit, for the Paginated object. The properties that we can apply on ``paged_wiki`` are as follows:

property-1: **items** -- *Returns the paginated Cursor object.*

.. Note: As ``paged_wiki`` is ``Paginator`` object it cannot iterate directly. Doing so will give an error - "'Paginator' object is not iterable". To do so we have the property of ``.items``.

>>> for each in paged_wiki.items:
...     print each['name']
...     #  do your stuff ..

Above code will loop for 10 times to print the name of objects.


Property-2: **is_paginated** -- *Boolean value determining if the cursor has multiple pages*

>>> paged_wiki.is_paginated
... True


Property-3: **start_index** -- *int index of the first item on the requested page*

>>> paged_wiki.start_index
... 11

As the no. of items per page is ``10``, we got the result of second page's, starting item's index as ``11``.


Property-4: **end_index**  -- *int index of the last item on the requested page*

>>> paged_wiki.end_index
... 20

As the no. of items per page is ``10``, we got the result of second page's, ending item's index as ``20``.


Property-5: **current_page** -- *int page number of the requested page*

>>> paged_wiki.current_page
... 2


Property-6: **previous_page** -- *int page number of previous page with respect to current requested page*

>>> paged_wiki.previous_page
... 1


Property-7: **next_page** -- *int page number of next page with respect to current requested page*

>>> paged_wiki.next_page
... 3


Property-8: **has_next** -- *True or False if the Cursor has a next page*

>>> paged_wiki.has_next
... True


Property-9: **has_previous** -- *True or False if the Cursor has a previous page*

>>> paged_wiki.has_previous
... True


Property-10: **page_range** -- *list of the all page numbers (ascending order) in a list format*

>>> paged_wiki.page_range
... [1, 2, 3, 4, 5, 6]


Property-11: **num_pages** -- *int of the total number of pages*

>>> paged_wiki.num_pages
... 6


Property-12: **count** -- *int total number of items on the cursor*

>>> paged_wiki.count
... 55

It's same as that of ``total_wikis.count()``