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

CONNECTION = Connection()

class IndexTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = CONNECTION['test']['mongokit']
        self.collection.drop_indexes()
        
    def tearDown(self):
        CONNECTION['test'].drop_collection('mongokit')
    
    def test_index_basic(self):
        class Movie(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
                'other':{
                    'deep':unicode,
                },
                'notindexed':unicode,
            }
            
            indexes = [
                {
                    'fields':['standard','other.deep'],
                    'unique':True,
                },
            ]
        movie = Movie()
        movie['standard'] = u'test'
        movie['other']['deep'] = u'testdeep'
        movie['notindexed'] = u'notthere'
        movie.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name': 'standard_1_other.deep_1', 'unique':True})
        assert item is not None, 'No Index Found'

        movie = Movie()
        movie['standard'] = u'test'
        movie['other']['deep'] = u'testdeep'
        self.assertRaises(OperationFailure, movie.save)
 
        
    def test_index_single(self):
        class Movie(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
            }
            
            indexes = [
                {
                    'fields':'standard',
                    'unique':True,
                },
            ]
        movie = Movie()
        movie['standard'] = u'test'
        movie.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_1', 'unique':True, 'key':{'standard':1}})
        
        assert item is not None, 'No Index Found'

    def test_index_multi(self):
        class Movie(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
                'other':{
                    'deep':unicode,
                },
                'notindexed':unicode,
                'alsoindexed':unicode,
            }
            
            indexes = [
                {
                    'fields':'standard',
                    'unique':True,
                },
                {
                    'fields':['alsoindexed', 'other.deep'],
                    'unique':True,
                },
            ]
        movie = Movie()
        movie['standard'] = u'test'
        movie.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_1', 'unique':True, 'key':{'standard':1}})
        index2 = db.system.indexes.find_one({'ns':'test.mongokit', 'name': 'alsoindexed_1_other.deep_1', 'unique':True})
        
        assert item is not None, 'No Index Found'
        assert index2 is not None, 'Index not found'

        movie = Movie()
        movie['standard'] = u'test'
        self.assertRaises(OperationFailure, movie.save)

    def test_index_multi(self):
        class Movie(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
                'other':{
                    'deep':unicode,
                },
                'notindexed':unicode,
                'alsoindexed':unicode,
            }
            
            indexes = [
                {
                    'fields':'standard',
                    'unique':True,
                },
                {
                    'fields':['other.deep'],
                    'unique':True,
                },
            ]
        movie = Movie()
        movie['standard'] = u'test'
        movie['other']['deep'] = u'foo'
        movie.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_1', 'unique':True, 'key':{'standard':1}})
        index2 = db.system.indexes.find_one({'ns':'test.mongokit', 'name': 'other.deep_1', 'unique':True})
        
        assert item is not None, 'No Index Found'
        assert index2 is not None, 'Index not found'

        movie = Movie()
        movie['standard'] = u'test'
        self.assertRaises(OperationFailure, movie.save)

        movie = Movie()
        movie['other']['deep'] = u'foo'
        self.assertRaises(OperationFailure, movie.save)

    def test_index_direction(self):
        class Movie(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
                'other':{
                    'deep':unicode,
                },
                'notindexed':unicode,
                'alsoindexed':unicode,
            }
            
            indexes = [
                {
                    'fields':{'standard':INDEX_DESCENDING},
                    'unique':True,
                },
                {
                    'fields':{'alsoindexed':INDEX_ASCENDING, 'other.deep':INDEX_DESCENDING},
                    'unique':True,
                },
            ]
        movie = Movie()
        movie['standard'] = u'test'
        movie.save()
        
        db = CONNECTION['test']
        index1 = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_-1', 'unique':True})
        index2 = db.system.indexes.find_one({'ns':'test.mongokit', 'name': 'alsoindexed_1_other.deep_-1', 'unique':True})
        
        assert index1 is not None, 'No Index Found'
        assert index2 is not None, 'Index not found'

    def test_bad_index_descriptor(self):
        class Movie(MongoDocument):
            structure = {
                'standard':unicode,
            }
            indexes = [
                {
                    'unique':True,
                },
            ]
        self.assertRaises(BadIndexError, Movie)
        class Movie(MongoDocument):
            structure = {
                'standard':unicode,
            }
            indexes = [
                {
                    'fields':{'standard':INDEX_DESCENDING},
                    'uniq':True,
                },
            ]
        self.assertRaises(BadIndexError, Movie)
        class Movie(MongoDocument):
            structure = {
                'standard':unicode,
            }
            indexes = [
                {
                    'fields':'std',
                },
            ]
        self.assertRaises(ValueError, Movie)
        class Movie(MongoDocument):
            structure = {
                'standard':unicode,
            }
            indexes = [
                {
                    'fields':{'standard':2},
                },
            ]
        self.assertRaises(BadIndexError, Movie)
        class Movie(MongoDocument):
            structure = {
                'standard':unicode,
            }
            indexes = [
                {
                    'fields':{'standard':1, 'bla':1},
                },
            ]
        self.assertRaises(ValueError, Movie)
        class Movie(MongoDocument):
            structure = {
                'standard':unicode,
            }
            indexes = [
                {
                    'fields':['std'],
                },
            ]
        self.assertRaises(ValueError, Movie)

    def test_index_ttl(self):
        class Movie(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
            }
            
            indexes = [
                {
                    'fields':'standard',
                    'unique':True,
                    'ttl': 86400
                },
        # If indexes are still broken validation will choke on the ttl
            ]
        movie = Movie()
        movie['standard'] = u'test'
        movie.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_1', 'unique':True, 'key':{'standard':1}})
        
        assert item is not None, 'No Index Found'

    def test_index_simple_inheritance(self):
        class DocA(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
            }
            
            indexes = [
                {
                    'fields':'standard',
                    'unique':True,
                },
            ]

        class DocB(DocA):
            structure = {
                'docb':unicode,
            }
            
        docb = DocB()
        docb['standard'] = u'test'
        docb['docb'] = u'foo'
        docb.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_1', 'unique':True, 'key':{'standard':1}})
        
        assert item is not None, 'No Index Found'

    def test_index_inheritance(self):
        class DocA(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'standard':unicode,
            }
            
            indexes = [
                {
                    'fields':'standard',
                    'unique':True,
                },
            ]

        class DocB(DocA):
            structure = {
                'docb':unicode,
            }
            indexes = [
                {
                    'fields':'docb',
                    'unique':True,
                },
            ]

            
        docb = DocB()
        docb['standard'] = u'test'
        docb['docb'] = u'foo'
        docb.save()
        
        db = CONNECTION['test']
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'standard_1', 'unique':True, 'key':{'standard':1}})
        item = db.system.indexes.find_one({'ns':'test.mongokit', 'name':'docb_1', 'unique':True, 'key':{'docb':1}})
        
        assert item is not None, 'No Index Found'


    def test_index_real_world(self):
        import datetime
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "mydoc":{
                    "creation_date":datetime.datetime,
                }
            }
            #indexes = [{'fields':[('mydoc.creation_date',-1), ('_id',1)]}]

        date = datetime.datetime.utcnow()

        mydoc = MyDoc()
        mydoc['creation_date'] = date
        mydoc['_id'] = u'aaa'
        mydoc.save()


        mydoc3 = MyDoc()
        mydoc3['creation_date'] = date
        mydoc3['_id'] = u'bbb'
        mydoc3.save()

        import time
        time.sleep(1)
        date2 = datetime.datetime.utcnow()

        mydoc2 = MyDoc()
        mydoc2['creation_date'] = date2
        mydoc2['_id'] = u'aa'
        mydoc2.save()

        time.sleep(1)
        date3 = datetime.datetime.utcnow()

        mydoc4 = MyDoc()
        mydoc4['creation_date'] = date3
        mydoc4['_id'] = u'ccc'
        mydoc4.save()

        MyDoc.collection.ensure_index([('mydoc.creation_date',-1), ('_id',1)])
        print list(MyDoc.db.system.indexes.find())
        results = [i['_id'] for i in MyDoc.fetch().sort([('mydoc.creation_date',-1),('_id',1)])]
        assert results  == [u'aaa', u'bbb', u'aa', u'ccc'], results

    def test_index_pymongo(self):
        import datetime
        date = datetime.datetime.utcnow()
        import pymongo
        collection = pymongo.Connection()['test']['test_index']

        mydoc = {'mydoc':{'creation_date':date}, '_id':u'aaa'}
        collection.insert(mydoc)

        mydoc2 = {'mydoc':{'creation_date':date}, '_id':u'bbb'}
        collection.insert(mydoc2)

        import time
        time.sleep(1)
        date2 = datetime.datetime.utcnow()

        mydoc3 = {'mydoc':{'creation_date':date2}, '_id':u'aa'}
        collection.insert(mydoc3)

        time.sleep(1)
        date3 = datetime.datetime.utcnow()

        mydoc4 = {'mydoc':{'creation_date':date3}, '_id':u'ccc'}
        collection.insert(mydoc4)

        collection.ensure_index([('mydoc.creation_date',-1), ('_id',1)])
        print list(collection.database().system.indexes.find())

        results = [i['_id'] for i in collection.find().sort([('mydoc.creation_date',-1),('_id',1)])]
        assert results  == [u'aaa', u'bbb', u'aa', u'ccc'], results
