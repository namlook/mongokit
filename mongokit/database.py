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

from pymongo.database import Database as PymongoDatabase
from pymongo.dbref import DBRef
from mongokit.document import Document
from collection import Collection

class Database(PymongoDatabase):

    def __init__(self, *args, **kwargs):
        self._collections = {}
        super(Database, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        if not key in self._collections:
            self._collections[key] = Collection(self, key) 
        return self._collections[key]


    def dereference(self, dbref, model = None):
        if model is None:
          return super(Database, self).dereference(dbref)

        if not isinstance(dbref, DBRef):
            raise TypeError("first argument must be a DBRef")

        if dbref.database is not None and dbref.database != self.name:
            raise ValueError("dereference must be called on the database `%s`" % dbref.database)

        if not issubclass(model, Document):
            raise TypeError("second argument must be a Document")

        return self[dbref.collection][model.__name__].one({'_id': dbref.id})

