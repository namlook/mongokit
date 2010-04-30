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
from pymongo.objectid import ObjectId


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



