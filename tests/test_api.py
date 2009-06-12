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

CONNECTION = Connection()

class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = CONNECTION['test']['mongokit']
        
    def tearDown(self):
        CONNECTION['test'].drop_collection('mongokit')
        CONNECTION['test'].drop_collection('versionned_mongokit')

    def test_save(self):
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
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        id = mydoc.save()
        assert isinstance(id['_id'], unicode)
        assert id['_id'].startswith("MyDoc"), id

        saved_doc = self.collection.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 43
        id = mydoc.save(uuid=False)
        assert isinstance(id['_id'], ObjectId)

        saved_doc = self.collection.find_one({"bla.bar":43})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

    def test_save_versionning(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla" : unicode,
            }

        doc = MyDoc()
        doc['bla'] =  u"bli"
        doc.save()
        assert "_version" not in doc

        class MyVersionnedDoc(VersionnedDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo" : unicode,
            }
            versioning = "versionned_mongokit"
 
        versionned_doc = MyVersionnedDoc()
        versionned_doc['_id'] = "mydoc"
        versionned_doc['foo'] = u'bla'
        versionned_doc.save()
        assert versionned_doc['_revision'] == 1
        assert versionned_doc.get_last_revision_id() == 1
        assert versionned_doc.get_revision(1) == {'foo':'bla', "_revision":1, "_id":"mydoc"}
        versionned_doc['foo'] = u'bar'
        versionned_doc.save()
        assert versionned_doc['_revision'] == 2
        assert versionned_doc.get_last_revision_id() == 2
        assert versionned_doc['foo'] == 'bar'
        assert versionned_doc.get_revision(2) == {'foo':'bar', "_revision":2, "_id":"mydoc"}, versionned_doc.get_revision(2)
        old_doc =  versionned_doc.get_revision(1)
        old_doc.save()
        assert old_doc['_revision'] == 3

        versionned_doc = MyVersionnedDoc.get_from_id(versionned_doc['_id'])
        assert len(list(versionned_doc.get_revisions())) == 3, len(list(versionned_doc.get_revisions()))

    def test_bad_versioning(self):
        class MyVersionnedDoc(VersionnedDocument):
            structure = {
                "foo" : unicode,
            }
            versioning = True
 
        self.assertRaises(ValidationError, MyVersionnedDoc)
 
    def test_save_without_collection(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["foo"] = 1
        self.assertRaises(ConnectionError, mydoc.save)

    def test_delete(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc['_id'] = 'foo'
        mydoc["foo"] = 1
        mydoc.save()
        assert MyDoc.all().count() == 1
        mydoc = MyDoc.get_from_id('foo')
        assert mydoc['foo'] == 1
        mydoc.delete()
        assert MyDoc.all().count() == 0
        
    def test_delete_versioning(self):
        class MyVersionnedDoc(VersionnedDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo" : unicode,
            }
            versioning_collection_name = "versionned_mongokit"
 
        versionned_doc = MyVersionnedDoc()
        versionned_doc['_id'] = "mydoc"
        versionned_doc['foo'] = u'bla'
        versionned_doc.save()
        assert MyVersionnedDoc.get_versioning_collection().find().count() == 1
        versionned_doc['foo'] = u'bar'
        versionned_doc.save()
        assert MyVersionnedDoc.get_versioning_collection().find().count() == 2
        versionned_doc.delete(versioning=True)
        assert MyVersionnedDoc.get_versioning_collection().find().count() == 0
        assert MyVersionnedDoc.all().count() == 0

        versionned_doc = MyVersionnedDoc()
        versionned_doc['_id'] = "mydoc"
        versionned_doc['foo'] = u'bla'
        versionned_doc.save()
        assert MyVersionnedDoc.get_versioning_collection().find().count() == 1
        versionned_doc['foo'] = u'bar'
        versionned_doc.save()
        assert MyVersionnedDoc.get_versioning_collection().find().count() == 2
        versionned_doc.delete()
        assert MyVersionnedDoc.get_versioning_collection().find().count() == 2
        assert MyVersionnedDoc.all().count() == 0

 
    def test_generate_skeleton(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int},
                "bar":unicode
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":None}, "bar":None}

    def test_generate_skeleton2(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":[int]},
                "bar":{unicode:{"egg":int}}
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[]}, "bar":{}}, a

    def test_generate_skeleton3(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":[int], "spam":{"bla":unicode}},
                "bar":{unicode:{"egg":int}}
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[], "spam":{"bla":None}}, "bar":{}}, a

    def test_get_from_id(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["_id"] = "bar"
        mydoc["foo"] = 3
        mydoc.save()
        fetched_doc = MyDoc.get_from_id("bar")
        assert mydoc == fetched_doc
        assert isinstance(fetched_doc, MyDoc)

    def test_all(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int,
            }
        for i in range(10):
            mydoc = MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        for i in MyDoc.all({"foo":{"$gt":4}}):
            assert isinstance(i, MyDoc)
        docs_list = [i["foo"] for i in MyDoc.all({"foo":{"$gt":4}})]
        assert docs_list == [5,6,7,8,9]
        # using limit/count
        assert MyDoc.all().count() == 10, MyDoc.all().count()
        assert MyDoc.all().limit(1).count() == 10, MyDoc.all().limit(1).count()
        assert MyDoc.all().where('this.foo').count() == 9 #{'foo':0} is not taken
        assert MyDoc.all().hint('foo')
        assert [i['foo'] for i in MyDoc.all().sort('foo', -1)] == [9,8,7,6,5,4,3,2,1,0]
        allPlans = MyDoc.all().explain()['allPlans']
        assert allPlans == [{u'cursor': u'BasicCursor', u'startKey': {}, u'endKey': {}}]
        next_doc =  MyDoc.all().sort('foo',1).next()
        assert isinstance(next_doc, MyDoc)
        assert next_doc['foo'] == 0
        assert len(list(MyDoc.all().skip(3))) == 7, len(list(MyDoc.all().skip(3)))
        assert isinstance(MyDoc.all().skip(3), MongoDocumentCursor)

    def test_one(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int
            }
        mydoc = MyDoc()
        mydoc['foo'] = 0
        mydoc.save()
        mydoc = MyDoc.one()
        assert mydoc["foo"] == 0
        assert isinstance(mydoc, MyDoc)
        for i in range(10):
            mydoc = MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        self.assertRaises(MultipleResultsFound, MyDoc.one)


 

