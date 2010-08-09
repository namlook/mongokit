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

from mongokit import *
import datetime


class AtomicTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')
        self.connection.drop_database('othertest')

    def test_atomic(self):
        class MyDoc(Document):
            structure = {
                'foo':{
                    'bar':[unicode],
                    'eggs':{'spam':int},
                },
                'bla':unicode
            }
            atomic_save = True
        self.connection.register([MyDoc])

        doc = self.col.MyDoc()
        doc['_id'] = 3
        doc['foo']['bar'] = [u'mybar', u'yourbar']
        doc['foo']['eggs']['spam'] = 4
        doc['bla'] = u'ble'
        doc.save() # version 1
        assert doc['_version'] == 1

        doc['foo']['eggs']['spam'] = 2
        doc['bla']= u'bli'

        new_doc = self.col.MyDoc.get_from_id(doc['_id'])
        new_doc['bla'] = u'blo'
        new_doc.save() # version 2
        new_doc.save() # version 2
        assert new_doc['_version'] == 2, new_doc['_version']

        try:
            doc.save() # version 1 -> failed : current version is 2
        except ConflictError,e:
            doc.reload() # version 2
            doc['foo']['eggs']['spam'] = 2
            doc['bla']= u'bli'
            doc.save() # version 3
            assert doc['_version'] == 3

        new_doc = self.col.MyDoc.get_from_id(doc['_id'])
        assert new_doc == {'foo': {'eggs': {'spam': 2}, 'bar': [u'mybar', u'yourbar']}, 'bla': u'bli', '_version': 3, '_id': 3}, new_doc

    def test_atomic_smooth_migration(self):
        class MyDoc(Document):
            structure = {
                'foo':{
                    'bar':unicode,
                    'eggs':{'spam':int},
                },
                'bla':unicode
            }
        self.connection.register([MyDoc])

        doc = self.col.MyDoc()
        doc['_id'] = 3
        doc['foo']['bar'] = u'mybar'
        doc['foo']['eggs']['spam'] = 4
        doc['bla'] = u'ble'
        doc.save() # version 1

        doc['foo']['eggs']['spam'] = 2
        doc['bla']= u'bli'

        MyDoc.atomic_save = True
        self.connection.register([MyDoc])

        new_doc = self.col.MyDoc.get_from_id(doc['_id'])
        new_doc['bla'] = u'blo'
        new_doc.save() # version 2
        print new_doc
        assert new_doc['_version'] == 1

        try:
            doc.save() # version 1 -> failed : current version is 2
        except ConflictError,e:
            doc.reload() # version 2
            doc['foo']['eggs']['spam'] = 2
            doc['bla']= u'bli'
            doc.save() # version 3
            assert doc['_version'] == 2


        new_doc = self.col.MyDoc.get_from_id(doc['_id'])
        assert new_doc == {'foo': {'eggs': {'spam': 2}, 'bar': u'mybar'}, 'bla': u'bli', '_version': 2, '_id': 3}, new_doc

    def test_atomic_save_with_unicode_type_as_key(self):
        class MyDoc(Document):
           structure = {
               'foo':unicode,
               'bar': {
                   unicode: {
                       'name': unicode,
                       'spam': bool,
                   },
               },
           }
           atomic_save = True

        self.connection.register([MyDoc])
        doc = self.col.MyDoc()
        doc['foo'] = u'Billy'
        doc.save()

        doc = self.col.MyDoc.get_from_id(doc['_id'])
        doc['bar'][u'dob'] = {
           'name': u'Date of Birth',
           'spam': True,
        }
        doc.save()

    def test_atomic_save_with_autorefs(self):
        class DocA(Document):
            structure = {
                'name':unicode
            }

        class MyDoc(Document):
            structure = {
               'foo':unicode,
               'bar': DocA,
            }
            atomic_save = True
            use_autorefs = True

        self.connection.register([DocA, MyDoc])
        doca = self.col.DocA()
        doca['name'] = u'hello'
        doca.save()

        mydoc = self.col.MyDoc()
        mydoc['foo'] = u'bla'
        mydoc['bar'] = doca
        mydoc.save()

        mydoc = self.col.MyDoc.get_from_id(mydoc['_id'])
        mydoc['foo'] = u'blo'
        mydoc['bar']['name'] = u'arf'
        mydoc.save()

        doca.reload()
        assert doca['name'] == u'arf'

        assert self.col.get_from_id(doca['_id']) == {'_id':doca['_id'], "name":"arf"}, self.col.get_from_id(doca['_id'])


    def test_atomic_save_with_dot_notation(self):
        class VDocument(Document):
           db_name = 'MyDB'
           use_dot_notation = True
           use_autorefs = True
           skip_validation = True
           atomic_save = True

           def __init__(self, *args, **kwargs):
               super(VDocument, self).__init__(*args, **kwargs)

           def save(self, *args, **kwargs):
               kwargs.update({'validate':True})
               return super(VDocument, self).save(*args, **kwargs)

        class MyDoc(VDocument):
            structure = {
                'details': unicode,
                'end_date': datetime.datetime,
                'is_active': bool,
                'is_removed': bool,
                'owner': ObjectId,
                'questions': [{
                    'content': unicode,
                    'is_active': bool,
                    'qid': int,
                    'type': IS(u'text', u'code', u'file'),
                }],
                'tags': [ObjectId],
                'title': unicode,
                'xa_index': {'indexed': bool, 'needs_update': bool},
            }
        self.connection.register([MyDoc])

        x = {u'_id': ObjectId('4c485c9e1d7c293f99000001'),
         u'_version': 11,
         u'details': u'detail var burada lorem morem ',
         u'end_date': datetime.datetime(2000, 1, 1, 0, 0),
         u'is_active': False,
         u'is_removed': False,
         u'owner': ObjectId('4c483bd41d7c291b55000000'),
         u'questions': [{'content':u'deneme', 'is_active':False, 'qid':1, 'type':u'text'}],
         u'tags': [ObjectId('4c541dde1d7c293345000000'),
                  ObjectId('4c485c9e1d7c293f99000000')],
         u'title': u'bebey',
         u'xa_index': {u'indexed': True, u'needs_update': True}}
        self.col.insert(x)

        mydoc = self.col.MyDoc.get_from_id(ObjectId('4c485c9e1d7c293f99000001'))
        mydoc.xa_index['needs_update'] = False
        mydoc.save()
        assert mydoc.xa_index['needs_update'] is False
        assert self.col.MyDoc.get_from_id(ObjectId('4c485c9e1d7c293f99000001')).xa_index['needs_update'] is False
        assert mydoc.xa_index.needs_update is False
        mydoc.reload()
        assert mydoc.xa_index['needs_update'] is False
        assert mydoc.xa_index.needs_update is False
        mydoc.xa_index['needs_update'] = True
        mydoc.save()
        assert mydoc.xa_index['needs_update'] is True
        assert self.col.MyDoc.get_from_id(ObjectId('4c485c9e1d7c293f99000001')).xa_index['needs_update'] is True
        assert mydoc.xa_index.needs_update is True
        mydoc.xa_index.needs_update = False
        mydoc.save()
        assert mydoc.xa_index['needs_update'] is False
        assert self.col.MyDoc.get_from_id(ObjectId('4c485c9e1d7c293f99000001')).xa_index['needs_update'] is False
        assert mydoc.xa_index.needs_update is False

        assert mydoc.questions[0]['content']  == u'deneme'
