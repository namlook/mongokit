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


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')
        self.connection.drop_database('othertest')

    def test_simple_i18n(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            i18n = ['title']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title']['en'] = u'Hello'
        doc['title']['fr'] = u"Salut"
        doc.save()

        assert doc == {'_id':doc['_id'], 'title':{'en':'Hello', 'fr':'Salut'}}, doc
        doc = self.col.Doc.find_random()
        assert doc['title'] == {'en':'Hello', 'fr':'Salut'}
        assert doc == {'_id':doc['_id'], 'title':{'en':'Hello', 'fr':'Salut'}}, doc

    def test_simple_i18n_with_int(self):
        class Doc(Document):
            structure = {
                'title':int,
            }
            i18n = ['title']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title']['en'] = 3
        doc['title']['fr'] = 10
        doc.save()

        assert doc == {'_id':doc['_id'], 'title':{'en': 3, 'fr': 10}}, doc
        doc = self.col.Doc.find_random()
        assert doc['title'] == {'en':3, 'fr':10}
        assert doc == {'_id':doc['_id'], 'title':{'en':3, 'fr':10}}, doc

    def test_i18n_with_dot_notation(self):
        class Doc(Document):
            use_dot_notation = True
            structure = {
                'title':int,
            }
            i18n = ['title']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title']['en'] = 3
        doc['title']['fr'] = 10
        print doc, doc.structure
        doc.save()

        assert doc == {'_id':doc['_id'], 'title':{'en': 3, 'fr': 10}}, doc
        doc = self.col.Doc.find_random()
        assert doc['title'] == {'en':3, 'fr':10}
        doc.set_lang('fr')
        assert doc.title == 10, doc.title
        doc.set_lang('en')
        assert doc.title == 3
        doc.set_lang('es')
        doc.title = 4
        assert doc == {'_id':doc['_id'], u'title': {u'fr': 10, u'en': 3, 'es': 4}}

    def test_i18n_with_list(self):
        class Doc(Document):
            use_dot_notation = True
            structure = {
                "title":[unicode]
            }
            i18n = ['title']
        self.connection.register([Doc])
        
        doc = self.col.Doc()
        doc.title = [u'Hello', u'Hi']
        doc.set_lang('fr')
        doc.title = [u'Bonjour', u'Salut']
        doc.save()

        assert doc.title == ['Bonjour', 'Salut']
        doc.set_lang('en')
        assert doc.title == ['Hello', 'Hi']
        doc.title.append(1)
        self.assertRaises(SchemaTypeError, doc.save)

    def test_i18n_nested_dict(self):
        class Doc(Document):
            structure = {
                'title':{
                    'foo':unicode,
                    'bar':{'bla':int},
                    'egg':int,
                }
            }
            i18n = ['title.foo', 'title.bar.bla']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title']['foo']['fr'] = u'Salut'
        doc['title']['bar']['bla']['fr'] = 3
        doc['title']['egg'] = 4
        doc['title']['foo']['en'] = u"Hello"
        doc['title']['bar']['bla']['en'] = 2
        assert doc == {'title': {'foo': {'fr': u'Salut', 'en': u'Hello'}, 'bar': {'bla': {'fr': 3, 'en': 2}}, 'egg':4}}, doc
        doc.save()

        raw_doc = self.col.find_one({'_id':doc['_id']})
        assert raw_doc == {'_id':doc['_id'],
          u'title': {u'foo': [{u'lang': u'fr', u'value': u'Salut'}, {u'lang': u'en', u'value': u'Hello'}],
          u'bar': {u'bla': [{u'lang': u'fr', u'value': 3}, {u'lang': u'en', u'value': 2}]}, 'egg':4}
        }, raw_doc
        fetched_doc = self.col.Doc.find_one({'_id':doc['_id']})
        assert fetched_doc['title']['foo']['en'] == 'Hello'
        assert fetched_doc['title']['foo']['fr'] == 'Salut'

    def test_i18n_nested_dict_dot_notation(self):
        class Doc(Document):
            use_dot_notation = True
            structure = {
                'title':{
                    'foo':unicode,
                    'bar':{'bla':int},
                    'egg':int,
                }
            }
            i18n = ['title.foo', 'title.bar.bla']
        self.connection.register([Doc])
        doc = self.col.Doc(lang='fr')
        doc.get_lang() == 'fr'
        doc.title.foo = u'Salut'
        doc.title.bar.bla = 3
        doc.title.egg = 4
        print doc
        doc.set_lang('en')
        doc.title.foo = u"Hello"
        doc.title.bar.bla = 2
        assert doc == {'title': {'foo': {'fr': u'Salut', 'en': u'Hello'}, 'bar': {'bla': {'fr': 3, 'en': 2}}, 'egg':4}}, doc
        doc.validate()
        doc.set_lang('fr')
        assert doc == {'title': {'foo': {'fr': u'Salut', 'en': u'Hello'}, 'bar': {'bla': {'fr': 3, 'en': 2}}, 'egg':4}}, doc
        doc.save()

        raw_doc = self.col.find_one({'_id':doc['_id']})
        assert raw_doc == {'_id':doc['_id'],
          u'title': {u'foo': [{u'lang': u'fr', u'value': u'Salut'}, {u'lang': u'en', u'value': u'Hello'}],
          u'bar': {u'bla': [{u'lang': u'fr', u'value': 3}, {u'lang': u'en', u'value': 2}]}, 'egg':4}
        }, raw_doc
        fetched_doc = self.col.Doc.find_one({'_id':doc['_id']})
        assert fetched_doc.get_lang() == 'en'
        assert fetched_doc.title.foo == 'Hello'
        fetched_doc.set_lang('fr')
        assert fetched_doc.title.foo == 'Salut'


    def test_i18n_fallback(self):
        class Doc(Document):
            use_dot_notation = True
            structure = {
                'title':{
                    'foo':unicode,
                },
                'bar':int,
            }
            i18n = ['title.foo', 'bar']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc.get_lang() == 'en'
        doc.title.foo = u"Hello"
        doc.bar = 3
        doc.save()
        doc.set_lang('fr')
        assert doc.title.foo == 'Hello'
        assert doc.bar == 3
        doc.title.foo = u'Salut'
        doc.bar = 4
        assert doc.title.foo == 'Salut'
        assert doc.bar == 4
        doc.get_lang() == 'fr'
        
    def test_i18n_bad_type(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            i18n = ['title']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title']['en'] = u'Hello'
        doc['title']['fr'] = 3
        self.assertRaises(SchemaTypeError, doc.save)

    def test_bad_i18n(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            i18n = ['title', 'bla']
        self.assertRaises(ValidationError, self.connection.register, [Doc])
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            i18n = ['title']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title']['en'] = u'Hello'
        doc['title'] = u"Salut"
        self.assertRaises(SchemaTypeError, doc.save)
        doc['title'] = i18n()
        doc['title']['en'] = u'Hello'
        doc['title']['fr'] = u"Salut"
        doc.save()
        doc = self.col.Doc.find_random()
        assert doc['title'] == {'en':'Hello', 'fr':'Salut'}

    def test_i18n_inheritance(self):
        class A(Document):
            structure = {
                'a':{
                    'title':unicode,
                }
            }
            i18n = ['a.title']

        class B(A):
            structure = {
                'b':{
                    'title':unicode,
                }
            }
            i18n = ['b.title']


        class C(Document):
            structure = {
                'c':{
                    'title':unicode,
                }
            }
            i18n = ['c.title']

        class D(B, C):
            structure = {
                'd':{
                    'title':unicode,
                }
            }

        self.connection.register([D])
        doc = self.col.D()
        assert doc.i18n == ['a.title', 'c.title', 'b.title'], doc.i18n
        doc['a']['title']['en'] = u'Hello'
        doc['b']['title']['fr'] = u"Salut"
        doc['c']['title']['fr'] = u"Salut"
        assert doc == {'a': {'title': {'en': u'Hello'}}, 'c': {'title': {'fr': u'Salut'}}, 'b': {'title': {'fr': u'Salut'}}, 'd': {'title': None}}

    def test_i18n_default_values(self):
        class Doc(Document):
            use_dot_notation = True
            structure = {
                'title':int,
                'foo':{'bar':unicode},
            }
            i18n = ['title', 'foo.bar']
            default_values = {'title':{'en':3, 'fr':4}, 'foo.bar': {'en':u'bla', 'fr': u'ble'}}
        self.connection.register([Doc])
        doc = self.col.Doc()
        assert doc == {'foo': {'bar': {'fr': u'ble', 'en': u'bla'}}, 'title': {'fr': 4, 'en': 3}}
        doc.save()


