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
        import json
        
        assert  json.loads(mydoc.to_json()) == json.loads('{"_id": "mydoc", "bla": {"egg": 1262304000000, "foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'), mydoc.to_json()
        assert  mydoc.to_json_type() == {'_id': 'mydoc', 'bla': {'egg': 1262304000000, 'foo': u'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}, mydoc.to_json_type()

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        assert json.loads(mydoc.to_json()) == json.loads('{"_id": "mydoc2", "bla": {"egg": null, "foo": "bar", "bar": 42}, "spam": [946684800000, 1218153600000]}'), mydoc.to_json()
        assert mydoc.to_json_type() == {'_id': 'mydoc2', 'bla': {'egg': None, 'foo': u'bar', 'bar': 42}, 'spam': [946684800000, 1218153600000]}, mydoc.to_json_type()

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
        assert  isinstance(mydoc.to_json_type()['_id']['$oid'], basestring), type(mydoc.to_json_type()['_id'])
        assert isinstance(mydoc.to_json(), unicode)
 
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
        assert  isinstance(a.to_json_type()['_id']['$oid'], basestring), type(a.to_json_type()['_id'])
        a.to_json()
        b = self.col.B()
        b['bar'] = [a['_id']]
        b['egg']['nested'] = a['_id']
        b.save()
        print b.to_json_type()
        assert  isinstance(b.to_json_type()['_id']['$oid'], basestring), b.to_json_type()
        assert  isinstance(b.to_json_type()['egg']['nested']['$oid'], basestring), b.to_json_type()
        assert  isinstance(b.to_json_type()['bar'][0]['$oid'], basestring), b.to_json_type()
        assert  isinstance(b.to_json_type()['egg']['nested']['$oid'], basestring), b.to_json_type()
        assert "ObjectId" not in b.to_json()
 
    def test_simple_to_json_with_no_id(self):
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
        assert  "_id" not in mydoc.to_json_type()
        assert mydoc.to_json() == '{"bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
 
    def test_to_json_custom_type(self):
        class CustomDegree(CustomType):
            mongo_type = int
            python_type = basestring
            def to_bson(self, value):
                if value is not None:
                    return int(value.replace('C', ''))
            def to_python(self, value):
                if value is not None:
                    return str(value)+"C"
 
        class MyDoc(Document):
            structure = {
                "doc":{
                    "foo":CustomDegree(),
                },
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['foo'] = '3C'
        mydoc.save()
        self.assertEqual(
            self.col.MyDoc.collection.find_one({'_id': 'mydoc'}),
            {"doc": {"foo": 3}, "_id": "mydoc"}
        )
        self.assertEqual(
            mydoc.to_json(),
            '{"doc": {"foo": "3C"}, "_id": "mydoc"}',
        )
        self.assertEqual(mydoc.to_json_type(), {"doc": {"foo": "3C"}, "_id": "mydoc"})
 
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
        assert isinstance(mydoc.to_json_type()['doc']['embed']['_id']['$oid'], basestring)
        assert mydoc.to_json() == '{"doc": {"embed": {"_collection": "mongokit", "_database": "test", "_id": {"$oid": "%s"}, "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": {"$oid": "%s"}}' % (
          embed['_id'], mydoc['_id']), mydoc.to_json()
 
    def test_to_json_with_None_embeded_doc(self):
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
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc.save()
        assert mydoc.to_json() == '{"doc": {"embed": null}, "_id": "mydoc"}'
        assert mydoc.to_json_type() == {'doc': {'embed': None}, '_id': 'mydoc'}, mydoc.to_json_type()
 
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
 
    def test_simple_from_json2(self):
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
        json = '{"_id": "mydoc2", "bla": {"foo": "bar", "bar": 42, "egg":946684800000}, "spam": [946684800000, 1218153600000]}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'_id': 'mydoc2', 'bla': {'foo': 'bar', 'bar': 42, "egg":datetime.datetime(2000, 1, 1, 0, 0)}, 'spam': [datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2008, 8, 8, 0, 0)]}, mydoc
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
        assert json == '{"doc": {"embed": {"_collection": "mongokit", "_database": "test", "_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "mydoc"}', json
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'doc': {'embed': {u'_id': u'embed', u'bla': {u'foo': u'bar', u'bar': 42}, u'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, '_id': u'mydoc'}, mydoc
        assert isinstance(mydoc['doc']['embed'], EmbedDoc)
 
    def test_from_json_embeded_doc_with_oid(self):
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
        embed["bla"] = {"foo": u"bar", "bar": 42}
        embed["spam"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        embed.save()
        mydoc = self.col.MyDoc()
        mydoc['doc']['embed'] = embed
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"embed": {"_collection": "mongokit", "_database": "test", "_id": {"$oid": "%s"}, "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": {"$oid": "%s"}}' %(
          embed['_id'], mydoc['_id']), json
        doc = self.col.MyDoc.from_json(json)
        assert doc == {'doc': {'embed': {u'_id': embed['_id'], u'bla': {u'foo': u'bar', u'bar': 42}, u'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, '_id': mydoc['_id']}, doc
        assert isinstance(doc['doc']['embed'], EmbedDoc)
 
 
    def test_from_json_with_None_embeded_doc(self):
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
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc.save()
        json= mydoc.to_json()
        assert json == '{"doc": {"embed": null}, "_id": "mydoc"}'
        doc = self.col.MyDoc.from_json(json)
        assert doc == {'doc': {'embed': None}, '_id': 'mydoc'}
 
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
 
    def test_from_json_embeded_doc_in_list_with_oid(self):
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
        embed["bla"] = {"foo": u"bar", "bar": 42}
        embed["spam"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        embed.save()
        mydoc = self.col.MyDoc()
        mydoc['doc']['embed'] = [embed]
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"embed": [{"_collection": "mongokit", "_database": "test", "_id": {"$oid": "%s"}, "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}]}, "_id": {"$oid": "%s"}}' %(
          embed['_id'], mydoc['_id']), json
        doc = self.col.MyDoc.from_json(json)
        assert doc == {'doc': {'embed': [{u'_id': embed['_id'], u'bla': {u'foo': u'bar', u'bar': 42}, u'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}]}, '_id': mydoc['_id']}, doc
        assert isinstance(doc['doc']['embed'][0], EmbedDoc)
 
    def test_from_json_with_no_embeded_doc_in_list(self):
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
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"embed": []}, "_id": "mydoc"}'
        mydoc = self.col.MyDoc.from_json(json)
        assert mydoc == {'doc': {'embed': []}, '_id': 'mydoc'}
 
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
        assert mydoc == {'doc': {'embed': [{'foo': 'bar', 'bar': 42}]}, '_id': 'mydoc'}, mydoc
 
    def test_from_json_unicode(self):
        class MyDoc(Document):
            structure = {
                "doc":{
                    "name":unicode
                },
                "foo": unicode,
            }
            use_autorefs = True
        self.connection.register([MyDoc])
 
        mydoc = self.col.MyDoc()
        mydoc['doc']['name'] = u'bla'
        mydoc['foo'] = u'bar'
        json = mydoc.to_json()
        mydoc2 = self.col.MyDoc.from_json(json)
        assert isinstance(mydoc['doc']['name'], unicode)
        assert isinstance(mydoc['foo'], unicode)
        assert isinstance(mydoc2['doc']['name'], unicode)
        assert isinstance(mydoc2['foo'], unicode)
 
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
        newpathlist = sys.path
        sys.path = []
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
        sys.path = newpathlist
        del newpathlist
 
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
        import json
        self.assertEqual(json.loads(mydoc.to_json()),
          json.loads('{"_id": "mydoc", "bla": {"bar": 42, "foo": "bar", "egg": 1262304000000}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'))
        self.assertEqual(mydoc.to_json_type(),
          {'_id': 'mydoc', 'bla': {'egg': 1262304000000, 'foo': u'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]})
 
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.bla.egg = datetime.datetime(2010, 1, 1)
        mydoc.spam = range(10)
        mydoc.save()
        self.assertEqual(json.loads(mydoc.to_json()),
          json.loads('{"_id": "mydoc", "bla": {"bar": 42, "foo": "bar", "egg": 1262304000000}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'))
        self.assertEqual(mydoc.to_json_type(),
          {'_id': 'mydoc', 'bla': {'egg': 1262304000000, 'foo': u'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]})
 
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.spam = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        self.assertEqual(json.loads(mydoc.to_json()),
          json.loads('{"_id": "mydoc2", "bla": {"bar": 42, "foo": "bar", "egg": null}, "spam": [946684800000, 1218153600000]}'))
        self.assertEqual(mydoc.to_json_type(),
          {'_id': 'mydoc2', 'bla': {'egg': None, 'foo': u'bar', 'bar': 42}, 'spam': [946684800000, 1218153600000]})
 
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
        import json
        self.assertEqual(mydoc.to_json_type(),
          {'_id': 'mydoc', 'bla': {'bar': 42, 'foo': {'fr': u'arf', 'en': u'bar'}, 'egg': 1262304000000}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]})
        self.assertEqual(json.loads(mydoc.to_json()),
          json.loads('{"_id": "mydoc", "bla": {"egg": 1262304000000, "foo": {"fr": "arf", "en": "bar"}, "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'))
 
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc.bla.foo = u"bar"
        mydoc.bla.bar = 42
        mydoc.spam = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        self.assertEqual(mydoc.to_json_type(),
          {'_id': 'mydoc2', 'bla': {'bar': 42, 'foo': {'en': u'bar'}, 'egg': None}, 'spam': [946684800000, 1218153600000]})
        self.assertEqual(json.loads(mydoc.to_json()),
          json.loads('{"_id": "mydoc2", "bla": {"egg": null, "foo": {"en": "bar"}, "bar": 42}, "spam": [946684800000, 1218153600000]}'))
 
 
    def test_from_json_with_list(self):
        class MyDoc(Document):
            structure = {
                'foo': {'bar': [unicode]}
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['foo']['bar'] = [u'a', u'b', u'c']
        mydoc.save()
        json = u'{"_id": "mydoc", "foo":{"bar":["a", "b", "c"]}}'
        doc_from_json = self.col.MyDoc.from_json(json)
        doc_from_json.save()
        assert doc_from_json == mydoc
 
    def test_from_json_with_ref(self):
        class A(Document):
            structure = {
                'foo': unicode
            }
        class B(Document):
            structure = {
                'bar': int,
                'a': A,
            }
            use_autorefs = True
        self.connection.register([A, B])
        a = self.col.A()
        a['_id'] = u'a'
        a['foo'] = u'a'
        a.save()
 
        json = '{"_id": "b", "bar":1, "a":{"$id": "a", "$ref": "%s", "$db": "%s"}}' % (self.col.name, self.col.database.name)
        print json
        b = self.col.B.from_json(json)
        b.save()
        assert isinstance(b['a'], A), type(b['a'])
 
    def test_from_json_with_ref_in_list(self):
        class A(Document):
            structure = {
                'foo': unicode
            }
        class B(Document):
            structure = {
                'bar': int,
                'a': [A],
            }
            use_autorefs = True
        self.connection.register([A, B])
        a = self.col.A()
        a['_id'] = u'a'
        a['foo'] = u'a'
        a.save()
 
        json = '{"_id": "b", "bar":1, "a":[{"$id": "a", "$ref": "%s", "$db": "%s"}]}' % (self.col.name, self.col.database.name)
        b = self.col.B.from_json(json)
        b.save()
        assert isinstance(b['a'][0], A), type(b['a'][0])
 
    def test_from_json_with_type_as_key(self):
        class MyDoc(Document):
            structure = {
                'foo': {unicode:[unicode]}
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'a'
        mydoc['foo'][u'bar'] = [u'bla', u'ble']
 
        json = '{"_id": "a", "foo": {"bar":["bla", "ble"]}}'
        mydoc_from_json = self.col.MyDoc.from_json(json)
        assert mydoc == mydoc_from_json, (mydoc, mydoc_from_json)
 
 
    def test_from_json_with_null_date(self):
        class MyDoc(Document):
            structure = {
                'date': datetime.datetime,
                'date_in_list': [datetime.datetime],
            }
        self.connection.register([MyDoc])
 
        json = '{"_id": "a", "date": null, "date_in_list":[]}'
        mydoc_from_json = self.col.MyDoc.from_json(json)
        assert mydoc_from_json['_id'] == 'a'
        assert mydoc_from_json['date'] is None
        assert mydoc_from_json['date_in_list'] == []
