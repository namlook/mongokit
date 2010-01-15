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


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')
        self.connection.drop_database('othertest')

    def test_save(self):
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
        id = mydoc.save()
        assert isinstance(id['_id'], ObjectId)

        saved_doc = self.col.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

        mydoc = self.col.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 43
        id = mydoc.save(uuid=True)
        assert isinstance(id['_id'], unicode)
        assert id['_id'].startswith("MyDoc"), id

        saved_doc = self.col.find_one({"bla.bar":43})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

    def test_save_without_collection(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = MyDoc()
        mydoc["foo"] = 1
        self.assertRaises(ConnectionError, mydoc.save)

    def test_delete(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = 'foo'
        mydoc["foo"] = 1
        mydoc.save()
        assert self.col.MyDoc.find().count() == 1
        mydoc = self.col.MyDoc.get_from_id('foo')
        assert mydoc['foo'] == 1
        mydoc.delete()
        assert self.col.MyDoc.find().count() == 0
        
    def test_generate_skeleton(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":int},
                "bar":unicode
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":None}, "bar":None}, a

    def test_generate_skeleton2(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":[int]},
                "bar":{unicode:{"egg":int}}
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[]}, "bar":{}}, a

    def test_generate_skeleton3(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":[int], "spam":{"bla":unicode}},
                "bar":{unicode:{"egg":int}}
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[], "spam":{"bla":None}}, "bar":{}}, a

    def test_get_from_id(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc["_id"] = "bar"
        mydoc["foo"] = 3
        mydoc.save()
        fetched_doc = self.col.MyDoc.get_from_id("bar")
        assert mydoc == fetched_doc
        assert callable(fetched_doc) is False
        assert isinstance(fetched_doc, MyDoc)
        raw_doc = self.col.get_from_id('bar')
        assert mydoc == raw_doc
        assert not isinstance(raw_doc, MyDoc)

    def test_find(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
                "bar":{"bla":int},
            }
        self.connection.register([MyDoc])
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc["bar"]['bla'] = i
            mydoc.save()
        for i in self.col.MyDoc.find({"foo":{"$gt":4}}):
            assert isinstance(i, MyDoc)
        docs_list = [i["foo"] for i in self.col.MyDoc.find({"foo":{"$gt":4}})]
        assert docs_list == [5,6,7,8,9]
        # using limit/count
        assert self.col.MyDoc.find().count() == 10, self.col.MyDoc.find().count()
        assert self.col.MyDoc.find().limit(1).count() == 10, self.col.MyDoc.find().limit(1).count()
        assert self.col.MyDoc.find().where('this.foo').count() == 9 #{'foo':0} is not taken
        assert self.col.MyDoc.find().where('this.bar.bla').count() == 9 #{'foo':0} is not taken
        assert self.col.MyDoc.find().hint([('foo', 1)])
        assert [i['foo'] for i in self.col.MyDoc.find().sort('foo', -1)] == [9,8,7,6,5,4,3,2,1,0]
        allPlans = self.col.MyDoc.find().explain()['allPlans']
        assert allPlans == [{u'cursor': u'BasicCursor', u'startKey': {}, u'endKey': {}}]
        next_doc =  self.col.MyDoc.find().sort('foo',1).next()
        assert callable(next_doc) is False
        assert isinstance(next_doc, MyDoc)
        assert next_doc['foo'] == 0
        assert len(list(self.col.MyDoc.find().skip(3))) == 7, len(list(self.col.MyDoc.find().skip(3)))
        assert isinstance(self.col.MyDoc.find().skip(3), MongoDocumentCursor)

    def test_find_one(self):
        class MyDoc(Document):
            structure = {
                "foo":int
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['foo'] = 0
        mydoc.save()
        mydoc = self.col.MyDoc.find_one()
        assert mydoc["foo"] == 0
        assert isinstance(mydoc, MyDoc)
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        one_doc = self.col.MyDoc.find_one()
        assert callable(one_doc) is False
        raw_mydoc = self.col.find_one()
        assert one_doc == raw_mydoc

    def test_one(self):
        class MyDoc(Document):
            structure = {
                "foo":int
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['foo'] = 0
        mydoc.save()
        raw_mydoc = self.col.one()
        mydoc = self.col.MyDoc.one()
        assert callable(mydoc) is False
        assert mydoc == raw_mydoc
        assert mydoc["foo"] == 0
        assert isinstance(mydoc, MyDoc)
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        self.assertRaises(MultipleResultsFound, self.col.MyDoc.one)
        self.assertRaises(MultipleResultsFound, self.col.one)

    def test_find_random(self):
        class MyDoc(Document):
            structure = {
                "foo":int
            }
        self.connection.register([MyDoc])
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        raw_mydoc = self.col.find_random()
        mydoc = self.col.MyDoc.find_random()
        assert callable(mydoc) is False
        assert isinstance(mydoc, MyDoc)
        assert mydoc != raw_mydoc, (mydoc, raw_mydoc)

    def test_fetch(self):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        self.connection.register([DocA])
        class DocB(Document):
            structure = {
                "doc_b":{"bar":int},
            }
        self.connection.register([DocB])
        # creating DocA
        for i in range(10):
            mydoc = self.col.DocA()
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = self.col.DocB()
            mydoc['doc_b']["bar"] = i
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert self.col.DocA.find().count() == 15

        # fetch get only the corresponding documents:
        assert self.col.DocA.fetch().count() == 10, self.col.DocA.fetch().count()
        assert self.col.DocB.fetch().count() == 5
        index = 0
        for doc in self.col.DocA.fetch():
            assert doc == {'_id':doc['_id'], 'doc_a':{'foo':index}}, doc
            assert callable(doc) is False
            index += 1

        #assert DocA.fetch().limit(12).count() == 10, DocA.fetch().limit(1).count() # ???
        assert self.col.DocA.fetch().where('this.doc_a.foo > 3').count() == 6

    def test_fetch_with_query(self):
        class DocA(Document):
            structure = {
                "bar":unicode,
                "doc_a":{'foo':int},
            }
        class DocB(Document):
            structure = {
                "bar":unicode,
                "doc_b":{"bar":int},
            }
        self.connection.register([DocA, DocB])

        # creating DocA
        for i in range(10):
            mydoc = self.col.DocA()
            if i % 2 == 0:
                mydoc['bar'] = u"spam"
            else:
                mydoc['bar'] = u"egg"
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = self.col.DocB()
            if i % 2 == 0:
                mydoc['bar'] = u"spam"
            else:
                mydoc['bar'] = u"egg"
            mydoc['doc_b']["bar"] = i
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert self.col.DocA.find().count() == 15
        assert self.col.DocA.fetch().count() == 10, self.col.DocA.fetch().count()
        assert self.col.DocB.fetch().count() == 5

        assert self.col.DocA.fetch({'bar':'spam'}).count() == 5
        assert self.col.DocB.fetch({'bar':'spam'}).count() == 3

    def test_fetch_inheritance(self):
        class Doc(Document):
            structure = {
                "doc":{'bla':int},
            }
        class DocA(Doc):
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(DocA):
            structure = {
                "doc_b":{"bar":int},
            }
        self.connection.register([Doc, DocA, DocB])
        # creating DocA
        for i in range(10):
            mydoc = self.col.DocA()
            mydoc['doc']["bla"] = i+1
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = self.col.DocB()
            mydoc['doc']["bla"] = i+1
            mydoc['doc_a']["foo"] = i
            mydoc['doc_b']["bar"] = i+2
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert self.col.DocA.find().count() == 15

        # fetch get only the corresponding documents:
        # DocB is a subclass of DocA and have all fields of DocA so
        # we get all doc here
        assert self.col.DocA.fetch().count() == 15, self.col.DocA.fetch().count()
        # but only the DocB as DocA does not have a 'doc_a' field
        assert self.col.DocB.fetch().count() == 5
        index = 0
        for doc in self.col.DocB.fetch():
            assert doc == {'_id':doc['_id'], 'doc_a':{'foo':index}, 'doc':{'bla':index+1}, "doc_b":{'bar':index+2}}, (doc, index)
            index += 1

        #assert DocA.fetch().limit(12).count() == 10, DocA.fetch().limit(1).count() # ???
        assert self.col.DocA.fetch().where('this.doc_a.foo > 3').count() == 7

    def test_fetch_one(self):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(DocA):
            structure = {
                "doc_b":{"bar":int},
            }
        self.connection.register([DocA, DocB])

        # creating DocA
        mydoc = self.col.DocA()
        mydoc['doc_a']["foo"] = 1
        mydoc.save()
        # creating DocB
        mydoc = self.col.DocB()
        mydoc['doc_b']["bar"] = 2
        mydoc.save()

        docb = self.col.DocB.fetch_one()
        assert callable(docb) is False
        assert docb
        assert isinstance(docb, DocB)
        self.assertRaises(MultipleResultsFound, self.col.DocA.fetch_one)

    def test_query_with_passing_collection(self):
        class MyDoc(Document):
            structure = {
                'foo':int,
            }
        self.connection.register([MyDoc])

        mongokit = self.connection.test.mongokit

        # boostraping
        for i in range(10):
            mydoc = mongokit.MyDoc()
            mydoc['_id'] = unicode(i)
            mydoc['foo'] = i
            mydoc.save()

        # get_from_id
        fetched_doc = mongokit.MyDoc.get_from_id('4')
        assert fetched_doc.collection == mongokit

        # all
        fetched_docs = mongokit.MyDoc.find({'foo':{'$gt':2}})
        assert fetched_docs.count() == 7
        for doc in fetched_docs:
            assert doc.collection == mongokit

        # one
        doc = mongokit.MyDoc.fetch_one({'foo':2})
        assert doc.collection == mongokit

        # fetch
        fetched_docs = mongokit.MyDoc.fetch({'foo':{'$gt':2}})
        assert fetched_docs.count() == 7
        for doc in fetched_docs:
            assert doc.collection == mongokit

        # fetch_one
        doc = mongokit.MyDoc.fetch_one({'foo':2})
        assert doc.collection == mongokit

    def test_skip_validation(self):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        self.connection.register([DocA])

        # creating DocA
        mydoc = self.col.DocA()
        mydoc['doc_a']["foo"] = u'bar' 
        assertion = False
        try:
            mydoc.save()
        except SchemaTypeError:
            assertion = True
        assert assertion
        mydoc.save(validate=False)

        DocA.skip_validation = True

        # creating DocA
        mydoc = self.col.DocA()
        mydoc['doc_a']["foo"] = u'foo' 
        self.assertRaises(SchemaTypeError, mydoc.save, validate=True)
        mydoc.save()


    def test_connection(self):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        self.connection.register([DocA])
        assertion = True
        try:
            DocA.connection
        except AttributeError:
            assertion = True
        assert assertion
        try:
            DocA.db
        except AttributeError:
            assertion = True
        assert assertion
        try:
            DocA.collection
        except AttributeError:
            assertion = True
        assert assertion

        assert self.col.DocA.connection == Connection("localhost", 27017)
        assert self.col.DocA.collection == Connection("localhost", 27017)['test']['mongokit']
        assert self.col.DocA.db == Connection("localhost", 27017)['test']

    def test_all_with_dynamic_collection(self):
        class Section(Document):
            structure = {"section":int}
        self.connection.register([Section])

        s = self.connection.test.section.Section()
        s['section'] = 1
        s.save()

        s = self.connection.test.section.Section()
        s['section'] = 2
        s.save()

        s = self.connection.test.other_section.Section()
        s['section'] = 1
        s.save()

        s = self.connection.test.other_section.Section()
        s['section'] = 2
        s.save()


        sect_col = self.connection.test.section
        sects = [s.collection.name == 'section' and s.db.name == 'test' for s in sect_col.Section.find({})] 
        assert len(sects) == 2, len(sects)
        assert any(sects)
        sects = [s.collection.name == 'section' and s.db.name == 'test' for s in sect_col.Section.fetch()]
        assert len(sects) == 2
        assert any(sects)

        sect_col = self.connection.test.other_section
        sects = [s.collection.name == 'other_section' and s.db.name == 'test' for s in sect_col.Section.find({})] 
        assert len(sects) == 2
        assert any(sects)
        sects = [s.collection.name == 'other_section' and s.db.name == 'test' for s in sect_col.Section.fetch()]
        assert len(sects) == 2
        assert any(sects)

    def test_get_collection_with_connection(self):
        class Section(Document):
            structure = {"section":int}
        connection = Connection('127.0.0.3')
        connection.register([Section])
        col = connection.test.mongokit
        assert col.database.connection == col.Section.connection
        assert col.database.name == 'test' == col.Section.db.name
        assert col.name == 'mongokit' == col.Section.collection.name

    def test_get_size(self):
        class MyDoc(Document):
            structure = {
                "doc":{"foo":int, "bla":unicode},
            }

        mydoc = MyDoc()
        mydoc['doc']['foo'] = 3
        mydoc['doc']['bla'] = u'bla bla'
        assert mydoc.get_size() == 41, mydoc.get_size()

        mydoc['doc']['bla'] = u'bla bla'+'b'*12
        assert mydoc.get_size() == 41+12

        mydoc.validate()

        mydoc['doc']['bla'] = u'b'*4000000
        self.assertRaises(MaxDocumentSizeError, mydoc.validate)

    def test_get_with_no_wrap(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])

        for i in xrange(2000):
            mydoc = self.col.MyDoc()
            mydoc['foo'] = i
            mydoc.save()

        import time
        start = time.time()
        wrapped_mydocs = [i for i in self.col.MyDoc.find()]
        end = time.time()
        wrap_time = end-start

        start = time.time()
        mydocs = [i for i in self.col.find().sort('foo', -1)]
        end = time.time()
        no_wrap_time = end-start

        assert no_wrap_time < wrap_time

        assert isinstance(wrapped_mydocs[0], MyDoc)
        assert not isinstance(mydocs[0], MyDoc), type(mydocs[0])
        assert [i['foo'] for i in mydocs] == list(reversed(range(2000))), [i['foo'] for i in mydocs]
        assert mydocs[0]['foo'] == 1999, mydocs[0]['foo']

        assert not isinstance(self.col.find().sort('foo', -1).next(), MyDoc)

    def test_get_dbref(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'1'
        mydoc['foo'] = 1
        mydoc.save()
        
        mydoc = self.connection.test.othercol.MyDoc()
        mydoc['_id'] = u'2'
        mydoc['foo'] = 2
        mydoc.save()

        mydoc = self.connection.othertest.mongokit.MyDoc()
        mydoc['_id'] = u'3'
        mydoc['foo'] = 3
        mydoc.save()

        mydoc = self.col.MyDoc.find_one({'foo':1})
        assert mydoc.get_dbref(), DBRef(u'mongokit', u'1', u'test')

        mydoc = self.connection.test.othercol.MyDoc.find_one({'foo':2})
        assert mydoc.get_dbref() == DBRef(u'othercol', u'2', u'test')

        mydoc = self.connection.othertest.mongokit.MyDoc.find_one({'foo':3})
        assert mydoc.get_dbref() == DBRef(u'mongokit', u'3', u'othertest')

    def test__hash__(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['foo'] = 1
        self.assertRaises(TypeError, hash, mydoc)

        mydoc.save()
        hash(mydoc)

    def test_non_callable(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        self.assertRaises(TypeError, mydoc)
        assert callable(mydoc) is False


    def test_bad_call(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.assertRaises(TypeError, self.connection.test.col.MyDoc)
        self.connection.register([MyDoc])
        self.connection.test.col.MyDoc()
        self.assertRaises(TypeError, self.connection.test.col.Bla)
        self.assertRaises(TypeError, self.connection.test.Bla)


    def test_fetched_dot_notation(self):
        class MyDoc(Document):
            use_dot_notation = True
            structure = {
                "foo":int,
                "bar":{"egg":unicode}
            }

        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc.foo = 3
        mydoc.bar.egg = u'bla'
        mydoc.save()
        fetched_doc = self.col.MyDoc.find_one()
        assert fetched_doc.foo == 3, fetched_doc.foo
        assert fetched_doc.bar.egg == "bla", fetched_doc.bar.egg

       

