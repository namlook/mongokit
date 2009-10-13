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
                structure = { "foo":unauth_type }
            self.assertRaises( StructureError, MyDoc )

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
        import mongokit
        mongokit.authorized_types.append(str)
        class MyDoc(SchemaDocument):
            structure = {
                "foo":str,
            }
        mydoc = MyDoc()
        mongokit.authorized_types.remove(str)
    

    def test_or_operator(self):
        from mongokit import OR
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
        

    def test_custom_type(self):
        import datetime

        class CustomDate(CustomType):
            mongo_type = unicode
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                "date": CustomDate(),
            }
            default_values = {'date':u'08-06-07'}
            
        foo = Foo()
        foo['_id'] = 1
        foo['date'] = datetime.datetime(2003,2,1)
        foo.save()
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo == {u'date': u'03-02-01', u'_id': 1}
        foo.save()

        foo2 = Foo()
        foo2['_id'] = 2
        foo2.save()
        foo2.save()
        assert foo['date'] == datetime.datetime(2003,2,1), foo['date']
        foo = Foo.get_from_id(1)
        assert foo['date'] == datetime.datetime(2003,2,1), foo['date']
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo['date'] == CustomDate().to_bson(datetime.datetime(2003,2,1)), saved_foo['date']
        foo2 = Foo.get_from_id(2)
        assert foo2['date'] == datetime.datetime(2008,6,7), foo2

    def test_custom_type_nested(self):
        import datetime
        class CustomDate(CustomType):
            mongo_type = unicode
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(MongoDocument):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'foo':{'date': CustomDate()},
            }
            default_values = {'foo.date':u'08-06-07'}
            
        foo = Foo()
        foo['_id'] = 1
        foo['foo']['date'] = datetime.datetime(2003,2,1)
        foo.save()
        foo.save()

        foo2 = Foo()
        foo2['_id'] = 2
        foo2.save()
        assert foo['foo']['date'] == datetime.datetime(2003,2,1), foo['foo']['date']
        foo = Foo.get_from_id(1)
        assert foo['foo']['date'] == datetime.datetime(2003,2,1)
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo['foo']['date'] == CustomDate().to_bson(datetime.datetime(2003,2,1)), foo['foo']['date']
        foo2 = Foo.get_from_id(2)
        assert foo2['foo']['date'] == datetime.datetime(2008,6,7), foo2

    def test_bad_custom_types(self):
        import datetime
        class CustomDate(CustomType):
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        self.assertRaises(TypeError, CustomDate)

    def test_custom_type_nested_list(self):
        import datetime

        class CustomPrice(CustomType):
            mongo_type = float
            def to_bson(self, value):
                return float(value)
            def to_python(self, value):
                return str(value)

        class Receipt(MongoDocument):
            use_dot_notation = True
            db_name = 'test'
            collection_name = 'test'
            structure = {
                'products': [
                      {
                        'sku': unicode,
                        'qty': int,
                        'price': CustomPrice(),
                      }
                ]
            }
          
        r = Receipt()
        r['_id'] = 'bla'
        r.products = []
        r.products.append({ 'sku': u'X-25A5F58B-61', 'qty': 1, 'price': '9.99' })
        r.products.append({ 'sku': u'Z-25A5F58B-62', 'qty': 2, 'price': '2.99' })
        r.save()
        r_saved = r.collection.find_one({'_id':'bla'})
        assert r_saved == {u'_id': u'bla', u'products': [{u'sku': u'X-25A5F58B-61', u'price': 9.9900000000000002, u'qty': 1}, {u'sku': u'Z-25A5F58B-62', u'price': 2.9900000000000002, u'qty': 2}]}

