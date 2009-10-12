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

class RevisionDocument(MongoDocument):
    structure = {
        "id": unicode,
        "revision":int,
        "doc":dict
    }

class VersionedDocument(MongoDocument):
    """
    This object implement a vesionnized mongo document
    """

    versioning_db_name = None
    versioning_collection_name = None

    _versioning_collection = None

    def __init__(self, *args, **kwargs):
        super(VersionedDocument, self).__init__(*args, **kwargs)
        if not ( self.versioning_db_name or self.db_name):
            raise ValidationError( 
              "you must specify versioning_db_name or db_name" )
        if not (self.versioning_collection_name or self.collection_name):
            raise ValidationError( 
              "you must specify versioning_collection_name or collection_name" )
        if type(self.versioning_db_name) not in [type(None), str, unicode]:
            raise ValidationError(
              "versioning_db attribute must be None or basestring")
        if type(self.versioning_collection_name) not in\
          [type(None), str, unicode]:
            raise ValidationError(
              "versioning_collection attribute must be None or basestring")

    def save(self, versioning=True, *args, **kwargs):
        if versioning:
            if '_revision' in self:
                self.pop('_revision')
                self['_revision'] = self.get_last_revision_id()
            else:
                self['_revision'] = 0
            self['_revision'] += 1
            _col = self.get_versioning_collection()
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
            self.get_versioning_collection().remove({'id':self['_id']})
        super(VersionedDocument, self).delete(*args, **kwargs)
        
    @classmethod
    def get_versioning_collection(cls):
        if not cls._versioning_collection:
            if cls._use_pylons:
                from mongokit.ext.pylons_env import MongoPylonsEnv
                db_name = MongoPylonsEnv.get_default_db()
            else:
                db_name = cls.db_name
            db_name = cls.versioning_db_name or db_name
            collection_name = cls.versioning_collection_name or\
              cls.collection_name
            if not db_name and not collection_name:
                raise ConnectionError( 
                  "You must set a db_name and a versioning collection name"
                )
            db = cls.connection[db_name]
            cls._versioning_collection = db[collection_name]
            if db.collection_names():
                if not collection_name in db.collection_names():
                    cls._versioning_collection.create_index(
                      [('id', 1), ('revision', 1)], unique=True)
        return cls._versioning_collection

    def _get_versioning_collection(self):
        return self.__class__.get_versioning_collection()
    versioning_collection = property(_get_versioning_collection)

    def get_revision(self, revision_number):
        _col = self.get_versioning_collection()
        doc = RevisionDocument.one(
          {"id":self['_id'], 'revision':revision_number}, collection=_col)
        if doc:
            return self.__class__(doc['doc'])

    def get_revisions(self):
        versionned_docs = self.versioning_collection.find({"id":self['_id']})
        for verdoc in versionned_docs:
            yield self.__class__(verdoc['doc'])

    def get_last_revision_id(self):
        last_doc = self.get_versioning_collection().find(
          {'id':self['_id']}).sort('revision', -1).next()
        if last_doc:
            return last_doc['revision']


