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

class VersionedTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection['test'].drop_collection('mongokit')
        self.connection['test'].drop_collection('versioned_mongokit')
        self.connection['test'].drop_collection('versioned_mongokit2')
        self.connection['versioned_test'].drop_collection('versioned_mongokit')

    def test_save_versioning(self):
        class MyDoc(Document):
            structure = {
                "bla" : unicode,
            }
        self.connection.register([MyDoc])

        doc = self.col.MyDoc()
        doc['bla'] =  u"bli"
        doc.save()
        assert "_revision" not in doc
        doc.delete()

        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
        self.connection.register([MyVersionedDoc])
 
        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()

        docs = list(self.col.find())
        assert len(docs) == 1

        ver_doc = list(self.connection.test.versioned_mongokit.find())
        assert len(ver_doc) == 1
        assert ver_doc[0]['id'] == 'mydoc'
        assert ver_doc[0]['revision'] == 1
        assert ver_doc[0]['doc'] == {u'_revision': 1, u'foo': u'bla', u'_id': u'mydoc'}

        assert versioned_doc['_revision'] == 1
        assert versioned_doc.get_last_revision_id() == 1
        assert versioned_doc.get_revision(1) == {'foo':'bla', "_revision":1, "_id":"mydoc"}
        versioned_doc['foo'] = u'bar'
        versioned_doc.save()

        ver_doc = list(self.connection.test.versioned_mongokit.find())
        assert len(ver_doc) == 2
        assert ver_doc[0]['id'] == 'mydoc'
        assert ver_doc[0]['revision'] == 1
        assert ver_doc[0]['doc'] == {u'_revision': 1, u'foo': u'bla', u'_id': u'mydoc'}
        assert ver_doc[1]['id'] == 'mydoc'
        assert ver_doc[1]['revision'] == 2
        assert ver_doc[1]['doc'] == {u'_revision': 2, u'foo': u'bar', u'_id': u'mydoc'}

        assert versioned_doc['_revision'] == 2
        assert versioned_doc.get_last_revision_id() == 2
        assert versioned_doc['foo'] == 'bar'
        assert versioned_doc.get_revision(2) == {'foo':'bar', "_revision":2, "_id":"mydoc"}, versioned_doc.get_revision(2)
        old_doc = versioned_doc.get_revision(1)
        print old_doc, type(old_doc)
        old_doc.save()
        assert old_doc['_revision'] == 3

        versioned_doc = self.connection.test.mongokit.MyVersionedDoc.get_from_id(versioned_doc['_id'])
        assert len(list(versioned_doc.get_revisions())) == 3, len(list(versioned_doc.get_revisions()))

    def test_save_without_versionning(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
        self.connection.register([MyVersionedDoc])
 
        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save(versioning=False)
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 0
        assert self.col.find().count() == 1


    def test_save_versioning_without_id(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
        self.connection.register([MyVersionedDoc])
 
        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()

        ver_doc = list(self.connection.test.versioned_mongokit.find())
        assert len(ver_doc) == 1
        assert 'doc' in ver_doc[0]
        assert 'revision' in ver_doc[0], ver_doc[0]

        ver_doc = list(self.col.find())
        assert len(ver_doc) == 1
        assert 'doc' not in ver_doc[0]
        assert '_revision' in ver_doc[0]

    def _test_bad_versioning(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
 
        self.connection.register([MyVersionedDoc])
        self.assertRaises(ValidationError, MyVersionedDoc)

    def test_delete_versioning(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
        self.connection.register([MyVersionedDoc])
 
        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 1
        versioned_doc['foo'] = u'bar'
        versioned_doc.save()
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 2
        versioned_doc.delete(versioning=True)
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 0
        assert self.col.MyVersionedDoc.find().count() == 0

        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 1
        versioned_doc['foo'] = u'bar'
        versioned_doc.save()
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 2
        versioned_doc.delete()
        assert self.col.MyVersionedDoc.versioning_collection.find().count() == 2
        assert self.col.MyVersionedDoc.find().count() == 0

    def test_remove_versioning(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
        self.connection.register([MyVersionedDoc])
 
        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()
        versioned_doc2 = self.col.MyVersionedDoc()
        versioned_doc2['_id'] = "mydoc2"
        versioned_doc2['foo'] = u'bla'
        versioned_doc2.save()
        versioned_doc3 = self.col.MyVersionedDoc()
        versioned_doc3['_id'] = "mydoc3"
        versioned_doc3['foo'] = u'bla'
        versioned_doc3.save()

        versioned_doc['foo'] = u'bar'
        versioned_doc.save()
        versioned_doc2['foo'] = u'bar'
        versioned_doc2.save()
        versioned_doc3['foo'] = u'bar'
        versioned_doc3.save()

        count =  self.col.MyVersionedDoc.versioning_collection.find().count()
        assert count == 6, count
        count =  self.col.MyVersionedDoc.collection.find().count()
        assert count == 3, count

        versioned_doc.remove({'foo':'bar'}, versioning=True)

        count =  self.col.MyVersionedDoc.versioning_collection.find().count()
        assert count == 0, count
        count =  self.col.MyVersionedDoc.collection.find().count()
        assert count == 0, count

    def _test_versioning_with_dynamic_db(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
        self.connection.register([MyVersionedDoc])
 
        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()

        ver_doc = list(self.connection.test.versioned_mongokit.find())
        assert len(ver_doc) == 1
        assert ver_doc[0]['id'] == 'mydoc'
        assert ver_doc[0]['revision'] == 1
        assert ver_doc[0]['doc'] == {u'_revision': 1, u'foo': u'bla', u'_id': u'mydoc'}

        ver_mongokit2 = list(CONNECTION['versioned_test']['versioned_mongokit'].find())
        assert len(ver_mongokit2) == 0, len(ver_mongokit2)

        versioned_doc2 = MyVersionedDoc(versioning_db_name="versioned_test")
        versioned_doc2['_id'] = "mydoc2"
        versioned_doc2['foo'] = u'bla'
        versioned_doc2.save()

        ver_mongokit = list(CONNECTION['test']['versioned_mongokit'].find())
        assert len(ver_mongokit) == 1, len(ver_mongokit)

        ver_doc = list(CONNECTION['versioned_test']['versioned_mongokit'].find())
        assert len(ver_doc) == 1
        assert ver_doc[0]['id'] == 'mydoc2'
        assert ver_doc[0]['revision'] == 1
        assert ver_doc[0]['doc'] == {u'_revision': 1, u'foo': u'bla', u'_id': u'mydoc2'}

        versioned_doc['foo'] = u'bar'
        versioned_doc.save()

        ver_doc = list(CONNECTION['test']['versioned_mongokit'].find())
        assert len(ver_doc) == 2
        ver_doc = list(CONNECTION['versioned_test']['versioned_mongokit'].find())
        assert len(ver_doc) == 1

    def _test_versioning_with_dynamic_collection(self):
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
            }
            versioning_collection_name = "versioned_mongokit"
 
        versioned_doc = MyVersionedDoc()
        versioned_doc['_id'] = "mydoc"
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()

        ver_doc = list(CONNECTION['test']['versioned_mongokit'].find())
        assert len(ver_doc) == 1
        assert ver_doc[0]['id'] == 'mydoc'
        assert ver_doc[0]['revision'] == 1
        assert ver_doc[0]['doc'] == {u'_revision': 1, u'foo': u'bla', u'_id': u'mydoc'}

        ver_mongokit2 = list(CONNECTION['test']['versioned_mongokit2'].find())
        assert len(ver_mongokit2) == 0

        versioned_doc2 = MyVersionedDoc(versioning_collection_name="versioned_mongokit2")
        versioned_doc2['_id'] = "mydoc2"
        versioned_doc2['foo'] = u'bla'
        versioned_doc2.save()

        ver_mongokit = list(CONNECTION['test']['versioned_mongokit'].find())
        assert len(ver_mongokit) == 1, len(ver_mongokit)

        ver_doc = list(CONNECTION['test']['versioned_mongokit2'].find())
        assert len(ver_doc) == 1
        assert ver_doc[0]['id'] == 'mydoc2'
        assert ver_doc[0]['revision'] == 1
        assert ver_doc[0]['doc'] == {u'_revision': 1, u'foo': u'bla', u'_id': u'mydoc2'}

        versioned_doc['foo'] = u'bar'
        versioned_doc.save()

        ver_doc = list(CONNECTION['test']['versioned_mongokit'].find())
        assert len(ver_doc) == 2
        ver_doc = list(CONNECTION['test']['versioned_mongokit2'].find())
        assert len(ver_doc) == 1

    def test_versioning_without_versioning_collection_name(self):
        test_passed = False
        try:
            class Group(VersionedDocument):
                use_autorefs = True
                structure = {
                       'name':unicode,
                       'members':[User], #users
                   }
        except:
            test_passed = True
        assert test_passed

    def test_resave_versioned_doc_with_objectId(self):
        """
        1. Create a simple VersionedDocument using the defaults, thus using the
        built-in objectID.
        2. save to the database
        3. change the VersionedDocument contents (leave _id unchanged)
        4. resave to the database
            4a. the save action will search for the get_last_revision_id
            4b. add +1 to the _revision attribute
            4c. save the revised document, save the old document in the
                versioned_* collection

        4a BREAKS!

            self['_revision'] = self.get_last_revision_id()
        File "...\mongokit\versioned_document.py", line 100, in get_last_revision_id
            {'id':self['_id']}).sort('revision', -1).next()
        File "...\mongokit\cursor.py", line 44, in next
            raise StopIteration
        """
        class MyVersionedDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
                }

        self.connection.register([MyVersionedDoc])

        versioned_doc = self.col.MyVersionedDoc()
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()

        docs = list(self.col.find())
        assert len(docs) == 1

        versioned_doc['foo'] = u'Some Other bla'
        versioned_doc.save()

        print(versioned_doc)

    def test_resave_versioned_doc_with_UUID(self):
        """
        Simple versioning test, a bit different than the test_save_versionning

        """
        class MyVersionedUUIDDoc(VersionedDocument):
            structure = {
                "foo" : unicode,
                }
            def save(self, versioning=True, uuid=True, *args, **kwargs):
                """ Ensure that the save is performed using uuid=True """
                return super(MyVersionedUUIDDoc, self).save(versioning, uuid, *args, **kwargs)

        self.connection.register([MyVersionedUUIDDoc])

        versioned_doc = self.col.MyVersionedUUIDDoc()
        versioned_doc['foo'] = u'bla'
        versioned_doc.save()

        docs = list(self.col.find())
        assert len(docs) == 1

        versioned_doc['foo'] = u'Some Other bla'
        versioned_doc.save()

        # search for the versioned_doc in the database and compare id's
        ver_doc = list(self.connection.test.mongokit.find())
        assert len(ver_doc) == 1
        assert ver_doc[0]['_revision'] == 2
        assert ver_doc[0]['foo'] == u'Some Other bla'
        assert ver_doc[0]['_id'][:18] == u'MyVersionedUUIDDoc'
        assert ver_doc[0]['_id'] == versioned_doc['_id']
