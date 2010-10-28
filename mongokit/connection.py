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

from pymongo import Connection as PymongoConnection
from database import Database

class CursorMixin(object):
    """
    brings the callable method to a Document. usefull for the connection's
    register method
    """
    def __call__(self, doc=None, gen_skel=False, lang='en', fallback_lang='en'):
        return self._obj_class(doc=doc, gen_skel=gen_skel, collection=self.collection, lang=lang, fallback_lang=fallback_lang)

class CallableMixin(object):
    """
    brings the callable method to a Document. usefull for the connection's
    register method
    """
    def __call__(self, doc=None, gen_skel=True, lang='en', fallback_lang='en'):
        return self._obj_class(doc=doc, gen_skel=gen_skel, collection=self.collection, lang=lang, fallback_lang=fallback_lang)


class Connection(PymongoConnection):

    def __init__(self, *args, **kwargs):
        self._databases = {} 
        self._registered_documents = {}
        super(Connection, self).__init__(*args, **kwargs)
    
    def register(self, obj_list):
        # cleanup
        for dbname, db in self._databases.items():
            for colname, col in db._collections.items():
                for docname, doc in col._documents.items():
                    del col._documents[docname]
                for obj_name in [obj.__name__ for obj in obj_list]:
                    if obj_name in col._registered_documents:
                        del col._registered_documents[obj_name]
        # register
        for obj in obj_list:
            CursorDocument = type("Cursor%s" % obj.__name__, (obj, CursorMixin), {"_obj_class":obj, "__repr__":object.__repr__})
            CallableDocument = type(
              "Callable%s" % obj.__name__,
              (obj, CallableMixin), {'cursor': CursorDocument(), "_obj_class":obj, "__repr__":object.__repr__})
            self._registered_documents[obj.__name__] = CallableDocument

    def __getattr__(self, key):
        if key not in self._databases:
            self._databases[key] = Database(self, key)
        return self._databases[key]


