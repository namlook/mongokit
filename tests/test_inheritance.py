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

from mongokit import *

class InheritanceTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = Connection()['test']['mongokit']
        
    def tearDown(self):
        Connection()['test'].drop_collection('mongokit')

    def test_simple_inheritance(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":int}
            }

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }

        assert B() == {"a":{"foo":None}, "b":{"bar":None}}, B()

    def test_simple_inheritance_without_child_structure(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":int}
            }

        class B(A):
            pass    # no structure defined for B

        b = B()
        b.structure['secret'] = int
        assert 'secret' in b.structure
        assert 'secret' not in A.structure
 
    def test_required_inheritance(self):
        class A(SchemaDocument):
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
        class A(SchemaDocument):
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

    def test_default_values_inheritance_with_function(self):
        from datetime import datetime
        class A(SchemaDocument):
            structure = {
                "a":{"foo":datetime}
            }
            default_values = {"a.foo":datetime.utcnow}

        class B(A):
            structure = {
                "b":{"bar":unicode}
            }

        assert isinstance(B()['a']['foo'], datetime)
 
        class C(A):
            structure = {
                "c":{"spam":unicode}
            }
            default_values = {"a.foo":datetime(2008,8,8)}

        assert C() == {"a":{"foo":datetime(2008, 8, 8)}, "c":{"spam":None}}, C()


    def test_validators_inheritance(self):
        class A(SchemaDocument):
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

    def test_complexe_validation_inheritance(self):
        class A(SchemaDocument):
            structure = {
                "foo":unicode,
            }
            def validate(self):
                self["foo"] = unicode(self["foo"])
                super(A, self).validate()

        class B(A):
            structure = {
                "bar":{"bla":unicode}
            }
            default_values = {"bar.bla":3}
            def validate(self):
                self["bar"]["bla"] = unicode(self["bar"]["bla"])
                super(B, self).validate()

        b = B()
        b['foo'] = 4
        b.validate()
        assert b['foo'] == "4"
        assert b["bar"]["bla"] == "3", b

 
    def test_complete_inheritance(self):
        class A(SchemaDocument):
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

    def test_polymorphism(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":int}
            }
            default_values = {"a.foo":3}

        class B(SchemaDocument):
            structure = {
                "b":{"bar":unicode}
            }
            required_fields = ['b.bar']

        b =  B()
        assert b == {"b":{"bar":None}}
        self.assertRaises(RequireFieldError, b.validate)
 
        class C(A,B):
            structure = {
                "c":{"spam":unicode}
            }
            default_values = {"a.foo":5}

        c =  C()
        assert c == {"a":{"foo":5}, "b":{"bar":None}, "c":{"spam":None}}, C()
        self.assertRaises(RequireFieldError, c.validate)
        c["b"]["bar"] = u"bla"
        c.validate()
   
    def test_simple_manual_inheritance(self):
        class A(SchemaDocument):
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
        class A(SchemaDocument):
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
        class A(SchemaDocument):
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
  

