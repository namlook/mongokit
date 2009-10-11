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
from pymongo.objectid import ObjectId

CONNECTION = Connection()

class VersionedTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = CONNECTION['test']['mongokit']
        
    def tearDown(self):
        CONNECTION['test'].drop_collection('mongokit')
        CONNECTION['test'].drop_collection('versioned_mongokit')

    def test_save_versionning(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla" : unicode,
            }

        doc = MyDoc()
        doc['bla'] =  u"bli"
        doc.save()
        assert "_version" not in doc

        class MyVersionedDoc(VersionedDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo" : unicode,
            }
            versioning = "versioned_mongokit"
 
        versioned_doc = MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()
        assert versioned_doc['_revision'] == 1
        assert versioned_doc.get_last_revision_id() == 1
        assert versioned_doc.get_revision(1) == {'foo':'bla', "_revision":1, "_id":"mydoc"}
        versioned_doc['foo'] = u'bar'
        versioned_doc.save()
        assert versioned_doc['_revision'] == 2
        assert versioned_doc.get_last_revision_id() == 2
        assert versioned_doc['foo'] == 'bar'
        assert versioned_doc.get_revision(2) == {'foo':'bar', "_revision":2, "_id":"mydoc"}, versioned_doc.get_revision(2)
        old_doc =  versioned_doc.get_revision(1)
        old_doc.save()
        assert old_doc['_revision'] == 3

        versioned_doc = MyVersionedDoc.get_from_id(versioned_doc['_id'])
        assert len(list(versioned_doc.get_revisions())) == 3, len(list(versioned_doc.get_revisions()))

    def test_bad_versioning(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
            versioning = True
 
        self.assertRaises(ValidationError, MyVersionedDoc)

    def test_delete_versioning(self):
        class MyVersionedDoc(VersionedDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo" : unicode,
            }
            versioning_collection_name = "versioned_mongokit"
 
        versioned_doc = MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()
        assert MyVersionedDoc.get_versioning_collection().find().count() == 1
        versioned_doc['foo'] = u'bar'
        versioned_doc.save()
        assert MyVersionedDoc.get_versioning_collection().find().count() == 2
        versioned_doc.delete(versioning=True)
        assert MyVersionedDoc.get_versioning_collection().find().count() == 0
        assert MyVersionedDoc.all().count() == 0

        versioned_doc = MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()
        assert MyVersionedDoc.get_versioning_collection().find().count() == 1
        versioned_doc['foo'] = u'bar'
        versioned_doc.save()
        assert MyVersionedDoc.get_versioning_collection().find().count() == 2
        versioned_doc.delete()
        assert MyVersionedDoc.get_versioning_collection().find().count() == 2
        assert MyVersionedDoc.all().count() == 0


