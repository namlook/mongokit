Migration
=========

Let's say we have created a blog post which look like this::

    >>> from mongokit import *
    >>> con = Connection()

    class BlogPost(Document):
        structure = {
            "blog_post":{
                "title": unicode,
                "created_at": datetime,
                "body": unicode,
            }
        }
        default_values = {'blog_post.created_at':datetime.utcnow()}


Let's create some blog posts:

    >>> for i in range(10):
    ...     con.test.tutorial.BlogPost({'title':u'hello %s' % i, 'body': u'I the post number %s' % i}).save()

Now, development goes on and we add a 'tags' field to our `BlogPost`::

    class BlogPost(Document):
        structure = {
            "blog_post":{
                "title": unicode,
                "created_at": datetime,
                "body": unicode,
                "tags":  [unicode],
            }
        }
        default_values = {'blog_post.created_at':datetime.utcnow()}

We're gonna be in trouble when we'll try to save the fetched document because the
structures don't match::

    >>> blog_post = con.test.tutorial.BlogPost.find_one()
    >>> blog_post['blog_post']['title'] = u'Hello World'
    >>> blog_post.save()
    Traceback (most recent call last):
        ...
    StructureError: missed fields : ['tags']

If we want to fix this issue, we have to add the 'tags' field manually to all
`BlogPost` in the database::

    >>> con.test.tutorial.update({'blog_post':{'$exists':True}, 'blog_post.tags':{'$exists':False}},
    ...    {'$set':{'blog_post.tags':[]}}, multi=True)

and now we can save our blog_post::

    >>> blog_post.reload()
    >>> blog_post['blog_post']['title'] = u'Hello World'
    >>> blog_post.save()

Lazy migration
--------------

.. IMPORTANT::
    You cannot use this feature if `use_schemaless` is set to True

Mongokit provides a convenient way to set migration rules and apply them lazily.
We will explain how to do that using the previous example.

Let's create a `BlogPostMigration` which inherits from `DocumentMigration`::

    class BlogPostMigration(DocumentMigration):
        def migration01__add_tags_field(self):
            self.target = {'blog_post':{'$exists':True}, 'blog_post.tags':{'$exists':False}}
            self.update = {'$set':{'blog_post.tags':[]}}


How does it work? All migration rules are simple methods on the
`BlogPostMigration`. They must begin with `migration` and be numbered (so they
can be applied in certain order). The rest of the name should describe the
rule. Here, we create our first rule (`migration01`) which adds the 'tags' field
to our `BlogPost`.

Then you must set two attributes : `self.target` and `self.update`. There's both
mongodb regular query.

`self.target` will tell mongokit which document will match this rule. Migration 
will be applied to every document matching this query.

`self.update` is a mongodb update query with modifiers. This will describe
what updates should be applied to the matching document.

Now that our `BlogPostMigration` is created, we have to tell Mongokit to what
document these migration rules should be applied.  To do that, we have to set
the `migration_handler` in `BlogPost`::

    class BlogPost(Document):
        structure = {
            "blog_post":{
                "title": unicode,
                "created_at": datetime,
                "body": unicode,
                "tags": [unicode],
            }
        }
        default_values = {'blog_post.created_at':datetime.utcnow}
        migration_handler = BlogPostMigration

Each time an error is raised while validating a document, migration rules
are applied to the object and the document is reloaded.

.. CAUTION::
    If `migration_handler` is set then `skip_validation` is deactivated.
    Validation must be on to allow lazy migration.

Bulk migration
--------------

Lazy migration is useful if you have many documents to migrate, because update
will lock the database. But sometimes you might want to make a migration on few
documents and you don't want slow down your application with validation. You
should then use bulk migration.

Bulk migration works like lazy migration but `DocumentMigration` method must
start with `allmigration`. Because lazy migration adds document `_id` to
`self.target`, with bulk migration you should provide more information on
`self.target`. Here's an example of bulk migration, where we finally wan't to remove
the `tags` field from `BlogPost`::

    class BlogPost(Document):
        structure = {
            "blog_post":{
                "title": unicode,
                "creation_date": datetime,
                "body": unicode,
            }
        }
        default_values = {'blog_post.created_at':datetime.utcnow}

Note that we don't need to add the `migration_handler`, it is required only for
lazy migration.

Let's edit the `BlogPostMigration`::

    class BlogPostMigration(DocumentMigration):
        def allmigration01_remove_tags(self):
            self.target = {'blog_post.tags':{'$exists':True}}
            self.update = {'$unset':{'blog_post.tags':[]}}


To apply the migration, instantiate the `BlogPostMigration` and call the
`migrate_all` method::

    >>> migration = BlogPostMigration(BlogPost)
    >>> migration.migrate_all(collection=con.test.tutorial)


.. NOTE::
    Because `migration_*` methods are not called with `migrate_all()`, you
    can mix `migration_*` and `allmigration_*` methods.

Migration status
----------------

Once all your documents have been migrated, some migration rules could become
deprecated. To know which rules are deprecated, use the `get_deprecated` method::

    >>>> migration = BlogPostMigration(BlogPost)
    >>> migration.get_deprecated(collection=con.test.tutorial)
    {'deprecated':['allmigration01__remove_tags'], 'active':['migration02__rename_created_at']}

Here we can remove the rule `allmigration01__remove_tags`.


Advanced migration
------------------

Lazy migration
~~~~~~~~~~~~~~

Sometimes we might want to build more advanced migration. For instance, say you
want to copy a field value into another field, you can have access to the
current doc value via `self.doc`. In the following example, we want to add an
`update_date` field and copy the `creation_date` value into it::

    class BlogPostMigration(DocumentMigration):
        def migration01__add_update_field_and_fill_it(self):
            self.target = {'blog_post.update_date':{'$exists':False}, 'blog_post':{'$exists':True}}
            self.update = {'$set':{'blog_post.update_date': self.doc['blog_post']['creation_date']}}


Advanced and bulk migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to do the same thing with bulk migration, things are a little different::

    class BlogPostMigration(DocumentMigration):
        def allmigration01__add_update_field_and_fill_it(self):
            self.target = {'blog_post.update_date':{'$exists':False}, 'blog_post':{'$exists':True}}
            if not self.status:
                for doc in self.collection.find(self.target):
                    self.update = {'$set':{'blog_post.update_date': doc['blog_post']['creation_date']}}
                    self.collection.update(self.target, self.update, multi=True, safe=True)

In this example, the method `allmigration01__add_update_field_and_fill_it` will
directly modify the database and will be called by `get_deprecated()`. But calling
`get_deprecated()` should not arm the database so, we need to specify what portion
of the code must be ignored when calling `get_deprecated()`. This explains the
second line.
