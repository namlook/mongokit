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
        for unauth_type in [set]:
            failed = False
            try:
                class MyDoc(SchemaDocument):
                    structure = { "foo":[unauth_type] }
            except StructureError, e:
                self.assertEqual(str(e), "MyDoc: %s is not an authorized type" % unauth_type)
                failed = True
            self.assertEqual(failed, True)
            failed = False
            try:
                class MyDoc(SchemaDocument):
                    structure = { "foo":(unauth_type) }
            except StructureError, e:
                self.assertEqual(str(e), "MyDoc: %s is not an authorized type" % unauth_type)
                failed = True
            self.assertEqual(failed, True)
            failed = False
            try:
                class MyDoc2(SchemaDocument):
                    structure = { 'foo':[{int:unauth_type }]}
            except StructureError, e:
                self.assertEqual(str(e), "MyDoc2: %s is not an authorized type" % unauth_type)
                failed = True
            self.assertEqual(failed, True)
            failed = False
            try:
                class MyDoc3(SchemaDocument):
                    structure = { 'foo':[{unauth_type:int }]}
            except AuthorizedTypeError, e:
                self.assertEqual(str(e), "MyDoc3: %s is not an authorized type" % unauth_type)
                failed = True
            self.assertEqual(failed, True)

        failed = False
        try:
            class MyDoc4(SchemaDocument):
                structure = {1:unicode}
        except StructureError, e:
            self.assertEqual(str(e), "MyDoc4: 1 must be a basestring or a type")
            failed = True
        self.assertEqual(failed, True)


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

        failed = False
        try:
            class BadMyDoc(SchemaDocument):
                structure = {"bla":OR(unicode,str)}
        except StructureError, e:
            self.assertEqual(str(e), "BadMyDoc: <type 'str'> in <unicode or str> is not an authorized type (type found)")
            failed = True
        self.assertEqual(failed, True)

        from datetime import datetime
        class MyDoc(SchemaDocument):
            structure = {
                "foo":OR(unicode,int),
                "bar":OR(unicode, datetime),
                "foobar": OR(basestring, int),
            }

        mydoc = MyDoc()
        assert str(mydoc.structure['foo']) == '<unicode or int>'
        assert str(mydoc.structure['bar']) == '<unicode or datetime>'
        assert str(mydoc.structure['foobar']) == '<basestring or int>'
        assert mydoc == {'foo': None, 'bar': None, 'foobar': None}
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
        mydoc['bar'] = u"bar"
        mydoc["foo"] = u"foo"
        mydoc["foobar"] = "foobar"
        mydoc.validate()
        mydoc["foobar"] = datetime.now()
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc["foobar"] = 3
        mydoc.validate()

    def test_not_operator(self):
        from mongokit import NOT
        failed = False
        try:
            class BadMyDoc(SchemaDocument):
                structure = {"bla":NOT(unicode,str)}
        except StructureError, e:
            self.assertEqual(str(e), "BadMyDoc: <type 'str'> in <not unicode, not str> is not an authorized type (type found)")
            failed = True
        self.assertEqual(failed, True)

        from datetime import datetime
        class MyDoc(SchemaDocument):
            structure = {
                "foo":NOT(unicode,int),
                "bar":NOT(datetime),
                "foobar": NOT(basestring)
            }

        mydoc = MyDoc()
        assert str(mydoc.structure['foo']) == '<not unicode, not int>', str(mydoc.structure['foo'])
        assert str(mydoc.structure['bar']) == '<not datetime>'
        assert str(mydoc.structure['foobar']) == '<not basestring>'
        assert mydoc == {'foo': None, 'bar': None, 'foobar': None}
        assert mydoc['foo'] is None
        assert mydoc['bar'] is None
        assert mydoc['foobar'] is None
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
        mydoc['foobar'] = 'abc'
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foobar'] = 1
        mydoc.validate()

    def test_is_operator(self):
        from mongokit import IS
        failed = False
        try:
            class BadMyDoc(SchemaDocument):
                structure = {"bla":IS('bla',3)}
        except StructureError, e:
            self.assertEqual(str(e), "BadMyDoc: bla in <is 'bla' or is 3> is not an authorized type (str found)")
            failed = True
        self.assertEqual(failed, True)

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

    def test_set_type2(self):
        class MyDoc(Document):
                structure = {
                        'title':unicode,
                        'category':Set(unicode)
                }
                required_fields=['title']
        self.connection.register([MyDoc])
        doc = self.col.MyDoc()
        print doc # {'category': set([]), 'title': None}
        assert isinstance(doc['category'], set)
        try:
                doc.validate()
        except RequireFieldError as e:
                print e # title is required

        print doc # {'category': [], 'title': None}
        assert isinstance(doc['category'], set)
        doc['title']=u'hello'
        doc.validate()

    def test_int_type(self):
        @self.connection.register
        class MyDoc(Document):
            structure = {
                "foo":int,
            }

        mydoc = self.col.MyDoc()
        mydoc['foo'] = ''
        self.assertRaises(SchemaTypeError, mydoc.validate)
        mydoc['foo'] = 10
        mydoc.save()

    def test_uuid_type(self):
        import uuid
        @self.connection.register
        class MyDoc(Document):
            structure = {
                'uuid': uuid.UUID,
            }
        uid = uuid.uuid4()
        obj = self.col.MyDoc()
        obj['uuid'] = uid
        obj.save()

        assert isinstance(self.col.MyDoc.find_one()['uuid'], uuid.UUID)

    def test_binary_with_str_type(self):
        import bson
        @self.connection.register
        class MyDoc(Document):
            structure = {
                'my_binary': basestring,
            }
        obj = self.col.MyDoc()
        # non-utf8 string
        non_utf8 = "\xFF\xFE\xFF";
        obj['my_binary'] = non_utf8

        self.assertRaises(bson.errors.InvalidStringData, obj.validate)

    def test_binary_with_unicode_type(self):
        import bson
        @self.connection.register
        class MyDoc(Document):
            structure = {
                'my_binary': unicode,
            }
        obj = self.col.MyDoc()
        # non-utf8 string
        non_utf8 = "\xFF\xFE\xFF";
        obj['my_binary'] = non_utf8

        self.assertRaises(bson.errors.InvalidStringData, obj.validate)

    def test_binary_with_binary_type(self):
        import bson
        @self.connection.register
        class MyDoc(Document):
            structure = {
                'my_binary': bson.binary.Binary,
            }
        obj = self.col.MyDoc()
        # non-utf8 string
        non_utf8 = "\xFF\xFE\xFF";
        bin_obj = bson.binary.Binary(non_utf8)
        obj['my_binary'] = bin_obj
        obj.save()

        self.assertEquals(self.col.MyDoc.find_one()['my_binary'], bin_obj)
