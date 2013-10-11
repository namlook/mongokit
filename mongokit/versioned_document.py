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

from mongokit import *
from mongo_exceptions import *


class RevisionDocument(Document):
    structure = {
        "id": unicode,
        "revision": int,
        "doc": dict
    }


class VersionedDocument(Document):
    """
    This object implement a vesionnized mongo document
    """

    def __init__(self, doc=None, *args, **kwargs):
        super(VersionedDocument, self).__init__(doc=doc, *args, **kwargs)
        if kwargs.get('collection', None):
            self.versioning_collection = self.db["versioned_%s" % self.collection.name]
            self.versioning_collection.ensure_index([('id', 1), ('revision', 1)], unique=True)
            self.versioning_collection.database.connection.register([self.__class__, RevisionDocument])

    def save(self, versioning=True, *args, **kwargs):
        if versioning:
            if '_revision' in self:
                self.pop('_revision')
                self['_revision'] = self.get_last_revision_id()
            else:
                self['_revision'] = 0
            self['_revision'] += 1
            super(VersionedDocument, self).save(*args, **kwargs)
            versionned_doc = RevisionDocument({"id": unicode(self['_id']), "revision": self['_revision']},
                                              collection=self.versioning_collection)
            versionned_doc['doc'] = dict(self)
            versionned_doc.save()
        else:
            super(VersionedDocument, self).save(*args, **kwargs)
        return self

    def delete(self, versioning=False, *args, **kwargs):
        """
        if versioning is True delete revisions documents as well
        """
        if versioning:
            self.versioning_collection.remove({'id': self['_id']})
        super(VersionedDocument, self).delete(*args, **kwargs)

    def remove(self, query, versioning=False, *args, **kwargs):
        """
        if versioning is True, remove all revisions documents as well.
        Be careful when using this method. If your query match tons of
        documents, this might be very very slow.
        """
        if versioning:
            id_lists = [i['_id'] for i in self.collection.find(query, fields=['_id'])]
            self.versioning_collection.remove({'id': {'$in': id_lists}})
        self.collection.remove(spec_or_id=query, *args, **kwargs)

    def get_revision(self, revision_number):
        doc = self.versioning_collection.RevisionDocument.find_one(
            {"id": self['_id'], 'revision': revision_number})
        if doc:
            return self.__class__(doc['doc'], collection=self.collection)

    def get_revisions(self):
        versionned_docs = self.versioning_collection.find({"id": self['_id']})
        for verdoc in versionned_docs:
            yield self.__class__(verdoc['doc'], collection=self.collection)

    def get_last_revision_id(self):
        last_doc = self.versioning_collection.find({'id': unicode(self['_id'])}).sort('revision', -1).next()
        if last_doc:
            return last_doc['revision']
