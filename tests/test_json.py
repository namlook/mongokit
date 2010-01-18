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
import datetime


class JsonTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection['test'].drop_collection('mongokit')
        self.connection['test'].drop_collection('versionned_mongokit')

    def test_simple_to_json(self):
        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                    "egg":datetime.datetime,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['bla']['egg'] = datetime.datetime(2010, 1, 1)
        mydoc['spam'] = range(10)
        mydoc.save()
        assert  mydoc.to_json() == '{"_id": "mydoc", "bla": {"egg": 1262300400.0, "foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
        assert  mydoc.to_json_type() == {'_id': 'mydoc', 'bla': {'egg': 1262300400.0, 'foo': u'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        assert mydoc.to_json() == '{"_id": "mydoc2", "bla": {"egg": null, "foo": "bar", "bar": 42}, "spam": [946681200.0, 1218146400.0]}'
        assert mydoc.to_json_type() == {'_id': 'mydoc2', 'bla': {'egg': None, 'foo': u'bar', 'bar': 42}, 'spam': [946681200.0, 1218146400.0]}

    def test_simple_to_json_with_oid(self):
        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = range(10)
        mydoc.save()
        assert  isinstance(mydoc.to_json_type()['_id'], basestring), type(mydoc.to_json_type()['_id'])
        mydoc.to_json()

    def test_simple_to_json_with_oid_in_list(self):
        class A(Document):
            structure = {
                "foo":unicode,
            }
        class B(Document):
            structure = {
                'bar':[ObjectId],
                'egg':{
                    'nested':ObjectId,
                }
            }

        self.connection.register([A, B])
        a = self.col.A()
        a["foo"] = u"bar"
        a.save()
        assert  isinstance(a.to_json_type()['_id'], basestring), type(a.to_json_type()['_id'])
        a.to_json()
        b = self.col.B()
        b['bar'] = [a['_id']]
        b['egg']['nested'] = a['_id']
        b.save()
        assert  isinstance(b.to_json_type()['bar'][0], basestring), b.to_json_type()
        assert  isinstance(b.to_json_type()['egg']['nested'], basestring), b.to_json_type()
        assert "ObjectId" not in b.to_json()



    def test_to_json_custom_type(self):
        class CustomFloat(CustomType):
            mongo_type = unicode
            python_type = float
            def to_bson(self, value):
                if value is not None:
                    return unicode(value)
            def to_python(self, value):
                if value is not None:
                    return float(value)

        class MyDoc(Document):
            structure = {
                "doc":{
                    "foo":CustomFloat(),
                },
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['foo'] = 3.70
        mydoc.save()
        assert mydoc.to_json() == '{"doc": {"foo": 3.7000000000000002}, "_id": "mydoc"}', mydoc.to_json()
        assert mydoc.to_json_type() == {"doc": {"foo": 3.7000000000000002}, "_id": "mydoc"}

    def test_to_json_embeded_doc(self):
        class EmbedDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        class MyDoc(Document):
            structure = {
                "doc":{
                    "embed":EmbedDoc,
                },
            }
            use_autorefs = True
        self.connection.register([MyDoc, EmbedDoc])
        embed = self.col.EmbedDoc()
        embed['_id'] = u'embed'
        embed["bla"]["foo"] = u"bar"
        embed["bla"]["bar"] = 42
        embed['spam'] = range(10)
        embed.save()
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['embed'] = embed
        mydoc.save()
        assert mydoc.to_json() == '{"doc": {"embed": {"_collection": "mongokit", "_database": "test", "_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "mydoc"}'
        assert mydoc.to_json_type() == {"doc": {"embed": {"_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "mydoc"}

    def test_to_json_embeded_doc_with_oid(self):
        class EmbedDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        class MyDoc(Document):
            structure = {
                "doc":{
                    "embed":EmbedDoc,
                },
            }
            use_autorefs = True
        self.connection.register([MyDoc, EmbedDoc])
        embed = self.col.EmbedDoc()
        embed["bla"]["foo"] = u"bar"
        embed["bla"]["bar"] = 42
        embed['spam'] = range(10)
        embed.save()
        mydoc = self.col.MyDoc()
        mydoc['doc']['embed'] = embed
        mydoc.save()
        assert isinstance(mydoc.to_json_type()['doc']['embed']['_id'], basestring)
        assert mydoc.to_json() == '{"doc": {"embed": {"_collection": "mongokit", "_database": "test", "_id": "%s", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "%s"}' % (
          embed['_id'], mydoc['_id'])

    def test_to_json_with_dict_in_list(self):
        class MyDoc(Document):
            structure = {
                "foo":[{'bar':unicode, 'egg':int}],
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["foo"] = [{'bar':u'bla', 'egg':3}, {'bar':u'bli', 'egg':4}]
        mydoc.save()
        assert  mydoc.to_json() == '{"foo": [{"bar": "bla", "egg": 3}, {"bar": "bli", "egg": 4}], "_id": "mydoc"}', mydoc.to_json()
        assert  mydoc.to_json_type() == {'foo': [{'bar': u'bla', 'egg': 3}, {'bar': u'bli', 'egg': 4}], '_id': 'mydoc'}


    def test_simple_from_json(self):
        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])
        json = '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'_id': 'mydoc', 'bla': {'foo': 'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
        assert mydoc.collection == self.col

    def test_simple_from_json(self):
        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                    "egg":datetime.datetime,
                },
                "spam":[datetime.datetime],
            }
        self.connection.register([MyDoc])
        json = '{"_id": "mydoc2", "bla": {"foo": "bar", "bar": 42, "egg":946681200.0}, "spam": [946681200.0, 1218146400.0]}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'_id': 'mydoc2', 'bla': {'foo': 'bar', 'bar': 42, "egg":datetime.datetime(2000, 1, 1, 0, 0)}, 'spam': [datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2008, 8, 8, 0, 0)]}
        assert mydoc.collection == self.col

    def test_from_json_embeded_doc(self):
        class EmbedDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        class MyDoc(Document):
            structure = {
                "doc":{
                    "embed":EmbedDoc,
                },
            }
            use_autorefs = True
        self.connection.register([MyDoc, EmbedDoc])
        
        embed = self.col.EmbedDoc()
        embed['_id'] = u"embed"
        embed["bla"] = {"foo": u"bar", "bar": 42}
        embed["spam"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        embed.save()
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['embed'] = embed
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"embed": {"_collection": "mongokit", "_database": "test", "_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "mydoc"}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'doc': {'embed': {u'_id': u'embed', u'bla': {u'foo': u'bar', u'bar': 42}, u'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, '_id': u'mydoc'}, mydoc
        assert isinstance(mydoc['doc']['embed'], EmbedDoc)

    def test_from_json_embeded_doc_in_list(self):
        class EmbedDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        class MyDoc(Document):
            structure = {
                "doc":{
                    "embed":[EmbedDoc],
                },
            }
            use_autorefs = True
        self.connection.register([MyDoc, EmbedDoc])
        embed = self.col.EmbedDoc()
        embed['_id'] = u"embed"
        embed["bla"] = {"foo": u"bar", "bar": 42}
        embed["spam"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        embed.save()
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['embed'] = [embed]
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"embed": [{"_collection": "mongokit", "_database": "test", "_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}]}, "_id": "mydoc"}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'doc': {'embed': [{u'_id': u'embed', u'bla': {u'foo': u'bar', u'bar': 42}, u'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}]}, '_id': u'mydoc'}, mydoc
        assert isinstance(mydoc['doc']['embed'][0], EmbedDoc)

    def test_from_json_dict_in_list(self):
        class MyDoc(Document):
            structure = {
                "doc":{
                    "embed":[{"foo":unicode, "bar":int}],
                },
            }
            use_autorefs = True
        self.connection.register([MyDoc])
        json = '{"doc": {"embed": [{"foo": "bar", "bar": 42}]}, "_id": "mydoc"}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'doc': {'embed': [{'foo': 'bar', 'bar': 42}]}, '_id': 'mydoc'}


    def test_simple_to_json_from_cursor(self):
        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = range(10)
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'

        mydoc2 = self.col.MyDoc()
        mydoc2['_id'] = u'mydoc2'
        mydoc2["bla"]["foo"] = u"bla"
        mydoc2["bla"]["bar"] = 32
        mydoc2['spam'] = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc2.save()
        json2 = mydoc2.to_json()

        assert [i.to_json() for i in self.col.MyDoc.fetch()] == [json, json2]

    def test_anyjson_import_error(self):
        import sys
        for i in sys.path:
            if 'anyjson' in i:
                index = sys.path.index(i)
                del sys.path[index]
                break
        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["foo"] = 4
        mydoc.save()
        self.assertRaises(ImportError, mydoc.to_json)
        self.assertRaises(ImportError, self.col.MyDoc.from_json, '{"_id":"mydoc", "foo":4}')
        sys.path.insert(index, i)

    def test_to_json_with_dot_notation(self):
        class MyDoc(Document):
            use_dot_notation = True
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                    "egg":datetime.datetime,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['bla']['egg'] = datetime.datetime(2010, 1, 1)
        mydoc['spam'] = range(10)
        mydoc.save()
        assert  mydoc.to_json() == '{"_id": "mydoc", "bla": {"egg": 1262300400.0, "foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
        assert  mydoc.to_json_type() == {'_id': 'mydoc', 'bla': {'egg': 1262300400.0, 'foo': u'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.bla.egg = datetime.datetime(2010, 1, 1)
        mydoc.spam = range(10)
        mydoc.save()
        assert  mydoc.to_json() == '{"_id": "mydoc", "bla": {"egg": 1262300400.0, "foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}', mydoc.to_json()
        assert  mydoc.to_json_type() == {'_id': 'mydoc', 'bla': {'egg': 1262300400.0, 'foo': u'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.spam = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        assert mydoc.to_json() == '{"_id": "mydoc2", "bla": {"egg": null, "foo": "bar", "bar": 42}, "spam": [946681200.0, 1218146400.0]}'
        assert mydoc.to_json_type() == {'_id': 'mydoc2', 'bla': {'egg': None, 'foo': u'bar', 'bar': 42}, 'spam': [946681200.0, 1218146400.0]}

    def test_to_json_with_i18n_and_dot_notation(self):
        class MyDoc(Document):
            use_dot_notation = True
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                    "egg":datetime.datetime,
                },
                "spam":[],
            }
            i18n = ['bla.foo']
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.bla.egg = datetime.datetime(2010, 1, 1)
        mydoc.spam = range(10)
        mydoc.set_lang('fr')
        mydoc.bla.foo = u"arf"
        mydoc.save()
        assert  mydoc.to_json_type() == {'_id': 'mydoc', 'bla': {'bar': 42, 'foo': {'fr': u'arf', 'en': u'bar'}, 'egg': 1262300400.0}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
        assert  mydoc.to_json() == '{"_id": "mydoc", "bla": {"bar": 42, "foo": {"fr": "arf", "en": "bar"}, "egg": 1262300400.0}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.spam = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        assert mydoc.to_json_type() == {'_id': 'mydoc2', 'bla': {'bar': 42, 'foo': {'en': u'bar'}, 'egg': None}, 'spam': [946681200.0, 1218146400.0]}
        assert mydoc.to_json() == '{"_id": "mydoc2", "bla": {"bar": 42, "foo": {"en": "bar"}, "egg": null}, "spam": [946681200.0, 1218146400.0]}'

 
