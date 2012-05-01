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

class CustomTypesTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection['test'].drop_collection('mongokit')
        self.connection['test'].drop_collection('test')

    def test_custom_type(self):
        import datetime

        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = datetime.datetime
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                "date": CustomDate(),
            }
            default_values = {'date':datetime.datetime(2008, 6, 7)}
        self.connection.register([Foo])
            
        foo = self.col.Foo()
        foo['_id'] = 1
        foo['date'] = datetime.datetime(2003,2,1)
        foo.save()
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo == {u'date': u'03-02-01', u'_id': 1}
        foo.save()

        foo2 = self.col.Foo()
        foo2['_id'] = 2
        foo2.save()
        foo2.save()
        assert foo['date'] == datetime.datetime(2003,2,1), foo['date']
        foo = self.col.Foo.get_from_id(1)
        assert foo['date'] == datetime.datetime(2003,2,1), foo['date']
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo['date'] == CustomDate().to_bson(datetime.datetime(2003,2,1)), saved_foo['date']
        foo2 = self.col.Foo.get_from_id(2)
        assert foo2['date'] == datetime.datetime(2008,6,7), foo2

    def test_custom_type2(self):
        import datetime

        class CustomPrice(CustomType):
            mongo_type = float
            python_type = basestring
            def to_bson(self, value):
                return float(value)
            def to_python(self, value):
                return str(value)

        class Receipt(Document):
            use_dot_notation = True
            structure = {
                'price': CustomPrice(),
            }
        self.connection.register([Receipt])
          
        r = self.connection.test.test.Receipt()
        r['_id'] = 'bla'
        r['price'] =  '9.99'
        r.save()
        r_saved = r.collection.find_one({'_id':'bla'})
        assert r_saved == {u'_id': u'bla', u'price': 9.9900000000000002}


    def test_instance_type(self):
        from bson.dbref import DBRef
        from bson.objectid import ObjectId
        class Bla(ObjectId):pass
        class Ble(DBRef):pass
        class MyDoc(Document):
            structure = { "foo":ObjectId }
        self.connection.register([MyDoc])
        doc = self.col.MyDoc()
        doc['foo'] = Ble("bla", "ble", "bli")
        self.assertRaises(SchemaTypeError, doc.validate)
        doc['foo'] = Bla()
        doc.validate()

    def test_custom_type_nested(self):
        import datetime
        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = datetime.datetime
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                'foo':{'date': CustomDate()},
            }
            default_values = {'foo.date':datetime.datetime(2008, 6, 7)}
        self.connection.register([Foo])
            
        foo = self.col.Foo()
        foo['_id'] = 1
        foo['foo']['date'] = datetime.datetime(2003,2,1)
        foo.save()
        foo.save()

        foo2 = self.col.Foo()
        foo2['_id'] = 2
        foo2.save()
        assert foo['foo']['date'] == datetime.datetime(2003,2,1), foo['foo']['date']
        foo = self.col.Foo.get_from_id(1)
        assert foo['foo']['date'] == datetime.datetime(2003,2,1)
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo['foo']['date'] == CustomDate().to_bson(datetime.datetime(2003,2,1)), foo['foo']['date']
        foo2 = self.col.Foo.get_from_id(2)
        assert foo2['foo']['date'] == datetime.datetime(2008,6,7), foo2

    def test_custom_type_nested_in_list(self):
        import datetime
        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = datetime.datetime
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                'foo':{'date': [CustomDate()]},
            }
            default_values = {'foo.date':[datetime.datetime(2008, 6, 7)]}
        self.connection.register([Foo])
            
        foo = self.col.Foo()
        foo['_id'] = 1
        foo['foo']['date'].append(datetime.datetime(2003,2,1))
        foo.save()
        foo.save()

        foo1 = self.col.Foo()
        foo1['_id'] = 1
        foo1['foo']['date'].append(1)
        self.assertRaises(SchemaTypeError, foo1.save)

        foo2 = self.col.Foo()
        print foo2
        foo2['_id'] = 2
        foo2.save()
        print id(foo['foo']['date']), id(foo2['foo']['date'])

        assert foo == {'foo': {'date': [datetime.datetime(2008, 6, 7, 0, 0), datetime.datetime(2003, 2, 1, 0, 0)]}, '_id': 1}
        foo = self.col.Foo.get_from_id(1)
        assert foo == {u'_id': 1, u'foo': {u'date': [datetime.datetime(2008, 6, 7, 0, 0), datetime.datetime(2003, 2, 1, 0, 0)]}}
        saved_foo =  foo.collection.find({'_id':1}).next()
        assert saved_foo == {u'_id': 1, u'foo': {u'date': [u'08-06-07', u'03-02-01']}}
        foo2 = self.col.Foo.get_from_id(2)
        assert foo2['foo']['date'] == [datetime.datetime(2008,6,7)], foo2

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

        class CustomDate(CustomType):
            mongo_type = unicode
        self.assertRaises(TypeError, CustomDate)

        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = int
        self.assertRaises(NotImplementedError, CustomDate().to_bson, "bla")
        self.assertRaises(NotImplementedError, CustomDate().to_python, "bla")

    def test_bad_custom_type_bad_python_type(self):
        import datetime

        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = basestring
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                "date": CustomDate(),
            }
            default_values = {'date':datetime.datetime(2008, 6, 7)}
        #self.assertRaises(DefaultFieldTypeError, self.connection.register, [Foo])
        self.connection.register([Foo])
        failed = False
        try:
            self.col.Foo()
        except DefaultFieldTypeError, e:
            failed = True
            self.assertEqual(str(e), 'date must be an instance of basestring not datetime')
 
    def test_custom_type_bad_python(self):
        import datetime

        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = str
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                "date": CustomDate(),
            }
            default_values = {'date':datetime.datetime(2008, 6, 7)}
        self.connection.register([Foo])
        failed = False
        try:
            self.col.Foo()
        except DefaultFieldTypeError, e:
            failed = True
            self.assertEqual(str(e),
              'date must be an instance of str not datetime')

        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = datetime.datetime
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                "date": CustomDate(),
            }
            default_values = {'date':(2008, 6, 7)}
        self.connection.register([Foo])
        failed = False
        try:
            self.col.Foo()
        except DefaultFieldTypeError, e:
            failed = True
            self.assertEqual(str(e),
              'date must be an instance of datetime not tuple')

        class Foo(Document):
            structure = {
                "date": [CustomDate()],
            }
            default_values = {'date':[(2008, 6, 7)]}
        self.connection.register([Foo])
        failed = False
        try:
            self.col.Foo()
        except DefaultFieldTypeError, e:
            failed = True
            self.assertEqual(str(e),
              'date must be an instance of datetime not tuple')

        class CustomDate(CustomType):
            mongo_type = int
            python_type = datetime.datetime
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')

        class Foo(Document):
            structure = {
                "date": CustomDate(),
            }
        self.connection.register([Foo])
        foo = self.col.Foo()
        foo['_id'] = 2
        foo['date'] = datetime.datetime(2003,2,1)
        self.assertRaises(SchemaTypeError, foo.save)

    def test_custom_type_nested_list(self):
        import datetime

        class CustomPrice(CustomType):
            mongo_type = float
            python_type = str
            def to_bson(self, value):
                return float(value)
            def to_python(self, value):
                return str(value)

        class Receipt(Document):
            use_dot_notation = True
            structure = {
                'products': [
                      {
                        'sku': unicode,
                        'qty': int,
                        'price': CustomPrice(),
                      }
                ]
            }
        self.connection.register([Receipt])
          
        r = self.connection.test.test.Receipt()
        r['_id'] = 'bla'
        r.products = []
        r.products.append({ 'sku': u'X-25A5F58B-61', 'qty': 1, 'price': '9.99' })
        r.products.append({ 'sku': u'Z-25A5F58B-62', 'qty': 2, 'price': '2.99' })
        r.save()
        r_saved = r.collection.find_one({'_id':'bla'})
        assert r_saved == {u'_id': u'bla', u'products': [{u'sku': u'X-25A5F58B-61', u'price': 9.9900000000000002, u'qty': 1}, {u'sku': u'Z-25A5F58B-62', u'price': 2.9900000000000002, u'qty': 2}]}

    def test_custom_type_list(self):
        import datetime

        class CustomPrice(CustomType):
            mongo_type = float
            python_type = basestring
            def to_bson(self, value):
                return float(value)
            def to_python(self, value):
                return str(value)

        class Receipt(Document):
            structure = {
                'foo': CustomPrice(),
                'price': [CustomPrice()],
                'bar':{'spam':CustomPrice()},
            }
        self.connection.register([Receipt])
          
        r = self.connection.test.test.Receipt()
        r['_id'] = 'bla'
        r['foo'] = '2.23'
        r['price'].append('9.99')
        r['price'].append('2.99')
        r['bar']['spam'] = '3.33'
        r.save()
        r_saved = r.collection.find_one({'_id':'bla'})
        assert r_saved == {u'price': [9.9900000000000002, 2.9900000000000002], u'_id': u'bla', u'bar': {u'spam': 3.3300000000000001}, u'foo': 2.23}

    def test_custom_type_not_serializable(self):
        from decimal import Decimal
        class DecimalType(CustomType):
           mongo_type = unicode
           python_type = Decimal

           def to_bson(self, value):
               """convert type to a mongodb type"""
               if value is not None:
                   return unicode(value)

           def to_python(self, value):
               """convert type to a python object"""
               if value is not None:
                   return Decimal(value)

        class MyDocument(Document):
           structure = {'amount': DecimalType()}
        self.connection.register([MyDocument])
        document = self.col.MyDocument()
        document['amount'] = Decimal(u'100.00')
        document.validate()

    def test_required_custom_type_mongotype_dict(self):
        class CustomObject(CustomType):
            mongo_type = dict
            python_type = float
            def to_bson(self, value):
                return {'f':unicode(value)}
            def to_python(self, value):
                return float(value['f'])

        class MyDocument(Document):
           structure = {'amount': CustomObject()}
           required_fields = ['amount']
           indexes = [{'fields':['amount.f'], 'check':False}]
           validators = {'amount':lambda x: x > 3.0}

        self.connection.register([MyDocument])

        document = self.col.MyDocument()
        document['_id'] = u'test'
        document['amount'] = 1.00
        self.assertRaises(ValidationError, document.validate)
        document['amount'] = 100.00
        document.save()
        assert self.col.find_one() == {u'amount': {u'f': u'100.0'}, u'_id': u'test'}, self.col.find_one()
        assert self.col.MyDocument.find_one() == {u'amount': 100.00, u'_id': u'test'}, self.col.MyDocument.find_one()
 
    def test_custom_type_mongotype_dict_index_not_checked(self):
        class CustomObject(CustomType):
            mongo_type = dict
            python_type = float
            def to_bson(self, value):
                return {'f':unicode(value)}
            def to_python(self, value):
                return float(value['f'])

        failed = False
        try:
            class MyDocument(Document):
               structure = {'amount': CustomObject()}
               required_fields = ['amount']
               indexes = [{'fields':['amount.f']}]
        except ValueError, e:
            self.assertEqual(str(e), "Error in indexes: can't find amount.f in structure")
            failed = True
        self.assertEqual(failed, True)

    def test_missing_custom_types(self):
        import datetime
        class CustomDate(CustomType):
            mongo_type = unicode
            python_type = datetime.datetime
            def to_bson(self, value):
                """convert type to a mongodb type"""
                return unicode(datetime.datetime.strftime(value,'%y-%m-%d'))
            def to_python(self, value):
                """convert type to a python object"""
                if value is not None:
                    return datetime.datetime.strptime(value, '%y-%m-%d')
                
        class Foo(Document):
            structure = {
                "date": CustomDate(),
            }
            default_values = {'date':datetime.datetime(2008, 6, 7)}
        self.connection.register([Foo])
            
        # insert a foo document without this field
        self.col.insert({'_id': 1})

        foo = self.col.Foo.get_from_id(1)
        foo['_id'] = 1
        foo['date'] = datetime.datetime(2003,2,1)
        foo.save()
