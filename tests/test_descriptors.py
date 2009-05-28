# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Nicolas Clairon
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

class DescriptorsTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = Connection()['test']['mongokit']
        
    def tearDown(self):
        Connection()['test'].drop_collection('mongokit')

    def test_duplicate_required(self):
        class MyDoc(MongoDocument):
            structure = {"foo":unicode}
            required_fields = ["foo", "foo"]
        self.assertRaises(DuplicateRequiredError, MyDoc)
    
    def test_flat_required(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":unicode,
            }
            required_fields = ["foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )
             
    def test_nested_required(self):
        class MyDoc(MongoDocument):
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
            structure = {
                "foo":[]
            }
            required_fields = ["foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )

    def test_list_required2(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{int:[]}
            }
            required_fields = ["foo.$int"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )


    def test_dict_required(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{}
            }
            required_fields = ["foo"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )

    def test_dict_nested_required(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:{"bar":int}}
            }
            required_fields = ["foo.$unicode.bar"]
        mydoc = MyDoc()
        self.assertRaises(RequireFieldError, mydoc.validate )

    def test_default_values(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":int
            }
            default_values = {"foo":42}
        mydoc = MyDoc()
        assert mydoc["foo"] == 42

    def test_default_values_from_function(self):
        import time
        class MyDoc(MongoDocument):
            structure = {
                "foo":float
            }
            default_values = {"foo":time.time}
        mydoc = MyDoc()
        mydoc.validate()
   
    def test_default_list_values(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":[int]
            }
            default_values = {"foo":[42,3]}
        mydoc = MyDoc()
        assert mydoc["foo"] == [42,3]
        mydoc.validate()

    def test_default_list_nested_values(self):
        class MyDoc(MongoDocument):
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
            structure = {
                "foo":{}
            }
            default_values = {"foo":{"bar":42}}
        mydoc = MyDoc()
        assert mydoc["foo"] == {"bar":42}, mydoc
         
    def test_default_dict_checked_values(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:int}
            }
            default_values = {"foo":{u"bar":42}}
        mydoc = MyDoc()
        assert mydoc["foo"] == {"bar":42}, mydoc

    def test_default_dict_nested_checked_values(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{unicode:{"bla":int, "ble":unicode}}
            }
            default_values = {"foo":{u"bar":{"bla":42, "ble":u"arf"}}}
        mydoc = MyDoc()
        assert mydoc["foo"] == {u"bar":{"bla":42, "ble":u"arf"}}, mydoc
           
    def test_validators(self):
        class MyDoc(MongoDocument):
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

    def test_multiple_validators(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":unicode,
            }
            validators = {
                "foo":[lambda x: x.startswith("http://"),lambda x: x.endswith(".com")],
            }
        mydoc = MyDoc()
        mydoc["foo"] = u"google.com"
        self.assertRaises(ValidationError, mydoc.validate)
        mydoc["foo"] = u"http://google.fr"
        self.assertRaises(ValidationError, mydoc.validate)
        mydoc["foo"] = u"http://google.com"
        mydoc.validate()

    def test_signals(self):
        def fill_foo(doc, value):
            if value is not None:
                doc['foo'] = unicode(value)
            else:
                doc['foo'] = None
       
        class MyDoc(MongoDocument):
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

    def test_signals2(self):
        def fill_foo(doc, value):
            doc["foo"] = unicode(doc["foo"])

        def fill_bar(doc, value):
            doc["bar"]["bla"] = unicode(doc["bar"]["bla"])
       
        class MyDoc(MongoDocument):
            structure = {
                "foo":unicode,
                "bar":{"bla":unicode}
            }
            signals = {"foo":fill_foo, "bar.bla":fill_bar}
            default_values = {"bar.bla":3}

        mydoc = MyDoc()
        mydoc['foo'] = 4
        mydoc.validate()
        assert mydoc['foo'] == "4"
        assert mydoc["bar"]["bla"] == "3", mydoc


    def test_multiple_signals(self):
        def fill_foo(doc, value):
            if value is not None:
                doc['foo'] = unicode(value)
            else:
                doc['foo'] = None

        def fill_bla(doc, value):
            doc["ble"] = doc["foo"]
       
        class MyDoc(MongoDocument):
            structure = {
                "foo":unicode,
                "bar":{
                    "bla":int
                },
                "ble":unicode,
            }
            signals = {"bar.bla":[fill_foo, fill_bla]}

        mydoc = MyDoc()
        mydoc['bar']['bla'] = 4
        assert mydoc['foo'] is None
        mydoc.validate()
        assert mydoc['foo'] == "4"
        assert mydoc["ble"] == "4"
        mydoc['bar']['bla'] = None
        mydoc.validate()
        assert mydoc['foo'] is None
        assert mydoc['ble'] is None

    def test_bad_signals(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{"bar":int},
            }
            signals = {"foo.bla":lambda x:x}
        self.assertRaises(ValueError, MyDoc)

    def test_bad_default_values(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{"bar":int},
            }
            default_values = {"foo.bla":2}
        self.assertRaises(ValueError, MyDoc)

    def test_bad_validators(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":{"bar":int},
            }
            validators = {"foo.bla":lambda x:x}
        self.assertRaises(ValueError, MyDoc)

 
