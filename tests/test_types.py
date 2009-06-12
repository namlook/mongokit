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

class TypesTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = Connection()['test']['mongokit']
        
    def tearDown(self):
        Connection()['test'].drop_collection('mongokit')

    def test_authorized_type(self):
       for auth_type in authorized_types:
            if auth_type is dict:
                auth_type = {}
            class MyDoc(MongoDocument):
                structure = { "foo":auth_type }
            if type(auth_type) is dict:
                assert MyDoc() == {"foo":{}}, MyDoc()
            elif auth_type is list:
                assert MyDoc() == {"foo":[]}
            else:
                assert MyDoc() == {"foo":None}, auth_type
 
    def test_not_authorized_type(self):
       for unauth_type in [set, str]:
            class MyDoc(MongoDocument):
                structure = { "foo":unauth_type }
            self.assertRaises( StructureError, MyDoc )

    def test_type_from_functions(self):
        from datetime import datetime
        class MyDoc(MongoDocument):
            structure = {
                "foo":datetime,
            }
        assert MyDoc() == {"foo":None}, MyDoc()
        mydoc = MyDoc()
        mydoc['foo'] = datetime.now()
        mydoc.validate()

    def test_non_typed_list(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":[]
            }
        mydoc = MyDoc()
        mydoc.validate()
        assert mydoc['foo'] == []
        mydoc['foo'] = [u"bla", 23]
        mydoc.validate()
        mydoc['foo'] = [set([1,2]), "bla"]
        self.assertRaises(AuthorizedTypeError, mydoc.validate)

#        class MyDoc(MongoDocument):
#            structure = {
#                "foo":list
#            }
#        mydoc = MyDoc()
#        mydoc.validate()
#        assert mydoc['foo'] == []
#        mydoc['foo'] = [u"bla", 23]
#        mydoc.validate()
#        mydoc['foo'] = [set([1,2]), "bla"]
#        self.assertRaises(AuthorizedTypeError, mydoc.validate)
  
    def test_typed_list(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":[int]
            }
        mydoc = MyDoc()
        mydoc.validate()
        assert mydoc['foo'] == []
        mydoc['foo'] = [1,2,3]
        mydoc.validate()
        mydoc['foo'] = [u"bla"]
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_typed_list_with_dict(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":[{unicode:int}]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [{u"bla":1},{u"ble":2}]
        mydoc.validate()
        mydoc['foo'] = [{u"bla":u"bar"}]
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_typed_list_with_list(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":[[unicode]]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [[u"bla",u"blu"],[u"ble",u"bli"]]
        mydoc.validate()
        mydoc['foo'] = [[u"bla",1]]
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_dict_unicode_typed_list(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:[int]}
            }
        mydoc = MyDoc()
        mydoc['foo'] = {u"bar":[1,2,3]}
        mydoc.validate()
        mydoc['foo'] = {u"bar":[u"bla"]}
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = {3:[1,2,3]}
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_with_custom_object(self):
        class MyDict(dict):
            pass
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:int}
            }
        mydoc = MyDoc()
        mydict = MyDict()
        mydict[u"foo"] = 3
        mydoc["foo"] = mydict
        mydoc.validate()
 
    def test_custom_object_as_type(self):
        class MyDict(dict):
            pass
        class MyDoc(MongoDocument):
            structure = {
                "foo":MyDict({unicode:int})
            }
        mydoc = MyDoc()
        mydict = MyDict()
        mydict[u"foo"] = 3
        mydoc["foo"] = mydict
        mydoc.validate()
        mydoc['foo'] = {u"foo":"7"}
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_list_instead_of_dict(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:[unicode]}
            }
        mydoc = MyDoc()
        mydoc['foo'] = [u'bla']
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def _test_big_nested_example(self):
        # XXX TODO
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:[int], u"bar":{"spam":{int:[unicode]}}},
                "bla":{"blo":{"bli":[{"arf":unicode}]}},
            }
        mydoc = MyDoc()
        print mydoc
        mydoc['foo'].update({u"bir":[1,2,3]})
        mydoc['foo'][u'bar'][u'spam'] = {1:[u'bla', u'ble'], 3:[u'foo', u'bar']}
        mydoc.validate()
        mydoc['bla']['blo']['bli'] = [{u"bar":[u"bla"]}]
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['bla']['blo']['bli'] = [{u"arf":[1]}]
        self.assertRaises(SchemaTypeError, mydoc.validate)

        
    def test_adding_custom_type(self):
        import mongokit
        mongokit.authorized_types.append(str)
        class MyDoc(MongoDocument):
            structure = {
                "foo":str,
            }
        mydoc = MyDoc()
        mongokit.authorized_types.remove(str)
 
