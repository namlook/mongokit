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

from mongokit import Document, Connection

class InheritedQueriesTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(safe=True)
        self.col = self.connection['test']['mongolite']
        
    def tearDown(self):
        self.connection.drop_database('test')

    def test_use_inherited_queries(self):
        @self.connection.register
        class A(Document):
            __database__ = 'test'
            __collection__ = 'mongolite'
            structure = {
                '_type': unicode,
                'a':{
                    'foo': int,
                    'bar': unicode,
                }
            }

        @self.connection.register
        class B(A):
            structure = {
                'b': {
                    'eggs': float,
                }
            }

        doc_a = self.connection.A()
        self.assertEqual(doc_a['_type'], 'A')
        doc_a['a']['foo'] = 3
        doc_a['a']['bar'] = u'Hello World'
        doc_a.save()

        doc_b = self.connection.B()
        self.assertEqual(doc_b['_type'], 'B')
        doc_b['a']['foo'] = 42
        doc_b['a']['bar'] = u'bye bye'
        doc_b['b']['eggs'] = 3.14
        doc_b.save()

        self.assertTrue(isinstance(self.connection.A.find_one({'_id':doc_b['_id']}), B))
        self.assertTrue(isinstance(self.connection.A.find({'_id':doc_b['_id']}).next(), B))
        self.assertTrue(isinstance(self.connection.A.find({'_id':doc_b['_id']})[0], B))

    def test_inherited_queries_without___collection__(self):
        @self.connection.register
        class A(Document):
            structure = {
                '_type': unicode,
                'a':{
                    'foo': int,
                    'bar': unicode,
                }
            }

        @self.connection.register
        class B(A):
            structure = {
                'b': {
                    'eggs': float,
                }
            }

        doc_a = self.col.A()
        self.assertEqual(doc_a['_type'], 'A')
        doc_a['a']['foo'] = 3
        doc_a['a']['bar'] = u'Hello World'
        doc_a.save()

        doc_b = self.col.B()
        self.assertEqual(doc_b['_type'], 'B')
        doc_b['a']['foo'] = 42
        doc_b['a']['bar'] = u'bye bye'
        doc_b['b']['eggs'] = 3.14
        doc_b.save()

        self.assertTrue(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), B))
        self.assertTrue(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), B))
        self.assertTrue(isinstance(self.col.A.find({'_id':doc_b['_id']})[0], B))

    def test_type_field_is_None(self):
        @self.connection.register
        class A(Document):
            type_field = None
            structure = {
                '_type': unicode,
                'a':{
                    'foo': int,
                    'bar': unicode,
                }
            }

        @self.connection.register
        class B(A):
            structure = {
                'b': {
                    'eggs': float,
                }
            }

        doc_a = self.col.A()
        self.assertEqual(doc_a['_type'], None)
        doc_a['a']['foo'] = 3
        doc_a['a']['bar'] = u'Hello World'
        doc_a.save()

        doc_b = self.col.B()
        self.assertEqual(doc_b['_type'], None)
        doc_b['a']['foo'] = 42
        doc_b['a']['bar'] = u'bye bye'
        doc_b['b']['eggs'] = 3.14
        doc_b.save()

        self.assertTrue(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), A))
        self.assertTrue(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), A))
        self.assertFalse(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), B))
        self.assertFalse(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), B))

    def test_no__type(self):
        @self.connection.register
        class A(Document):
            structure = {
                'a':{
                    'foo': int,
                    'bar': unicode,
                }
            }

        @self.connection.register
        class B(A):
            structure = {
                'b': {
                    'eggs': float,
                }
            }

        doc_a = self.col.A()
        self.assertTrue('_type' not in doc_a)
        doc_a['a']['foo'] = 3
        doc_a['a']['bar'] = u'Hello World'
        doc_a.save()

        doc_b = self.col.B()
        self.assertTrue('_type' not in doc_b)
        doc_b['a']['foo'] = 42
        doc_b['a']['bar'] = u'bye bye'
        doc_b['b']['eggs'] = 3.14
        doc_b.save()

        self.assertTrue(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), A))
        self.assertTrue(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), A))
        self.assertFalse(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), B))
        self.assertFalse(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), B))

    def test_change_type_field(self):
        @self.connection.register
        class A(Document):
            type_field = '_t'
            structure = {
                '_type': unicode,
                '_t': unicode,
                'a':{
                    'foo': int,
                    'bar': unicode,
                }
            }

        @self.connection.register
        class B(A):
            structure = {
                'b': {
                    'eggs': float,
                }
            }

        doc_a = self.col.A()
        self.assertEqual(doc_a['_type'], None)
        self.assertEqual(doc_a['_t'], 'A')
        doc_a['a']['foo'] = 3
        doc_a['a']['bar'] = u'Hello World'
        doc_a.save()

        doc_b = self.col.B()
        self.assertEqual(doc_b['_type'], None)
        self.assertEqual(doc_b['_t'], 'B')
        doc_b['a']['foo'] = 42
        doc_b['a']['bar'] = u'bye bye'
        doc_b['b']['eggs'] = 3.14
        doc_b.save()

        self.assertTrue(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), A))
        self.assertTrue(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), A))
        self.assertTrue(isinstance(self.col.A.find_one({'_id':doc_b['_id']}), B))
        self.assertTrue(isinstance(self.col.A.find({'_id':doc_b['_id']}).next(), B))


