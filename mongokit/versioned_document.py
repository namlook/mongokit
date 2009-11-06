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

from mongokit import *
from mongokit.mongo_document import MongoProperties

class RevisionDocument(MongoDocument):
    structure = {
        "id": unicode,
        "revision":int,
        "doc":dict
    }

class VersionedMongoProperties(MongoProperties):
    def __new__(cls, name, bases, attrs):
        obj = super(VersionedMongoProperties, cls).__new__(cls, name, bases, attrs)
        if obj.collection_name:
            if obj.versioning_db_name:
                obj.versioning_db = Connection(obj.db_host, obj.db_port)[obj.versioning_db_name]
                attrs['versioning_db_name'] = obj.versioning_db_name
            else:
                obj.versioning_db = Connection(obj.db_host, obj.db_port)[obj.db_name]
                attrs['versioning_db_name'] = obj.db_name
            if obj.versioning_collection_name:
                obj.versioning_collection = obj.versioning_db[obj.versioning_collection_name]
                attrs['versioning_collection_name'] = obj.versioning_collection_name
            else:
                obj.versioning_collection = obj.versioning_db[obj.collection_name]
                attrs['versioning_collection_name'] = obj.collection_name
            attrs['versioning_db'] = obj.versioning_db
            attrs['versioning_collection'] = obj.versioning_collection
            # creating index
            if not obj.versioning_collection_name in obj.versioning_db.collection_names():
                obj.versioning_collection.ensure_index(
                  [('id', 1), ('revision', 1)], unique=True)
        return type.__new__(cls, name, bases, attrs)        

class VersionedDocument(MongoDocument):
    """
    This object implement a vesionnized mongo document
    """
    __metaclass__ = VersionedMongoProperties

    versioning_db_name = None
    versioning_collection_name = None

    def __init__(self, doc=None, versioning_db_name=None, versioning_collection_name=None, *args, **kwargs):
        super(VersionedDocument, self).__init__(doc=doc, *args, **kwargs)
        reset_versioning_connection = False
        if versioning_db_name is not None:
            self.versioning_db_name = versioning_db_name
            reset_versioning_connection = True
        if versioning_collection_name is not None:
            self.versioning_collection_name = versioning_collection_name
            reset_versioning_connection = True
        # check if versioning_db_name exists
        if not ( self.versioning_db_name or self.db_name):
            raise ValidationError( 
              "you must specify versioning_db_name or db_name" )
        # check if versioning_collection_name exists
        if not (self.versioning_collection_name or self.collection_name or versioning_collection_name):
            raise ValidationError( 
              "you must specify versioning_collection_name or collection_name" )
        # check if versioning_db_name and versioning_collection_name are well typed
        if type(self.versioning_db_name) not in [type(None), str, unicode]:
            raise ValidationError(
              "versioning_db attribute must be None or basestring")
        if type(self.versioning_collection_name) not in\
          [type(None), str, unicode]:
            raise ValidationError(
              "versioning_collection attribute must be None or basestring")
        # overload versioning db and collection if needed
        if reset_versioning_connection:
            connection = Connection(self.db_host, self.db_port)
            self.versioning_db = connection[self.versioning_db_name]
            self.versioning_collection = self.versioning_db[self.versioning_collection_name]
            if not self.versioning_collection_name in self.versioning_db.collection_names():
                self.versioning_collection.ensure_index(
                  [('id', 1), ('revision', 1)], unique=True)

    def save(self, versioning=True, *args, **kwargs):
        if versioning:
            if '_revision' in self:
                self.pop('_revision')
                self['_revision'] = self.get_last_revision_id()
            else:
                self['_revision'] = 0
            self['_revision'] += 1
            _col = self.versioning_collection
            collection_name = _col.name()
            db_name = _col.database().name()
            versionned_doc = RevisionDocument(
              {"id":unicode(self['_id']), "revision":self['_revision']},
              db_name = db_name, collection_name = collection_name)
            versionned_doc['doc'] = dict(self)
            versionned_doc.save()
        return super(VersionedDocument, self).save(*args, **kwargs)

    def delete(self, versioning=False, *args, **kwargs):
        """
        if versioning is True delete revisions documents as well
        """
        if versioning:
            self.versioning_collection.remove({'id':self['_id']})
        super(VersionedDocument, self).delete(*args, **kwargs)

    @classmethod
    def remove(cls, query, versioning=False, *args, **kwargs):
        """
        if versioning is True, remove all revisions documents as well.
        Be carefull when using this method. If your query match tons of
        documents, this might be very very slow.
        """
        if versioning:
            collection = kwargs.get('collection', cls.collection)
            id_lists = [i['_id'] for i in  collection.find(query, fields=['_id'])]
            versioning_collection = kwargs.pop('versioning_collection', cls.versioning_collection)
            versioning_collection.remove({'id':{'$in':id_lists}})
        super(VersionedDocument, cls).remove(spec_or_object_id=query, *args, **kwargs)
                
    def get_revision(self, revision_number):
        doc = RevisionDocument.one(
          {"id":self['_id'], 'revision':revision_number},
          collection=self.versioning_collection)
        if doc:
            return self.__class__(doc['doc'])

    def get_revisions(self):
        versionned_docs = self.versioning_collection.find({"id":self['_id']})
        for verdoc in versionned_docs:
            yield self.__class__(verdoc['doc'])

    def get_last_revision_id(self):
        last_doc = self.versioning_collection.find(
          {'id':self['_id']}).sort('revision', -1).next()
        if last_doc:
            return last_doc['revision']


