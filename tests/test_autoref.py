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

class AutoRefTestCase(unittest.TestCase):
    """Tests AutoRef case"""
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')

    def test_simple_autoref(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
            }
        self.connection.register([DocA])

        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 3
        doca.save()

        class DocB(Document):
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True
        self.connection.register([DocB])

        docb = self.col.DocB()
        # the structure is automaticly filled by the corresponding structure
        assert docb == {'b': {'doc_a':None}}, docb
        #docb.validate()
        docb['_id'] = 'docb'
        docb['b']['doc_a'] = 4
        self.assertRaises(SchemaTypeError, docb.validate)
        docb['b']['doc_a'] = doca
        assert docb == {'b': {'doc_a': {'a': {'foo': 3}, '_id': 'doca'}}, '_id': 'docb'}
        docb.save()
        saved_docb = self.col.find_one({'_id':'docb'})
        print saved_docb
        _docb = self.col.DocB.get_from_id('docb')
        print _docb, type(_docb), type(_docb['b']['doc_a'])
        print _docb['b']['doc_a'].structure
        assert saved_docb['b']['doc_a'] == DBRef(database='test', collection='mongokit', id='doca'), saved_docb['b']['doc_a']

        docb_list = list(self.col.DocB.fetch())
        assert len(docb_list) == 1
        new_docb = docb_list[0]
        assert isinstance(new_docb['b']['doc_a'], self.col.DocA.__class__)
        assert docb == {'b': {'doc_a': {'a': {'foo': 3}, '_id': 'doca'}}, '_id': 'docb'}, docb
        assert docb['b']['doc_a']['a']['foo'] == 3
        docb['b']['doc_a']['a']['foo'] = 4
        docb.save()
        assert docb['b']['doc_a']['a']['foo'] == 4, docb
        assert self.col.DocA.fetch().next()['a']['foo'] == 4
        assert doca['a']['foo'] == 4, doca['a']['foo']
        saved_docb = self.col.DocB.collection.find_one({'_id':'docb'})
        assert saved_docb['b']['doc_a'] == DBRef(database='test', collection='mongokit', id='doca'), saved_docb['b']['doc_a']
        assert self.col.DocB.fetch_one() == docb
        assert self.col.DocB.find_one({'_id':'docb'}) == docb

    def test_autoref_with_default_values(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
                "abis":{'bar':int},
            }
        self.connection.register([DocA])
        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 2
        doca.save()

        class DocB(Document):
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True
            default_values = {'b.doc_a':doca}
        self.connection.register([DocB])

        docb = self.col.DocB()
        assert docb == {'b': {'doc_a': {'a': {'foo': 2}, 'abis': {'bar': None}, '_id': 'doca'}}}, docb
        docb.save()

    def test_autoref_with_required_fields(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
                "abis":{'bar':int},
            }
            required_fields = ['a.foo']
        self.connection.register([DocA])

        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 2
        doca.save()

        class DocB(Document):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True
        self.connection.register([DocB])

        docb = self.col.DocB()
        docb['b']['doc_a'] = doca
        assert docb == {'b': {'doc_a': {'a': {'foo': 2}, 'abis': {'bar': None}, '_id': 'doca'}}}, docb
        docb['_id'] = 'docb'
        docb['b']['doc_a']['a']['foo'] = None 
        self.assertRaises(RequireFieldError, docb.validate)
        docb['b']['doc_a']['a']['foo'] = 4 
        docb.save()
    
        docb['b']['doc_a'] = None
        docb.save()

    def test_badautoref(self):
        """Test autoref enabled, but embed the wrong kind of document.
        Assert that it tells us it's a bad embed.
        """
        class EmbedDoc(Document):
            structure = {
                "spam": unicode
            }
        self.connection.register([EmbedDoc])
        embed = self.col.EmbedDoc()
        embed["spam"] = u"eggs"
        embedObj = embed.save()
        assert embedObj

        class EmbedOtherDoc(Document):
            structure = {
                "ham": unicode
            }
        self.connection.register([EmbedOtherDoc])
        embedOther = self.connection.test.embed_other.EmbedOtherDoc()
        embedOther["ham"] = u"eggs"
        embedOtherObj = embedOther.save()
        assert embedOtherObj

        class MyDoc(Document):
            use_autorefs = True
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
            use_autorefs = True
        self.connection.register([MyDoc])
        mydoc = self.connection.test.autoref.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc["spam"] = embedOtherObj
        
        self.assertRaises(SchemaTypeError, mydoc.save) 
  
    def test_badautoref_not_enabled(self):
        # Test that, when autoref is disabled
        # we refuse to allow a MongoDocument 
        # to be valid schema.

        class EmbedDoc(Document):
            structure = {
                "spam": unicode
            }
        self.connection.register([EmbedDoc])
        embed = self.connection.test['autoref.embed'].EmbedDoc()
        embed["spam"] = u"eggs"
        embedObj = embed.save()
        assert embedObj

        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
        self.assertRaises(StructureError, self.connection.register, [MyDoc])

    def test_subclass(self):
        # Test autoref enabled, but embed a subclass.
        # e.g. if we say EmbedDoc, a subclass of EmbedDoc 
        # is also valid.
        
        class EmbedDoc(Document):
            structure = {
                "spam": unicode
            }
        self.connection.register([EmbedDoc])
        embed = self.connection.test['autoref.embed'].EmbedDoc()
        embed["spam"] = u"eggs"
        embed.save()

        class EmbedOtherDoc(EmbedDoc):
            structure = {
                "ham": unicode
            }
        self.connection.register([EmbedOtherDoc])
        embedOther = self.connection.test['autoref.embed_other'].EmbedOtherDoc()
        embedOther["ham"] = u"eggs"
        embedOther.save()
        assert embedOther

        class MyDoc(Document):
            use_autorefs = True
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
        self.connection.register([MyDoc])
        mydoc = self.connection.test.autoref.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc["spam"] = embedOther
        
        mydoc.save()
        assert mydoc['spam'].collection.name == "autoref.embed_other"
        assert mydoc['spam'] == embedOther

    def test_autoref_in_list(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
            }
        self.connection.register([DocA])

        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 3
        doca.save()

        doca2 = self.col.DocA()
        doca2['_id'] = 'doca2'
        doca2['a']['foo'] = 5
        doca2.save()

        class DocB(Document):
            structure = {
                "b":{"doc_a":[DocA]},
            }
            use_autorefs = True
        self.connection.register([DocB])

        docb = self.col.DocB()
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
        assert isinstance(docb.collection.find_one({'_id':'docb'})['b']['doc_a'][0], DBRef), type(docb.collection.find_one({'_id':'docb'})['b']['doc_a'][0])

        assert docb == {'b': {'doc_a': [{'a': {'foo': 3}, '_id': 'doca'}]}, '_id': 'docb'}
        assert docb['b']['doc_a'][0]['a']['foo'] == 3
        docb['b']['doc_a'][0]['a']['foo'] = 4
        docb.save()
        assert docb['b']['doc_a'][0]['a']['foo'] == 4, type(docb['b']['doc_a'][0])
        assert doca['a']['foo'] == 4, doca['a']['foo']

        docb['b']['doc_a'].append(doca2)
        assert docb == {'b': {'doc_a': [{'a': {'foo': 4}, '_id': 'doca'}, {'a': {'foo': 5}, '_id': 'doca2'}]}, '_id': 'docb'}
        docb.validate()
    
    def test_autoref_retrieval(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
            }
        self.connection.register([DocA])

        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 3
        doca.save()

        class DocB(Document):
            structure = {
                "b":{
                    "doc_a":DocA,
                    "deep": {"doc_a_deep":DocA}, 
                    "deeper": {"doc_a_deeper":DocA,
                               "inner":{"doc_a_deepest":DocA}}
                },
                
            }
            use_autorefs = True
        self.connection.register([DocB])

        docb = self.col.DocB()
        # the structure is automaticly filled by the corresponding structure
        docb['_id'] = 'docb'
        docb['b']['doc_a'] = doca
    
        # create a few deeper  docas
        deep = self.col.DocA()
        #deep['_id'] = 'deep' 
        deep['a']['foo'] = 5
        deep.save()
        docb['b']['deep']['doc_a_deep'] = deep
        deeper = self.col.DocA()
        deeper['_id'] = 'deeper'
        deeper['a']['foo'] = 8
        deeper.save()
        docb['b']['deeper']['doc_a_deeper'] = deeper
        deepest = self.col.DocA()
        deepest['_id'] = 'deepest'
        #deepest['_id'] = 'deeper'
        deepest['a']['foo'] = 18
        deepest.save()
        docb['b']['deeper']['inner']['doc_a_deepest'] = deepest

        docb.save()

        # now, does retrieval function as expected?
        test_doc = self.col.DocB.get_from_id(docb['_id'])
        assert isinstance(test_doc['b']['doc_a'], DocA), type(test_doc['b']['doc_a'])
        assert test_doc['b']['doc_a']['a']['foo'] == 3
        assert isinstance(test_doc['b']['deep']['doc_a_deep'], DocA)
        assert test_doc['b']['deep']['doc_a_deep']['a']['foo'] == 5
        assert isinstance(test_doc['b']['deeper']['doc_a_deeper'], DocA)
        assert test_doc['b']['deeper']['doc_a_deeper']['a']['foo'] == 8, test_doc
        assert isinstance(test_doc['b']['deeper']['inner']['doc_a_deepest'], DocA)
        assert test_doc['b']['deeper']['inner']['doc_a_deepest']['a']['foo'] == 18

    def test_autoref_with_same_embed_id(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
            }
        self.connection.register([DocA])

        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['a']['foo'] = 3
        doca.save()

        class DocB(Document):
            structure = {
                "b":{
                    "doc_a":DocA,
                    "deep": {"doc_a_deep":DocA}, 
                },
                
            }
            use_autorefs = True
        self.connection.register([DocB])

        docb = self.col.DocB()
        docb['_id'] = 'docb'
        docb['b']['doc_a'] = doca
        # create a few deeper  docas
        deep = self.col.DocA()
        deep['_id'] = 'doca'
        deep['a']['foo'] = 5
        deep.save()
        docb['b']['deep']['doc_a_deep'] = deep

        docb.save()

        test_doc = self.col.DocB.get_from_id(docb['_id'])
        assert test_doc['b']['doc_a']['a']['foo'] == 5
        assert test_doc['b']['deep']['doc_a_deep']['a']['foo'] == 5

    def test_autorefs_embed_in_list_with_bad_reference(self):
        class User(Document):
            structure = {'name':unicode}
        self.connection.register([User])

        class Group(Document):
            use_autorefs = True
            structure = {
                   'name':unicode,
                   'members':[User], #users
               }
        self.connection.register([User, Group])

        user = self.col.User()
        user['_id'] = u'fixe'
        user['name'] = u'fixe'
        user.save()

        user2 = self.col.User()
        user['_id'] = u'namlook'
        user2['name'] = u'namlook'
        user2.save()

        group = self.col.Group()
        group['members'].append(user)
        self.assertRaises(AutoReferenceError, group.save)

    def test_autorefs_with_dynamic_collection(self):
        class DocA(Document):
            structure = {'a':unicode}

        class DocB(Document):
            structure = {'b':DocA}
            use_autorefs = True
        self.connection.register([DocA, DocB])

        doca = self.connection.test.doca.DocA()
        doca['a'] = u'bla'
        doca.save()

        docb = self.connection.test.docb.DocB()
        docb['b'] = doca
        docb.save()

        assert docb['b']['a'] == 'bla'
        assert docb['b'].collection.name == "doca"

        doca2 = self.connection.test.doca2.DocA()
        doca2['a'] = u'foo'
        doca2.save()

        docb2 = self.connection.test.docb.DocB()
        docb2['b'] = doca2
        docb2.save()

        assert docb2['b']['a'] == 'foo' 
        assert docb2['b'].collection.name == 'doca2'
        assert docb2.collection.name == 'docb'

        assert list(self.connection.test.docb.DocB.fetch()) == [docb, docb2]
        
    def test_autorefs_with_dynamic_db(self):
        class DocA(Document):
            structure = {'a':unicode}

        class DocB(Document):
            structure = {'b':DocA}
            use_autorefs = True
        self.connection.register([DocA, DocB])

        doca = self.connection.dba.mongokit.DocA()
        doca['a'] = u'bla'
        doca.save()

        docb = self.connection.dbb.mongokit.DocB()
        docb['b'] = doca
        docb.save()

        assert docb['b']['a'] == 'bla'
        docb = self.connection.dbb.mongokit.DocB.get_from_id(docb['_id'])
        assert isinstance(docb['b'], DocA)
 
