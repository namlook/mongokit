# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
__author__ = 'n.namlook {at} gmail {dot} com'

import unittest

from mongokit import *

class MongoDocumentTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = Connection()['test']['mongokit']
        
    def tearDown(self):
        Connection()['test'].drop_collection('mongokit')

    def test_no_structure(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
        self.assertRaises(StructureError, MyDoc)

    def test_empty_structure(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {}
        assert MyDoc() == {}

    def test_load_with_dict(self):
        doc = {"foo":1, "bla":{"bar":u"spam"}}
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {"foo":int, "bla":{"bar":unicode}}
        mydoc = MyDoc(doc)
        assert mydoc == doc
        mydoc.validate()
        
    def test_simple_structure(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":unicode,
                "bar":int
            }
        assert MyDoc() == {"foo":None, "bar":None}

    def test_missed_field(self):
        doc = {"foo":u"arf"}
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":unicode,
                "bar":{"bla":int}
            }
        mydoc = MyDoc(doc)
        del mydoc["bar"]
        self.assertRaises(StructureError, mydoc.validate)

    def test_unknown_field(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":unicode,
            }
        mydoc = MyDoc()
        mydoc["bar"] = 4
        self.assertRaises(StructureError, mydoc.validate)

    def test_authorized_type(self):
       for auth_type in authorized_types:
            if auth_type is dict:
                auth_type = {}
            class MyDoc(MongoDocument):
                connection_path = "test.mongokit"
                structure = { "foo":auth_type }
            if type(auth_type) is dict:
                assert MyDoc() == {"foo":{}}, MyDoc()
            else:
                assert MyDoc() == {"foo":None}, MyDoc()
 
    def test_not_authorized_type(self):
       for unauth_type in [set, str]:
            class MyDoc(MongoDocument):
                connection_path = "test.mongokit"
                structure = { "foo":unauth_type }
            self.assertRaises( AssertionError, MyDoc )

    def test_type_from_functions(self):
        from datetime import datetime
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":datetime,
            }
        assert MyDoc() == {"foo":None}, MyDoc()
        mydoc = MyDoc()
        mydoc['foo'] = datetime.now()
        mydoc.validate()

    def test_save(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
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
        mydoc.save()

        saved_doc = self.collection.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

    def test_save_without_connection_path(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["foo"] = 1
        self.assertRaises(ConnectionError, mydoc.save)

    def test_duplicate_required(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {"foo":unicode}
            required_fields = ["foo", "foo"]
        self.assertRaises(DuplicateRequiredError, MyDoc)
    
    def test_flat_required(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":unicode,
            }
            required_fields = ["foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )
             
    def test_nested_required(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                },
            }
            required_fields = ["bla.foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )

    def test_list_required(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":[]
            }
            required_fields = ["foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )

    def test_dict_required(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":{}
            }
            required_fields = ["foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )
   
    def test_non_typed_list(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":[]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [u"bla", 23]
        mydoc.validate()
        mydoc['foo'] = [set([1,2]), "bla"]
        self.assertRaises(AuthorizedTypeError, mydoc.validate)
        
 
    def test_typed_list(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":[int]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [1,2,3]
        mydoc.validate()
        mydoc['foo'] = [u"bla"]
        self.assertRaises(TypeError, mydoc.validate)

    def _test_typed_list_with_dict(self):
        # TODO
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":[{unicode:int}]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [{u"bla":1},{u"ble":2}]
        mydoc.validate()
        mydoc['foo'] = [{u"bla":u"bar"}]
        self.assertRaises(TypeError, mydoc.validate)

    def _test_typed_list_with_list(self):
        # TODO
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":[[unicode]]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [[u"bla",u"blu"],[u"ble",u"bli"]]
        mydoc.validate()
        mydoc['foo'] = [[u"bla",1]]
        self.assertRaises(TypeError, mydoc.validate)

    def test_default_values(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":int
            }
            default_values = {"foo":42}
        mydoc = MyDoc()
        assert mydoc["foo"] == 42

    def test_default_values_from_function(self):
        import time
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":float
            }
            default_values = {"foo":time.time}
        mydoc = MyDoc()
        mydoc.validate()
   
    def test_default_list_values(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":[int]
            }
            default_values = {"foo":[42,3]}
        mydoc = MyDoc()
        assert mydoc["foo"] == [42,3]
        mydoc.validate()

    def test_default_list_nested_values(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":{
                    "bar":[int]
                }
            }
            default_values = {"foo.bar":[42,3]}
        mydoc = MyDoc()
        assert mydoc["foo"]["bar"] == [42,3]

    def test_default_dict_values(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":{}
            }
            default_values = {"foo":{"bar":42}}
        mydoc = MyDoc()
        assert mydoc["foo"] == {"bar":42}, mydoc
         
    def test_default_dict_checked_values(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":{unicode:int}
            }
            default_values = {"foo":{u"bar":42}}
        mydoc = MyDoc()
        assert mydoc["foo"] == {"bar":42}, mydoc
          
    def test_validators(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":unicode,
                "bar":{
                    "bla":int
                }
            }
            validators = {
                "foo":lambda x: x.startswith("http://"),
                "bar.bla": lambda x: x > 5
            }
        mydoc = MyDoc()
        mydoc["foo"] = u"google.com"
        self.assertRaises(ValidationError, mydoc.validate)
        mydoc["foo"] = u"http://google.com"
        mydoc.validate()
        mydoc['bar']['bla'] = 2
        self.assertRaises(ValidationError, mydoc.validate)
        mydoc['bar']['bla'] = 42
        mydoc.validate()

    def test_signals(self):
        def fill_foo(doc, value):
            if value is not None:
                doc['foo'] = unicode(value)
            else:
                doc['foo'] = None
       
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":unicode,
                "bar":{
                    "bla":int
                }
            }
            signals = {"bar.bla":fill_foo}

        mydoc = MyDoc()
        mydoc['bar']['bla'] = 4
        assert mydoc['foo'] is None
        print mydoc
        mydoc.validate()
        assert mydoc['foo'] == "4"
        mydoc['bar']['bla'] = None
        mydoc.validate()
        assert mydoc['foo'] is None

    def test_simple_inheritance(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int}
            }

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }

        assert B() == {"a":{"foo":None}, "b":{"bar":None}}
 
    def test_required_inheritance(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int}
            }
            required_fields = ["a.foo"]

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }

        b = B()
        self.assertRaises(RequireFieldError, b.validate)
        b['a']['foo'] = 4
        b.validate()
 
    def test_default_values_inheritance(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int}
            }
            default_values = {"a.foo":3}

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }

        assert B() == {"a":{"foo":3}, "b":{"bar":None}}
 
        class C(A):
            structure = {
                "c":{"spam":unicode}
            }

        assert C() == {"a":{"foo":5}, "c":{"spam":None}}, C()

    def test_validators_inheritance(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int}
            }
            validators = {"a.foo":lambda x: x>1}

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }

        b = B()
        b["a"]["foo"] = 0
        self.assertRaises(ValidationError, b.validate)
        b["a"]["foo"] = 3
        b.validate()

        class C(A):
            validators = {"a.foo":lambda x: x<1}

        class D(C):
            pass

        d = D()
        d["a"]["foo"] = 4
        self.assertRaises(ValidationError, d.validate)
        d["a"]["foo"] = -3
        d.validate()
 
    def test_complete_inheritance(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int}
            }
            default_values = {"a.foo":3}

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }
            required_fields = ['b.bar']
            default_values = {"a.foo":5}

        b =  B()
        assert b == {"a":{"foo":5}, "b":{"bar":None}}
        self.assertRaises(RequireFieldError, b.validate)
 
        class C(B):
            structure = {
                "c":{"spam":unicode}
            }

        c =  C()
        assert c == {"a":{"foo":5}, "b":{"bar":None}, "c":{"spam":None}}, C()
        self.assertRaises(RequireFieldError, c.validate)
        c["b"]["bar"] = u"bla"
        c.validate()
  
    def test_simple_manual_inheritance(self):
        class A(MongoDocument):
            auto_inheritance = False
            structure = {
                "a":{"foo":int}
            }

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }
            structure.update(A.structure)

        assert B() == {"a":{"foo":None}, "b":{"bar":None}}
 
    def test_required_inheritance(self):
        class A(MongoDocument):
            auto_inheritance = False
            structure = {
                "a":{"foo":int}
            }
            required_fields = ["a.foo"]

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }
            structure.update(A.structure)
            required_fields = A.required_fields

        b = B()
        self.assertRaises(RequireFieldError, b.validate)
        b['a']['foo'] = 4
        b.validate()
 
    def test_default_values_inheritance(self):
        class A(MongoDocument):
            auto_inheritance = False
            structure = {
                "a":{"foo":int}
            }
            default_values = {"a.foo":3}

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }
            structure.update(A.structure)
            default_values = A.default_values

        assert B() == {"a":{"foo":3}, "b":{"bar":None}}
 
        class C(A):
            structure = {
                "c":{"spam":unicode}
            }
            structure.update(A.structure)
            default_values = A.default_values
            default_values.update({"a.foo":5})

        assert C() == {"a":{"foo":5}, "c":{"spam":None}}, C()
  
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

    def test_get_from_id(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["_id"] = "bar"
        mydoc["foo"] = 3
        mydoc.save()
        fetched_doc = MyDoc.get_from_id("bar")
        mydoc == fetched_doc

    def test_find(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":int,
            }
        for i in range(10):
            mydoc = MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        docs_list = [i["foo"] for i in MyDoc.find({"foo":{"$gt":4}})]
        assert docs_list == [5,6,7,8,9]


    def test_id(self):
        class MyDoc(MongoDocument):
            connection_path = "test.mongokit"
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["_id"] = "bar"
        assert mydoc.id == "bar"
        mydoc.id = "ble"
        assert mydoc['_id'] == "ble"
        mydoc.save()
