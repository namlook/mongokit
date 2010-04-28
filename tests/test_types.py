#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2010, Nicolas Clairon
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

from mongokit.schema_document import *
from mongokit import Document, Connection

class TypesTestCase(unittest.TestCase):

    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')


    def test_authorized_type(self):
       for auth_type in SchemaDocument.authorized_types:
            if auth_type is dict:
                auth_type = {}
            class MyDoc(SchemaDocument):
                structure = { "foo":auth_type }
            if type(auth_type) is dict:
                assert MyDoc() == {"foo":{}}, MyDoc()
            elif auth_type is list:
                assert MyDoc() == {"foo":[]}
            else:
                assert MyDoc() == {"foo":None}, auth_type
 
    def test_not_authorized_type(self):
        for unauth_type in [set, str]:
            class MyDoc(SchemaDocument):
                structure = { "foo":[unauth_type] }
            self.assertRaises( StructureError, MyDoc )
            class MyDoc(SchemaDocument):
                structure = { "foo":(unauth_type) }
            self.assertRaises( StructureError, MyDoc )
            class MyDoc2(SchemaDocument):
                structure = { 'foo':[{int:unauth_type }]}
            self.assertRaises( StructureError, MyDoc2 )
            class MyDoc3(SchemaDocument):
                structure = { 'foo':[{unauth_type:int }]}
            self.assertRaises( AuthorizedTypeError, MyDoc3 )

        class MyDoc4(SchemaDocument):
            structure = {1:unicode}
        self.assertRaises( StructureError, MyDoc4 )


    def test_type_from_functions(self):
        from datetime import datetime
        class MyDoc(SchemaDocument):
            structure = {
                "foo":datetime,
            }
        assert MyDoc() == {"foo":None}, MyDoc()
        mydoc = MyDoc()
        mydoc['foo'] = datetime.now()
        mydoc.validate()

    def test_non_typed_list(self):
        class MyDoc(SchemaDocument):
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
        mydoc['foo'] = u"bla"
        self.assertRaises(SchemaTypeError, mydoc.validate)

#        class MyDoc(SchemaDocument):
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
        class MyDoc(SchemaDocument):
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
        class MyDoc(SchemaDocument):
            structure = {
                "foo":[{unicode:int}]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [{u"bla":1},{u"ble":2}]
        mydoc.validate()
        mydoc['foo'] = [{u"bla":u"bar"}]
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_typed_list_with_list(self):
        class MyDoc(SchemaDocument):
            structure = {
                "foo":[[unicode]]
            }
        mydoc = MyDoc()
        mydoc['foo'] = [[u"bla",u"blu"],[u"ble",u"bli"]]
        mydoc.validate()
        mydoc['foo'] = [[u"bla",1]]
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_typed_tuple(self):
        class MyDoc(SchemaDocument):
            structure = {
                "foo":(int, unicode, float)
            }
        mydoc = MyDoc()
        mydoc.validate()
        assert mydoc['foo'] == [None, None, None]
        mydoc['foo'] = [u"bla", 1, 4.0]
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = [1, u"bla"]
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = u"bla"
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = [1,u'bar',3.2]
        mydoc.validate()
        mydoc['foo'] = [None, u"bla", 3.1]
        mydoc.validate()
        mydoc['foo'][0] = 50
        mydoc.validate()

    def test_nested_typed_tuple(self):
        class MyDoc(SchemaDocument):
            structure = {
                "foo":{'bar':(int, unicode, float)}
            }
        mydoc = MyDoc()
        mydoc.validate()
        assert mydoc['foo']['bar'] == [None, None, None]
        mydoc['foo']['bar'] = [u"bla", 1, 4.0]
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo']['bar'] = [1, u"bla"]
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo']['bar'] = [1,u'bar',3.2]
        mydoc.validate()
        mydoc['foo']['bar'] = [None, u"bla", 3.1]
        mydoc.validate()
        mydoc['foo']['bar'][0] = 50
        mydoc.validate()

    def test_saving_tuple(self):
        class MyDoc(Document):
            structure = { 'foo': (int, unicode, float) }
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        assert mydoc == {'foo': [None, None, None]}, mydoc
        mydoc['foo'] = (1, u'a', 1.1) # note that this will be converted to list
        assert mydoc == {'foo': (1, u'a', 1.1000000000000001)}, mydoc
        mydoc.save()
        mydoc = self.col.find_one()

        class MyDoc(Document):
            structure = {'foo':[unicode]}
        self.connection.register([])
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['foo'] = (u'bla', u'bli', u'blu', u'bly')
        mydoc.save()
        mydoc = self.col.get_from_id(mydoc['_id'])


    def test_nested_typed_tuple_in_list(self):
        class MyDoc(SchemaDocument):
            structure = {
                "foo":{'bar':[(int, unicode, float)]}
            }
        mydoc = MyDoc()
        mydoc.validate()
        assert mydoc == {'foo': {'bar': []}}
        mydoc['foo']['bar'].append([u"bla", 1, 4.0])
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo']['bar'] = []
        mydoc['foo']['bar'].append([1, u"bla"])
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo']['bar'] = []
        mydoc['foo']['bar'].append([1,u'bar',3.2])
        mydoc.validate()
        mydoc['foo']['bar'].append([None, u"bla", 3.1])
        mydoc.validate()
        mydoc['foo']['bar'][1][0] = 50
        mydoc.validate()

    def test_dict_unicode_typed_list(self):
        class MyDoc(SchemaDocument):
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
        class MyDoc(SchemaDocument):
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
        class MyDoc(SchemaDocument):
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

        class MyInt(int):
            pass
        class MyDoc(SchemaDocument):
            structure = {
                "foo":MyInt,
            }
        mydoc = MyDoc()
        mydoc["foo"] = MyInt(3)
        mydoc.validate()
        mydoc['foo'] = 3
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_list_instead_of_dict(self):
        class MyDoc(SchemaDocument):
            structure = {
                "foo":{unicode:[unicode]}
            }
        mydoc = MyDoc()
        mydoc['foo'] = [u'bla']
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def _test_big_nested_example(self):
        # XXX TODO
        class MyDoc(SchemaDocument):
            structure = {
                "foo":{unicode:[int], u"bar":{"spam":{int:[unicode]}}},
                "bla":{"blo":{"bli":[{"arf":unicode}]}},
            }
        mydoc = MyDoc()
        mydoc['foo'].update({u"bir":[1,2,3]})
        mydoc['foo'][u'bar'][u'spam'] = {1:[u'bla', u'ble'], 3:[u'foo', u'bar']}
        mydoc.validate()
        mydoc['bla']['blo']['bli'] = [{u"bar":[u"bla"]}]
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['bla']['blo']['bli'] = [{u"arf":[1]}]
        self.assertRaises(SchemaTypeError, mydoc.validate)

        
    def test_adding_custom_type(self):
        class MyDoc(SchemaDocument):
            structure = {
                "foo":str,
            }
            authorized_types = SchemaDocument.authorized_types + [str]
        mydoc = MyDoc()
    
    def test_schema_operator(self):
        from mongokit.operators import SchemaOperator
        class OP(SchemaOperator):
            repr = "op"
        op = OP()
        self.assertRaises(NotImplementedError, op.validate, "bla")
            

    def test_or_operator(self):
        from mongokit import OR
        assert repr(OR(unicode, str)) == "<unicode or str>"

        class BadMyDoc(SchemaDocument):
            structure = {"bla":OR(unicode,str)}
        self.assertRaises(StructureError, BadMyDoc)

        from datetime import datetime
        class MyDoc(SchemaDocument):
            structure = {
                "foo":OR(unicode,int),
                "bar":OR(unicode, datetime)
            }

        mydoc = MyDoc()
        assert str(mydoc.structure['foo']) == '<unicode or int>'
        assert str(mydoc.structure['bar']) == '<unicode or datetime>'
        assert mydoc == {'foo': None, 'bar': None}
        mydoc['foo'] = 3.0
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = u"foo"
        mydoc.validate()
        mydoc['foo'] = 3
        mydoc.validate()
        mydoc['foo'] = 'bar'
        self.assertRaises(SchemaTypeError, mydoc.validate)

        mydoc['foo'] = datetime.now()
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = u"foo"
        mydoc['bar'] = datetime.now()
        mydoc.validate()
        mydoc['bar'] = u"today"
        mydoc.validate()
        mydoc['bar'] = 25
        self.assertRaises(SchemaTypeError, mydoc.validate)

    def test_not_operator(self):
        from mongokit import NOT
        class BadMyDoc(SchemaDocument):
            structure = {"bla":NOT(unicode,str)}
        self.assertRaises(StructureError, BadMyDoc)

        from datetime import datetime
        class MyDoc(SchemaDocument):
            structure = {
                "foo":NOT(unicode,int),
                "bar":NOT(datetime)
            }

        mydoc = MyDoc()
        assert str(mydoc.structure['foo']) == '<not unicode, not int>', str(mydoc.structure['foo'])
        assert str(mydoc.structure['bar']) == '<not datetime>'
        assert mydoc == {'foo': None, 'bar': None}
        assert mydoc['foo'] is None
        assert mydoc['bar'] is None
        mydoc['foo'] = 3
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = u"foo"
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = 3.0
        mydoc.validate()
        mydoc['foo'] = datetime.now()
        mydoc.validate()

        mydoc['bar'] = datetime.now()
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['bar'] = u"today"
        mydoc.validate()
        mydoc['bar'] = 25
        mydoc.validate()

    def test_is_operator(self):
        from mongokit import IS
        class BadMyDoc(SchemaDocument):
            structure = {"bla":IS('bla',3)}
        self.assertRaises(StructureError, BadMyDoc)

        from datetime import datetime
        class MyDoc(SchemaDocument):
            structure = {
                "foo":IS(u'spam',u'eggs'),
                "bar":IS(u'3', 3)
            }

        mydoc = MyDoc()
        assert str(mydoc.structure['foo']) == "<is u'spam' or is u'eggs'>"
        assert str(mydoc.structure['bar']) == "<is u'3' or is 3>"
        assert mydoc == {'foo': None, 'bar': None}
        assert mydoc['foo'] is None
        assert mydoc['bar'] is None
        mydoc['foo'] = 3
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = u"bla"
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = datetime.now()
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = u"spam"
        mydoc.validate()
        mydoc['foo'] = u"eggs"
        mydoc.validate()

        mydoc['bar'] = datetime.now()
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['bar'] = u"today"
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['bar'] = 'foo'
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['bar'] = 3
        mydoc.validate()
        mydoc['bar'] = u"3"
        mydoc.validate()

    def test_subclassed_type(self):
        """
        accept all subclass of supported type
        """
        class CustomFloat(float):
            def __init__(self, float):
                self = float + 2
        class MyDoc(SchemaDocument):
            structure = {
                "foo":float,
            }
        mydoc = MyDoc()
        mydoc['foo'] = CustomFloat(4)
        mydoc.validate()


    def test_set_type(self):
        from mongokit import Set
        class MyDoc(Document):
            structure = {
                "tags":Set(int),
            }

        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['tags'] = set(["1","1","2","3","4"])
        self.assertRaises(ValueError, mydoc.validate)
        mydoc['tags'] = set([1,1,2,3,4])
        mydoc.save()

        doc = self.col.MyDoc.find_one()
        assert doc['tags'] == set([1,2,3,4]), doc['tags']

