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

from mongokit.helpers import DotCollapsedDict
from mongokit.mongo_exceptions import *


class DocumentMigration(object):

    def __init__(self, doc_class):
        self.doc_class = doc_class
        self.target = None
        self.update = None
        self.doc = None
        self.collection = None

    def clean(self):
        self.target = None
        self.update = None
        self.doc = None
        self.collection = None
        self.status = False

    def validate_update(self, update_query):
        structure = DotCollapsedDict(self.doc_class.structure)
        for op, fields in update_query.iteritems():
            for field in fields:
                if op != '$unset' and op != '$rename':
                    if field not in structure:
                        raise UpdateQueryError("'%s' not found in %s's structure" % (
                            field, self.doc_class.__name__))

    def migrate(self, doc, safe=True):
        """migrate the doc through all migration process"""
        method_names = sorted([i for i in dir(self) if i.startswith('migration')])
        for method_name in method_names:
            self.clean()
            self.doc = doc
            getattr(self, method_name)()
            if self.target and self.update:
                if '_id' in doc:
                    self.target['_id'] = doc['_id']
                doc.collection.update(self.target, self.update, multi=False, safe=safe)
                # reload
                try:
                    doc.update(doc.collection.get_from_id(doc['_id']))
                except:
                    raise OperationFailure('Can not reload an unsaved document. '
                                           '%s is not found in the database' % doc['_id'])
                # self.reload()

    def migrate_all(self, collection, safe=True):
        method_names = sorted([i for i in dir(self) if i.startswith('allmigration')])
        for method_name in method_names:
            self.clean()
            self.collection = collection
            getattr(self, method_name)()
            if self.target and self.update:
                self.validate_update(self.update)
                collection.update(self.target, self.update, multi=True, safe=safe)
                status = collection.database.last_status()
                if not status.get('updatedExisting', 1):
                    print "%s : %s >>> deprecated" % (self.__class__.__name__, method_name)

    def get_deprecated(self, collection):
        method_names = sorted([i for i in dir(self) if i.startswith('migration') or i.startswith('allmigration')])
        deprecated = []
        active = []
        for method_name in method_names:
            self.clean()
            self.status = True
            getattr(self, method_name)()
            if not collection.find(self.target).count():
                deprecated.append(method_name)
            else:
                active.append(method_name)
        return {'deprecated': deprecated, 'active': active}
