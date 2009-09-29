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
import logging

logging.basicConfig(level=logging.DEBUG)

from mongokit import *
from pymongo.objectid import ObjectId

CONNECTION = Connection()

class AutoRefTestCase(unittest.TestCase):
    """Tests AutoRef case"""
    def setUp(self):
        self.collection = CONNECTION['test']['autoref']
        
    def tearDown(self):
        CONNECTION.drop_database('test')

    def test_autoref(self):
        """Test the basic functionality.
        If autoreferencing is enabled, can we embed a document?
        """
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "a":{'foo':int},
            }

        doca = DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 3
        doca.save()

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True

        docb = DocB()
        # the structure is automaticly filled by the corresponding structure
        assert docb == {'b': {'doc_a':None}}
        docb.validate()
        docb['_id'] = 'docb'
        docb['b']['doc_a'] = 4
        self.assertRaises(SchemaTypeError, docb.validate)
        docb['b']['doc_a'] = doca
        assert docb == {'b': {'doc_a': {'a': {'foo': 3}, '_id': 'doca'}}, '_id': 'docb'}
        docb.save()

        # the '_ns' field is added to the docb
        assert docb == {'_ns': u'mongokit', 'b': {'doc_a': {'a': {'foo': 3}, '_id': 'doca'}}, '_id': 'docb'}
        assert docb['b']['doc_a']['a']['foo'] == 3
        docb['b']['doc_a']['a']['foo'] = 4
        docb.save()
        assert docb['b']['doc_a']['a']['foo'] == 4
        assert doca['a']['foo'] == 4

    def test_autoref_with_default_values(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "a":{'foo':int},
                "abis":{'bar':int},
            }
        doca = DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 2
        doca.save()

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True
            default_values = {'b.doc_a':doca}

        docb = DocB()
        assert docb == {'b': {'doc_a': {'a': {'foo': 2}, 'abis': {'bar': None}, '_id': 'doca'}}}
        docb.save()

    def test_autoref_with_required_fields(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "a":{'foo':int},
                "abis":{'bar':int},
            }
            required_fields = ['a.foo']

        doca = DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 2
        doca.save()

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True

        docb = DocB()
        docb['b']['doc_a'] = doca
        assert docb == {'b': {'doc_a': {'a': {'foo': 2}, 'abis': {'bar': None}, '_id': 'doca'}}}, docb
        docb['_id'] = 'docb'
        docb['b']['doc_a']['a']['foo'] = None 
        self.assertRaises(RequireFieldError, docb.validate)
        docb['b']['doc_a']['a']['foo'] = 4 
        docb.save()

    def test_badautoref(self):
        """Test autoref enabled, but embed the wrong kind of document.
        Assert that it tells us it's a bad embed.
        """
        class EmbedDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "spam": unicode
            }
        embed = EmbedDoc()
        embed["spam"] = u"eggs"
        embedObj = embed.save()
        assert embedObj

        class EmbedOtherDoc(MongoDocument):
            db_name = "test"
            collection_name = "embed_other"
            structure = {
                "ham": unicode
            }
        embedOther = EmbedOtherDoc()
        embedOther["ham"] = u"eggs"
        embedOtherObj = embedOther.save()
        assert embedOtherObj

        class MyDoc(MongoDocument):
            use_autorefs = True
            db_name = "test"
            collection_name = "autoref"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc["spam"] = embedOtherObj
        
        self.assertRaises(SchemaTypeError, mydoc.save) 
  
    def test_badautoref_not_enabled(self):
        """Test that, when autoref is disabled
        we refuse to allow a MongoDocument 
        to be valid schema.
        """
        class EmbedDoc(MongoDocument):
            db_name = "test"
            collection_name = "autoref.embed"
            structure = {
                "spam": unicode
            }
        embed = EmbedDoc()
        embed["spam"] = u"eggs"
        embedObj = embed.save()
        assert embedObj

        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "autoref"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
        self.assertRaises(StructureError, MyDoc) 

    def test_subclass(self):
        """Test autoref enabled, but embed a subclass.
        e.g. if we say EmbedDoc, a subclass of EmbedDoc 
        is also valid.
        """
        class EmbedDoc(MongoDocument):
            db_name = "test"
            collection_name = "autoref.embed"
            structure = {
                "spam": unicode
            }
        embed = EmbedDoc()
        embed["spam"] = u"eggs"
        embedObj = embed.save()
        assert embedObj

        class EmbedOtherDoc(EmbedDoc):
            db_name = "test"
            collection_name = "autoref.embed_other"
            structure = {
                "ham": unicode
            }
        embedOther = EmbedOtherDoc()
        embedOther["ham"] = u"eggs"
        embedOtherObj = embedOther.save()
        assert embedOtherObj

        class MyDoc(MongoDocument):
            use_autorefs = True
            db_name = "test"
            collection_name = "autoref"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc["spam"] = embedOtherObj
        
        id = mydoc.save()
        assert id

    def test_autoref_in_list(self):
        """Test the basic functionality.
        If autoreferencing is enabled, can we embed a document?
        """
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "a":{'foo':int},
            }

        doca = DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 3
        doca.save()

        doca2 = DocA()
        doca2['_id'] = 'doca2'
        doca2['a']['foo'] = 5
        doca2.save()

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "b":{"doc_a":[DocA]},
            }
            use_autorefs = True

        docb = DocB()
        # the structure is automaticly filled by the corresponding structure
        assert docb == {'b': {'doc_a':[]}}, docb
        docb.validate()
        docb['_id'] = 'docb'
        docb['b']['doc_a'].append(u'bla')
        self.assertRaises(SchemaTypeError, docb.validate)
        docb['b']['doc_a'] = []
        docb['b']['doc_a'].append(doca)
        assert docb == {'b': {'doc_a': [{'a': {'foo': 3}, '_id': 'doca'}]}, '_id': 'docb'}
        docb.save()

        # the '_ns' field is added to the docb
        assert docb == {'_ns': u'mongokit', 'b': {'doc_a': [{'a': {'foo': 3}, '_id': 'doca'}]}, '_id': 'docb'}
        assert docb['b']['doc_a'][0]['a']['foo'] == 3
        docb['b']['doc_a'][0]['a']['foo'] = 4
        docb.save()
        assert docb['b']['doc_a'][0]['a']['foo'] == 4
        assert doca['a']['foo'] == 4

        docb['b']['doc_a'].append(doca2)
        assert docb == {'_ns': u'mongokit', 'b': {'doc_a': [{'a': {'foo': 4}, '_id': 'doca'}, {'a': {'foo': 5}, '_id': 'doca2'}]}, '_id': 'docb'}
        docb.validate()


