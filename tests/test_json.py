#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009, Nicolas Clairon
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

CONNECTION = Connection()

class JsonTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = CONNECTION['test']['mongokit']
        
    def tearDown(self):
        CONNECTION['test'].drop_collection('mongokit')
        CONNECTION['test'].drop_collection('versionned_mongokit')

    def test_simple_to_json(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        mydoc = MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = range(10)
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'

        mydoc = MyDoc()
        mydoc['_id'] = u'mydoc2'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"_id": "mydoc2", "bla": {"foo": "bar", "bar": 42}, "spam": [946681200.0, 1218146400.0]}'

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

        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc":{
                    "foo":CustomFloat(),
                },
            }
        mydoc = MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['foo'] = 3.70
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"foo": "3.7"}, "_id": "mydoc"}', json

    def test_to_json_embeded_doc(self):
        class EmbedDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc":{
                    "embed":EmbedDoc,
                },
            }
            use_autorefs = True
        embed = EmbedDoc()
        embed['_id'] = u'embed'
        embed["bla"]["foo"] = u"bar"
        embed["bla"]["bar"] = 42
        embed['spam'] = range(10)
        embed.save()
        mydoc = MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc['doc']['embed'] = embed
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"doc": {"embed": {"_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "mydoc"}'

    def test_simple_from_json(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        json = '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'
        mydoc = MyDoc.from_json(json)
        assert mydoc == {'_id': 'mydoc', 'bla': {'foo': 'bar', 'bar': 42}, 'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}

    def test_simple_from_json(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[datetime.datetime],
            }
        json = '{"_id": "mydoc2", "bla": {"foo": "bar", "bar": 42}, "spam": [946681200.0, 1218146400.0]}'
        mydoc = MyDoc.from_json(json)
        assert mydoc == {'_id': 'mydoc2', 'bla': {'foo': 'bar', 'bar': 42}, 'spam': [datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2008, 8, 8, 0, 0)]}

    def test_from_json_embeded_doc(self):
        class EmbedDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc":{
                    "embed":EmbedDoc,
                },
            }
            use_autorefs = True
        json = '{"doc": {"embed": {"_id": "embed", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, "_id": "mydoc"}'
        mydoc = MyDoc.from_json(json)
        assert mydoc == {'doc': {'embed': {u'_id': u'embed', u'bla': {u'foo': u'bar', u'bar': 42}, u'spam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}}, '_id': u'mydoc'}, mydoc
        assert isinstance(mydoc['doc']['embed'], EmbedDoc)

    def test_simple_to_json_from_cursor(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        mydoc = MyDoc()
        mydoc['_id'] = u'mydoc'
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc['spam'] = range(10)
        mydoc.save()
        json = mydoc.to_json()
        assert json == '{"_id": "mydoc", "bla": {"foo": "bar", "bar": 42}, "spam": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}'

        mydoc2 = MyDoc()
        mydoc2['_id'] = u'mydoc2'
        mydoc2["bla"]["foo"] = u"bla"
        mydoc2["bla"]["bar"] = 32
        mydoc2['spam'] = [datetime.datetime(2000, 1, 1), datetime.datetime(2008, 8, 8)]
        mydoc2.save()

        [i.to_json() for i in MyDoc.fetch()]

