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

class ApiTestCase(unittest.TestCase):
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
