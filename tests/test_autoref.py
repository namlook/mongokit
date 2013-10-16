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
import logging

logging.basicConfig(level=logging.DEBUG)

from mongokit import *
from bson.objectid import ObjectId

class AutoRefTestCase(unittest.TestCase):
    """Tests AutoRef case"""
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')
        self.connection.drop_database('test2')

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
        _docb = self.col.DocB.get_from_id('docb')
        assert saved_docb['b']['doc_a'] == DBRef(database='test', collection='mongokit', id='doca'), saved_docb['b']['doc_a']

        docb_list = list(self.col.DocB.fetch())
        assert len(docb_list) == 1
        new_docb = docb_list[0]
        assert isinstance(new_docb['b']['doc_a'], DocA), new_docb['b']['doc_a'].__class__
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

    def test_simple_autoref2(self):
        class Embed(Document):
            structure = {
                'foo': dict,
                'bar': int,
            }

        class Doc(Document):
            structure = {
                'embed':Embed,
                'eggs': unicode,
            }
            use_autorefs = True
        self.connection.register([Embed, Doc])

        embed = self.col.Embed()
        embed['foo'] = {'hello':u'monde'}
        embed['bar'] = 3
        embed.save()

        doc = self.col.Doc()
        doc['embed'] = embed
        doc['eggs'] = u'arf'
        doc.save()

        assert doc == {'embed': {u'_id': embed['_id'], u'bar': 3, u'foo': {u'hello': u'monde'}}, '_id': doc['_id'], 'eggs': u'arf'}, doc

        doc = self.col.Doc.fetch_one()
        doc['embed']['foo']['hello'] = u'World'
        doc.save()

        assert doc == {'embed': {u'_id': embed['_id'], u'bar': 3, u'foo': {u'hello': u'World'}}, '_id': doc['_id'], 'eggs': u'arf'}, doc
        assert self.col.Embed.fetch_one() == {u'_id': embed['_id'], u'bar': 3, u'foo': {u'hello': u'World'}}

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
        embed.save()
        assert embed

        class EmbedOtherDoc(Document):
            structure = {
                "ham": unicode
            }
        self.connection.register([EmbedOtherDoc])
        embedOther = self.connection.test.embed_other.EmbedOtherDoc()
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
            use_autorefs = True
        self.connection.register([MyDoc])
        mydoc = self.connection.test.autoref.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc["spam"] = embedOther
        
        self.assertRaises(SchemaTypeError, mydoc.save) 
  
    def test_badautoref_not_enabled(self):
        # Test that, if autoref is disabled
        # adding a Document to the structure act
        # like a regular dict

        class EmbedDoc(Document):
            structure = {
                "spam": unicode
            }
        self.connection.register([EmbedDoc])
        embed = self.connection.test['autoref.embed'].EmbedDoc()
        embed["spam"] = u"eggs"
        embed.save()
        assert embed

        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam": EmbedDoc,
            }
        self.connection.register([MyDoc])
        doc = self.col.MyDoc()
        self.assertEqual(doc, {'bla': {'foo': None, 'bar': None}, 'spam': None})

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
        # the structure is automatically filled by the corresponding structure
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
        assert docb['b']['doc_a'][0]['a']['foo'] == 4, docb['b']['doc_a'][0]['a']['foo']
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
        # the structure is automatically filled by the corresponding structure
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
        deep['_id'] = 'doca' # XXX same id of doca, this will be erased by doca when saving docb
        deep['a']['foo'] = 5
        deep.save()
        docb['b']['deep']['doc_a_deep'] = deep

        docb.save()

        test_doc = self.col.DocB.get_from_id(docb['_id'])
        assert test_doc['b']['doc_a']['a']['foo'] == 3, test_doc['b']['doc_a']['a']
        assert test_doc['b']['deep']['doc_a_deep']['a']['foo'] == 3, test_doc['b']['deep']['doc_a_deep']['a']['foo']

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

    def test_autoref_without_validation(self):
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
            skip_validation = True
        self.connection.register([DocB])

        docb = self.col.DocB()
        docb['_id'] = 'docb'
        docb['b']['doc_a'] = doca
        docb.save()

    def test_autoref_updated(self):
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
        doca2['a']['foo'] = 6
        doca2.save()

        class DocB(Document):
            structure = {
                "b":{"doc_a":[DocA]},
            }
            use_autorefs = True
        self.connection.register([DocB])

        docb = self.col.DocB()
        docb['_id'] = 'docb'
        docb.save()
        assert docb ==  {'b': {'doc_a': []}, '_id': 'docb'}
        docb['b']['doc_a'] = [doca, doca2]
        docb.save()
        assert docb == {'b': {'doc_a': [{u'a': {u'foo': 3}, u'_id': u'doca'}, {u'a': {u'foo': 6}, u'_id': u'doca2'}]}, '_id': 'docb'}
        docb['b']['doc_a'].pop(0)
        docb.save()
        assert docb == {'b': {'doc_a': [{u'a': {u'foo': 6}, u'_id': u'doca2'}]}, '_id': 'docb'}
        fetched_docb = self.col.DocB.get_from_id('docb')
        assert fetched_docb == {u'_id': u'docb', u'b': {u'doc_a': [{u'a': {u'foo': 6}, u'_id': u'doca2'}]}}

        docb = self.col.DocB()
        docb['_id'] = 'docb'
        docb.save()
        assert docb ==  {'b': {'doc_a': []}, '_id': 'docb'}
        docb['b']['doc_a'] = [doca, doca2]
        docb.save()
        assert docb == {'b': {'doc_a': [{u'a': {u'foo': 3}, u'_id': u'doca'}, {u'a': {u'foo': 6}, u'_id': u'doca2'}]}, '_id': 'docb'}, docb
        docb['b']['doc_a'].pop(0)
        docb['b']['doc_a'].append(doca)
        docb.save()
        assert docb == {'b': {'doc_a': [{u'a': {u'foo': 6}, u'_id': u'doca2'}, {u'a': {u'foo': 3}, u'_id': u'doca'}]}, '_id': 'docb'}, docb
        fetched_docb = self.col.DocB.get_from_id('docb')
        assert fetched_docb == {u'_id': u'docb', u'b': {u'doc_a': [{u'a': {u'foo': 6}, u'_id': u'doca2'}, {u'a': {u'foo': 3}, u'_id': u'doca'}]}}

    def test_autoref_updated_with_default_values(self):
        class DocA(Document):
            structure = {
                "a":{'foo':int},
                   "abis":{'bar':int},
                }
            default_values = {'a.foo':2}
            required_fields = ['abis.bar']

        self.connection.register([DocA])
        doca = self.col.DocA()
        doca['_id'] = 'doca'
        doca['abis']['bar'] = 3
        doca.save()

        class DocB(Document):
            structure = {
                "b":{"doc_a":DocA},
            }
            use_autorefs = True

        self.connection.register([DocB])
        docb = self.col.DocB()
        docb['_id'] = 'docb'
        docb['b']['doc_a'] = doca
        assert docb == {'b': {'doc_a': {'a': {'foo': 2}, 'abis': {'bar': 3}, '_id': 'doca'}}, '_id': 'docb'}, docb
        docb['b']['doc_a']['a']['foo'] = 4
        docb.save()
        assert docb == {'b': {'doc_a': {'a': {'foo': 4}, 'abis': {'bar': 3}, '_id': 'doca'}}, '_id': 'docb'}, docb
        assert doca['a']['foo'] == 4

    def test_autoref_with_None(self):
        class RootDocument(Document):
           use_dot_notation=True
           use_autorefs = True
           structure = {}

        class User(RootDocument):
           collection_name = "users"
           structure = {
               "email": unicode,
               "password": unicode,
           }
           required_fields = [ "email", "password" ]
           indexes = [
               { "fields": "email",
                 "unique": True,
               },
           ]
        self.connection.register([User])
        User = self.col.User
        u = User()
        u['email'] = u'....'
        u['password'] = u'....'
        u.save()
        assert u['_id'] != None
    
        class ExampleSession(RootDocument):
           #collection_name = "sessions"
           use_autorefs = True
           structure   = {
               "user": User,
               "token": unicode,
           }
        # raise an assertion because User is a CallableUser, not User
        self.connection.register([ExampleSession])
        ex = self.col.ExampleSession()
        self.assertRaises(SchemaTypeError, ex.validate)

    def test_autoref_without_database_specified(self):
        class EmbedDoc(Document):
            use_dot_notation = True
            structure = {
               "foo": unicode,
            }

        class Doc(Document):
           use_dot_notation=True
           use_autorefs = True
           force_autorefs_current_db = True
           __database__ = "test"
           __collection__ = "mongokit"
           structure = {
               "embed": EmbedDoc,
           }
        self.connection.register([EmbedDoc, Doc])

        embed = self.connection.test.embed_docs.EmbedDoc()
        embed['foo'] = u'bar'
        embed.save()

        raw_doc = {'embed':DBRef(
            collection=self.connection.test.embed_docs.name,
            id=embed['_id'])
        }
        self.connection.test.mongokit.insert(raw_doc)
        doc = self.connection.Doc.find_one({'_id':raw_doc['_id']})
        assert isinstance(doc.embed, EmbedDoc)
        self.assertTrue(doc.embed.foo, u"bar")

    def test_recreate_and_reregister_class_with_reference(self):
        class CompanyDocument(Document):
            collection_name = "test_companies"
            use_autorefs = True
            use_dot_notation = True
            structure = {
                "name": unicode,
            }

        class UserDocument(Document):
            collection_name = "test_users"
            use_autorefs = True
            use_dot_notation = True
            structure = {
                "email": unicode,
                "company": CompanyDocument,
            }

        class SessionDocument(Document):
            collection_name = "test_sessions"
            use_autorefs = True
            use_dot_notation = True
            structure = {
                "token": unicode,
                "owner": UserDocument,
            }
        self.connection.register([CompanyDocument, UserDocument, SessionDocument])

        company = self.col.database[CompanyDocument.collection_name].CompanyDocument()
        company.name = u"Company"
        company.save()

        company_owner = self.col.database[UserDocument.collection_name].UserDocument()
        company_owner.email = u"manager@test.com"
        company_owner.company = company
        company_owner.save()

        s = self.col.database[SessionDocument.collection_name].SessionDocument()
        s.token = u'asddadsad'
        s.owner = company_owner
        s.save()

        sbis= self.col.database[SessionDocument.collection_name].SessionDocument.find_one({"token": u"asddadsad" })
        assert sbis == s, sbis

        class CompanyDocument(Document):
            collection_name = "test_companies"
            use_autorefs = True
            structure = {
                "name": unicode,
            }

        class UserDocument(Document):
            collection_name = "test_users"
            use_autorefs = True
            structure = {
                "email": unicode,
                "company": CompanyDocument,
            }

        class SessionDocument(Document):
            collection_name = "test_sessions"
            use_autorefs = True
            structure = {
                "token": unicode,
                "owner": UserDocument,
            }
        self.connection.register([CompanyDocument, UserDocument, SessionDocument])

        sbis= self.col.database[SessionDocument.collection_name].SessionDocument.find_one({"token": u"asddadsad" })
        assert sbis == s, sbis


    def test_nested_autorefs(self):
        class DocA(Document):
            structure = {
                'name':unicode,
              }
            use_autorefs = True

        class DocB(Document):
            structure = {
                'name': unicode,
                'doca' : DocA,
            }
            use_autorefs = True

        class DocC(Document):
            structure = {
                'name': unicode,
                'docb': DocB,
                'doca': DocA,
            }
            use_autorefs = True

        class DocD(Document):
            structure = {
                'name': unicode,
                'docc': DocC,
            }
            use_autorefs = True
        self.connection.register([DocA, DocB, DocC, DocD])

        doca = self.col.DocA()
        doca['name'] = u'Test A'
        doca.save()

        docb = self.col.DocB()
        docb['name'] = u'Test B'
        docb['doca'] = doca
        docb.save()

        docc = self.col.DocC()
        docc['name'] = u'Test C'
        docc['docb'] = docb
        docc['doca'] = doca
        docc.save()

        docd = self.col.DocD()
        docd['name'] = u'Test D'
        docd['docc'] = docc
        docd.save()

        doca = self.col.DocA.find_one({'name': 'Test A'})
        docb = self.col.DocB.find_one({'name': 'Test B'})
        docc = self.col.DocC.find_one({'name': 'Test C'})
        docd = self.col.DocD.find_one({'name': 'Test D'})


    def test_nested_autoref_in_list_and_dict(self):
        class DocA(Document):
            structure = {
                'name':unicode,
              }
            use_autorefs = True


        class DocB(Document):
            structure = {
                'name': unicode,
                'test': [{
                    'something' : unicode,
                    'doca' : DocA,
                }]
            }
            use_autorefs = True

        self.connection.register([DocA, DocB])

        doca = self.col.DocA()
        doca['name'] = u'Test A'
        doca.save()

        docc = self.col.DocA()
        docc['name'] = u'Test C'
        docc.save()

        docb = self.col.DocB()
        docb['name'] = u'Test B'
        docb['test'].append({u'something': u'foo', 'doca': doca})
        docb['test'].append({u'something': u'foo', 'doca': docc})
        docb.save()

        raw_docb = self.col.find_one({'name':'Test B'})
        assert isinstance(raw_docb['test'][0]['doca'], DBRef), raw_docb['test'][0]

    def test_dereference(self):

        class DocA(Document):
            structure = {
                'name':unicode,
              }
            use_autorefs = True

        self.connection.register([DocA])

        doca = self.col.DocA()
        doca['name'] = u'Test A'
        doca.save()

        docb = self.connection.test2.mongokit.DocA()
        docb['name'] = u'Test B'
        docb.save()

        dbref = doca.get_dbref()

        self.assertRaises(TypeError, self.connection.test.dereference, 1)
        self.assertRaises(ValueError, self.connection.test.dereference, docb.get_dbref(), DocA)
        assert self.connection.test.dereference(dbref) == {'_id':doca['_id'], 'name': 'Test A'}
        assert isinstance(self.connection.test.dereference(dbref), dict)
        assert self.connection.test.dereference(dbref, DocA) == {'_id':doca['_id'], 'name': 'Test A'}
        assert isinstance(self.connection.test.dereference(dbref, DocA), DocA)

    def test_autorefs_with_list(self):
        class VDocument(Document):
            db_name = 'MyDB'
            use_dot_notation = True
            use_autorefs = True
            skip_validation = True

            def __init__(self, *args, **kwargs):
                super(VDocument, self).__init__(*args, **kwargs)

            def save(self, *args, **kwargs):
                kwargs.update({'validate':True})
                return super(VDocument, self).save(*args, **kwargs)

        class H(VDocument):
            structure = {'name':[ObjectId], 'blah':[unicode], 'foo': [{'x':unicode}]}
        self.connection.register([H, VDocument])

        h = self.col.H()
        obj_id = ObjectId()
        h.name.append(obj_id)
        h.blah.append(u'some string')
        h.foo.append({'x':u'hey'})
        h.save()
        assert h == {'blah': [u'some string'], 'foo': [{'x': u'hey'}], 'name': [obj_id], '_id': h['_id']}

    def test_autorefs_with_list2(self):
        class DocA(Document):
            structure = {'name':unicode}

        class DocB(Document):
            structure = {
                'docs':[{
                    'doca': [DocA],
                    'inc':int,
                }],
            }
            use_autorefs = True

        self.connection.register([DocA, DocB])

        doca = self.col.DocA()
        doca['_id'] = u'doca'
        doca['name'] = u"foo"
        doca.save()

        self.col.insert(
          {'_id': 'docb', 'docs':[
            {
              'doca':[DBRef(database='test', collection='mongokit', id='doca')],
              'inc':2,
            },
          ]
        })
        assert self.col.DocB.find_one({'_id':'docb'}) == {u'docs': [{u'doca': [{u'_id': u'doca', u'name': u'foo'}], u'inc': 2}], u'_id': u'docb'}

    def test_autorefs_with_required(self):
        import datetime
        import uuid

        @self.connection.register
        class User(Document):
           structure = {
             'email': unicode,
           }

        @self.connection.register
        class Event(Document):
           structure = {
             'user': User,
             'title': unicode,
           }
           required_fields = ['user', 'title']
           use_autorefs = True

        user = self.connection.test.users.User()
        user.save()
        event = self.connection.test.events.Event()
        event['user'] = user
        event['title'] = u"Test"
        event.validate()
        event.save()

