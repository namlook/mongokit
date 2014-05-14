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
from bson.objectid import ObjectId
from mongokit.helpers import i18nDotedDict


class i18nTestCase(unittest.TestCase):
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
                'toto':{'titi':{'tata':int}},
                'title':{
                    'foo':unicode,
                    'bar':{'bla':int},
                    'egg':int,
                }
            }
            i18n = ['title.foo', 'title.bar.bla']
        self.connection.register([Doc])
        doc = self.col.Doc(lang='fr')
        assert isinstance(doc.toto, DotedDict), type(doc.toto)
        assert isinstance(doc.toto.titi, DotedDict), type(doc.toto.titi)
        assert isinstance(doc.title, i18nDotedDict), type(doc.title)
        assert isinstance(doc.title.bar, i18nDotedDict), type(doc.title.bar)
        assert doc.title.foo is None, type(doc.title.foo)
        doc.get_lang() == 'fr'
        doc.title.foo = u'Salut'
        doc.title.bar.bla = 3
        doc.title.egg = 4
        doc.set_lang('en')
        doc.title.foo = u"Hello"
        doc.title.bar.bla = 2
        doc.save()

        self.assertEqual(doc.toto, {'titi': {'tata': None}})
        self.assertEqual(doc.title, {
            'egg': 4,
            'foo': {'fr': u'Salut', 'en': u'Hello'},
            'bar': {'bla': {'fr': 3, 'en': 2}}
        })
        doc.validate()
        doc.set_lang('fr')
        self.assertEqual(doc.toto, {'titi': {'tata': None}})
        self.assertEqual(doc.title, {
            'egg': 4,
            'foo': {'fr': u'Salut', 'en': u'Hello'},
            'bar': {'bla': {'fr': 3, 'en': 2}}
        })
        self.assertEqual(doc.title.foo, u"Salut")
        self.assertEqual(doc.title.bar.bla, 3)
        doc.save()

        raw_doc = self.col.find_one({'_id':doc['_id']})
        self.assertEqual(raw_doc, {'_id':doc['_id'],
          u'toto': {u'titi': {u'tata': None}},
          u'title': {
              u'foo':[
                  {u'lang': u'fr', u'value': u'Salut'},
                  {u'lang': u'en', u'value': u'Hello'}
                ],
              u'bar': {u'bla': [
                  {u'lang': u'fr', u'value': 3},
                  {u'lang': u'en', u'value': 2}
                ]},
              'egg':4}
        })
        fetched_doc = self.col.Doc.find_one({'_id':doc['_id']})
        assert isinstance(fetched_doc.toto, DotedDict), type(fetched_doc.toto)
        assert isinstance(fetched_doc.toto.titi, DotedDict), type(fetched_doc.toto.titi)
        assert isinstance(fetched_doc.title, i18nDotedDict), type(fetched_doc.title)
        assert isinstance(fetched_doc.title.bar, i18nDotedDict), type(fetched_doc.title.bar)
        self.assertEqual(fetched_doc.get_lang(), 'en')
        self.assertEqual(fetched_doc.title.foo, 'Hello')
        fetched_doc.set_lang('fr')
        assert fetched_doc.title.foo == 'Salut'

    def test_i18n_dot_notation_missing(self):
        class MyDoc(Document):
            use_dot_notation = True
            structure = {
                "existent": unicode,
                'exists': {
                    'subexists': unicode
                }
            }
            i18n = ["existent", "exists.subexists"]
        # We register it, and not use directly coz i18n is fucking broken
        # (see https://github.com/namlook/mongokit/pull/170)
        # TODO: remove this when fix would be applied in upstream
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc(lang='en')
        mydoc.existent = u"31337"
        mydoc.exists.subexists = u"31337"
        self.assertTrue(isinstance(mydoc, MyDoc), 'MyDoc is MyDoc')
        self.assertTrue(isinstance(mydoc.exists, i18nDotedDict), 'Field inside MyDoc is i18nDotedDict')

        self.assertEqual(mydoc.existent, u"31337", 'Getting existent value from dotted')
        self.assertEqual(mydoc.exists.subexists, u"31337", 'Getting existent value from dotted')
        self.assertRaises(AttributeError, lambda: mydoc.not_existent)
        self.assertRaises(AttributeError, lambda: mydoc.exists.not_subexists)

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
        failed = False
        try:
            class Doc(Document):
                structure = {
                    'title':unicode,
                }
                i18n = ['title', 'bla']
        except ValueError, e:
            self.assertEqual(str(e), "Error in i18n: can't find bla in structure")
            failed = True
        self.assertEqual(failed, True)

        class Doc(Document):
            use_dot_notation = True
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

    def test_unicode_type_as_key(self):
        class MyDoc(Document):
            structure = {
                "foo":{
                    "bar": unicode,
                    "bla":{
                        unicode:[unicode],
                    },
                },
            }
            i18n = ['foo.bar']
        self.connection.register([MyDoc])
        doc = self.col.MyDoc()
        doc['foo']['bla'][u'spam'] = [u'eggs']
        doc['foo']['bar']['fr'] = u'bla'
        doc.save()


