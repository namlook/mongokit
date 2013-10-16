#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2011, Nicolas Clairon
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
import datetime


class SchemaLessTestCase(unittest.TestCase):

    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')
        self.connection.drop_database('othertest')

    def test_simple_schemaless(self):
        @self.connection.register
        class MyDoc(Document):
            use_schemaless = True
            structure = {
                'foo': unicode,
                'bar': int,
            }

        doc = self.col.MyDoc()
        self.assertEqual('foo' in doc, True)
        self.assertEqual('bar' in doc, True)
        self.assertEqual('egg' in doc, False)
        doc['foo'] = u'bla'
        doc['bar'] = 3
        doc['egg'] = 9
        doc.save()
        
        doc = self.col.find_one()
        self.assertEqual('foo' in doc, True)
        self.assertEqual('bar' in doc, True)
        self.assertEqual('egg' in doc, True)

        doc = self.col.MyDoc.find_one()
        self.assertEqual('foo' in doc, True)
        self.assertEqual('bar' in doc, True)
        self.assertEqual('egg' in doc, True)
        doc['foo'] = 2
        self.assertRaises(SchemaTypeError, doc.save)
        doc.pop('foo')
        doc.pop('bar')
        doc.save()
        doc = self.col.MyDoc.find_one()
        self.assertEqual(doc.keys(), ['_id', 'egg'])

        doc = self.col.MyDoc({'_id':1, 'foo':u'bla'})
        doc.save()
        

    def test_schemaless_with_required(self):
        @self.connection.register
        class MyDoc(Document):
            use_schemaless = True
            structure = {
                'foo': unicode,
                'bar': int,
            }
            required_fields = ['foo']

        doc = self.col.MyDoc()
        self.assertEqual('foo' in doc, True)
        self.assertEqual('bar' in doc, True)
        self.assertEqual('egg' in doc, False)
        doc['foo'] = u'bla'
        doc['bar'] = 3
        doc['egg'] = 9
        doc.save()
        
        doc = self.col.MyDoc()
        doc.pop('foo')
        doc['bar'] = 3
        doc['egg'] = 9
        self.assertRaises(RequireFieldError, doc.save)
        
        doc = self.col.find_one()
        doc.pop('foo')
        self.col.save(doc)

        doc = self.col.MyDoc.find_one()
        self.assertEqual('foo' in doc, False)
        self.assertEqual('bar' in doc, True)
        self.assertEqual('egg' in doc, True)
        doc['bar'] = 2
        self.assertRaises(RequireFieldError, doc.save)
        doc['foo'] = u'arf'
        doc.save()

    def test_schemaless_no_structure(self):
        @self.connection.register
        class MyDoc(Document):
            use_schemaless = True

        doc = self.col.MyDoc()
        self.assertEqual('foo' in doc, False)
        self.assertEqual('bar' in doc, False)
        doc['_id'] = u'foo'
        doc['foo'] = u'bla'
        doc['bar'] = 3
        doc.save()
        
        doc = self.col.find_one()
        self.assertEqual('foo' in doc, True)
        self.assertEqual('bar' in doc, True)

        doc = self.col.MyDoc.find_one()
        self.assertEqual('foo' in doc, True)
        self.assertEqual('bar' in doc, True)
        self.assertEqual(doc, {'_id': 'foo', 'foo':'bla', 'bar':3})

    def test_schemaless_scenario2(self):
        @self.connection.register
        class User(Document):
            __collection__ = 'mongokit'
            __database__ = 'test'
            use_schemaless = True
            structure = {
                'name': unicode,
                'password': unicode,
                'last_name': unicode,
                'first_name': unicode,
                'email': unicode,
                'last_login': datetime.datetime,
            }
            use_dot_notation = True

        self.connection.User.collection.save({'name': u'namlook', 'password': u'test', 'email': u'n@c.com'})

        found_attribute = self.connection.User.find_one({'name':'namlook'})
        found_attribute.last_login = datetime.datetime.utcnow()
        found_attribute.save()
