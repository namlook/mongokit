#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2010, Nicolas Clairon
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University of California, Berkeley nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from mongokit import *
from pymongo.objectid import ObjectId
from datetime import datetime


class MigrationTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']

        # create initial blog post class
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                }
            }
            default_values = {'blog_post.created_at':datetime.utcnow()}
        self.connection.register([BlogPost])

        # creating some blog posts
        for i in range(10):
            blog_post = self.col.BlogPost()
            blog_post['blog_post']['title'] = u'hello %s' % i
            blog_post['blog_post']['body'] = u'I the post number %s' % i
            blog_post.save()
       
    def tearDown(self):
        self.connection.drop_database('test')
        self.connection.drop_database('othertest')

    def test_simple_doc_migration(self):
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                    "tags":  [unicode],
                }
            }
        self.connection.register([BlogPost])
        bp =  self.col.BlogPost.find_one()
        self.assertRaises(StructureError, bp.validate)

        # creating blog post migration
        class BlogPostMigration(DocumentMigration):
            def migration01_add_tags(self):
                self.target = {'blog_post':{'$exists':True}}
                self.update = {'$set':{'blog_post.tags':[]}}

        # migrate a blog post
        migration = BlogPostMigration(BlogPost)
        migration.migrate(bp)
        bp = self.col.BlogPost.get_from_id(bp['_id'])
        bp.validate()

    def test_simple_all_migration(self):
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                    "tags":  [unicode],
                }
            }
        self.connection.register([BlogPost])
        bp =  self.col.BlogPost.find_one()
        self.assertRaises(StructureError, bp.validate)
        # creating blog post migration
        class BlogPostMigration(DocumentMigration):
            def allmigration01_add_tags(self):
                self.target = {'blog_post':{'$exists':True}, 'blog_post.tags':{'$exists':False}}
                self.update = {'$set':{'blog_post.tags':[]}}
        # migrate all blog posts
        migration = BlogPostMigration(BlogPost)
        assert migration.get_deprecated(self.col) == {'active': ['allmigration01_add_tags'], 'deprecated': []}
        migration.migrate_all(self.col)
        assert migration.get_deprecated(self.col) == {'active': [], 'deprecated': ['allmigration01_add_tags']}
        bp =  self.col.BlogPost.find_one()
        bp.validate()

    def test_simple_all_migration_with_bad_update(self):
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                    "tags":  [unicode],
                }
            }
        self.connection.register([BlogPost])
        bp =  self.col.BlogPost.find_one()
        self.assertRaises(StructureError, bp.validate)

        # creating blog post migration
        class BlogPostMigration(DocumentMigration):
            def allmigration01_add_tags(self):
                self.target = {'blog_post':{'$exists':True}}
                self.update = {'$set':{'tags':[]}}
        migration = BlogPostMigration(BlogPost)
        self.assertRaises(UpdateQueryError, migration.migrate_all, self.col)
        
    def test_lazy_migration(self):
        # creating blog post migration
        class BlogPostMigration(DocumentMigration):
            def migration01__add_tags(self):
                self.target = {'blog_post':{'$exists':True}}
                self.update = {'$set':{'blog_post.tags':[]}}
            def migration02__rename_create_at_to_creation_date(self):
                self.target = {'blog_post.created_at':{'$exists':True}}
                self.update = {
                  '$set':{'blog_post.creation_date': self.doc['blog_post']['created_at']},
                  '$unset':{'blog_post.created_at':1}
                }
        # update blog post class
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                    "tags": [unicode],
                }
            }
            migration_handler = BlogPostMigration
        self.connection.register([BlogPost])

        # fetching a blog post
        bp = self.col.BlogPost.find_one()
        created_at = bp['blog_post']['created_at']
        assert 'tags' not in bp['blog_post']

        # via lazzy migration, the following line don't raise errors
        bp['blog_post']['title'] = u'Hello big World'
        bp.save()
        assert bp['blog_post']['title'] == 'Hello big World', bp['blog_post']

        # the field 'tags' has been added automatically
        assert 'tags' in bp['blog_post'], bp
        assert 'creation_date' in bp['blog_post'], bp
        assert bp['blog_post']['creation_date'] == created_at

    def test_lazy_migration_with_skip_validation(self):
        # creating blog post migration
        class BlogPostMigration(DocumentMigration):
            def migration01__add_tags(self):
                self.target = {'blog_post':{'$exists':True}}
                self.update = {'$set':{'blog_post.tags':[]}}
            def migration02__rename_create_at_to_creation_date(self):
                self.target = {'blog_post.created_at':{'$exists':True}}
                self.update = {
                  '$set':{'blog_post.creation_date': self.doc['blog_post']['created_at']},
                  '$unset':{'blog_post.created_at':1}
                }
        # update blog post class
        class BlogPost(Document):
            skip_validation = True
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                    "tags": [unicode],
                }
            }
            migration_handler = BlogPostMigration
        self.connection.register([BlogPost])

        # fetching a blog post
        bp = self.col.BlogPost.find_one()
        created_at = bp['blog_post']['created_at']
        assert 'tags' not in bp['blog_post']

        # via lazzy migration, the following line don't raise errors
        bp.save()

        # the field 'tags' has been added automatically
        assert 'tags' in bp['blog_post'], bp
        assert 'creation_date' in bp['blog_post'], bp
        assert bp['blog_post']['creation_date'] == created_at


    def test_lazy_migration_with_autorefs(self):
        # creating blog post migration
        class BlogPostMigration(DocumentMigration):
            def migration01__add_tags(self):
                self.target = {'blog_post':{'$exists':True}}
                self.update = {'$set':{'blog_post.tags':[]}}
            def migration02__rename_create_at_to_creation_date(self):
                if 'created_at' in self.doc['blog_post']:
                    self.target = {'blog_post.created_at':{'$exists':True}}
                    self.update = {
                      '$set':{'blog_post.creation_date': self.doc['blog_post']['created_at']},
                      '$unset':{'blog_post.created_at':1}
                    }
        # update blog post class
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "title": unicode,
                    "created_at": datetime,
                    "body": unicode,
                    "tags": [unicode],
                }
            }
            migration_handler = BlogPostMigration
        self.connection.register([BlogPost])

        class A(Document):
            structure = {
                "a":{'blogpost':BlogPost},
            }
            use_autorefs = True
        self.connection.register([A])

        for doc in self.col.BlogPost.find():
            a = self.col.A()
            a['a']['blogpost'] = doc
            a.save()
            assert 'creation_date' in a['a']['blogpost']['blog_post'], a

        class AMigration(DocumentMigration):
            def migration01__add_bar(self):
                self.target = {'a':{'$exists':True}, 'a.bar':{'$exists':False}}
                self.update = {'$set':{'a.bar':None}}
        class A(Document):
            structure = {
                "a":{'blogpost':BlogPost, 'bar':int},
            }
            use_autorefs = True
            migration_handler = AMigration
        self.connection.register([A])
        
        a = self.col.A.fetch().next()
        assert 'bar' not in a['a'], a
        assert 'creation_date' in a['a']['blogpost']['blog_post'], a
        a.validate()
        assert 'bar' in a['a'], a

