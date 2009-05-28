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

class InheritanceTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = Connection()['test']['mongokit']
        
    def tearDown(self):
        Connection()['test'].drop_collection('mongokit')

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
            default_values = {"a.foo":5}

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

    def test_signals_inheritance(self):
        def fill_foo(doc, value):
            doc["foo"] = unicode(doc["foo"])

        def fill_bar(doc, value):
            doc["bar"]["bla"] = unicode(doc["bar"]["bla"])
       
        class A(MongoDocument):
            structure = {
                "foo":unicode,
            }
            signals = {"foo":fill_foo}

        class B(A):
            structure = {
                "bar":{"bla":unicode}
            }
            signals = {"bar.bla":fill_bar}
            default_values = {"bar.bla":3}

        b = B()
        b['foo'] = 4
        b.validate()
        assert b['foo'] == "4"
        assert b["bar"]["bla"] == "3", b

 
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

    def test_polymorphisme(self):
        class A(MongoDocument):
            structure = {
                "a":{"foo":int}
            }
            default_values = {"a.foo":3}

        class B(MongoDocument):
            structure = {
                "b":{"bar":unicode}
            }
            required_fields = ['b.bar']

        b =  B()
        assert b == {"b":{"bar":None}}
        self.assertRaises(RequireFieldError, b.validate)
 
        class C(A,B):
            auto_inheritance = False
            structure = {
                "c":{"spam":unicode}
            }
            structure.update(A.structure)
            structure.update(B.structure)
            default_values = {"a.foo":5}
            required_fields = B.required_fields

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
 
    def test_required_manual_inheritance(self):
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
 
    def test_default_values_manual_inheritance(self):
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
  

