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

from gridfs import GridFS
from gridfs.grid_file import GridFile

class FSContainer(object):
    def __init__(self, container_name, obj):
        self._container_name = container_name
        self._obj = obj
        self._fs = GridFS(self._obj.db)

    def __getitem__(self, key):
        try:
            f = GridFile({'metadata':{'name':key, 'container':self._container_name, 'doc_id':self._obj['_id']}}, self._obj.db, 'r', self._obj.collection.name)
            content = f.read()
            f.close()
        except:
            raise IOError('"%s" is not found in the database' % key)
        return content

    def __setitem__(self, key, value):
        f = GridFile({'metadata':{'name':key, 'container':self._container_name, 'doc_id':self._obj['_id']}}, self._obj.db, 'w', self._obj.collection.name)
        try:
            f.write(value)
        except TypeError:
            raise TypeError("GridFS value mus be string not %s" % type(value))
        finally:
            f.close()

    def __delitem__(self, key):
        self._fs.remove({'metadata.doc_id':self._obj['_id'], 'metadata.container':self._container_name, 'metadata.name':key}, collection=self._obj.collection.name)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self._container_name)

class FS(object):
    def __init__(self, gridfs, obj):
        self._gridfs = gridfs
        for container in self._gridfs.get('containers', []):
            self.__dict__[container] = FSContainer(container, obj)
        self._obj = obj
        self._fs = GridFS(self._obj.db)

    def __getitem__(self, key):
        try:
            f = GridFile({'metadata':{'name':key, 'doc_id':self._obj['_id']}}, self._obj.db, 'r', self._obj.collection.name)
            content = f.read()
            f.close()
        except IOError:
            raise IOError('"%s" is not found in the database' % key)
        return content

    def __setitem__(self, key, value):
        f = GridFile({'metadata':{'name':key, 'doc_id':self._obj['_id']}}, self._obj.db, 'w', self._obj.collection.name)
        try:
            f.write(value)
        except TypeError:
            raise TypeError("GridFS value mus be string not %s" % type(value))
        finally:
            f.close()

    def __getattr__(self, key):
        if key not in ['_gridfs', '_obj', '_fs', '_containers']:
            if key not in self._gridfs.get('containers', []) and key in self._gridfs.get('files', []):
                return self[key]
        return super(FS, self).__getattribute__(key)

    def __setattr__(self, key, value):
        if key not in ['_gridfs', '_obj', '_fs', '_containers']:
            if key not in self._gridfs.get('containers', []) and key in self._gridfs.get('files', []):
                self[key] = value
        else:
            super(FS, self).__setattr__(key, value)

    def __delitem__(self, key):
        self._fs.remove({'metadata.doc_id':self._obj['_id'], 'metadata.name':key}, collection=self._obj.collection.name)

    def __delattr__(self, key):
        del self[key]

    def open(self, name, mode='r'):
        assert name in self._gridfs.get('files', []), "%s is not declared in gridfs" % name
        return GridFile({'metadata':{'name':name, 'doc_id':self._obj['_id']}}, self._obj.db, mode, self._obj.collection.name)

    def __repr__(self):
        return "<%s of object '%s'>" % (self.__class__.__name__, self._obj['_id'])

