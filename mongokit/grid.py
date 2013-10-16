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

from gridfs import GridFS, NoFile, GridOut
from pymongo import ASCENDING, DESCENDING

#try:
#    from magic import Magic
#except:
#    Magic = None


class FS(GridFS):
    def __init__(self, obj):
        self._obj = obj
        super(FS, self).__init__(obj.db)
        if not isinstance(self, FSContainer):
            for container in obj.gridfs.get('containers', []):
                self.__dict__[container] = FSContainer(container, obj)
        #self._fs = GridFS(self._obj.db)
        #if Magic:
        #    self._magic = Magic(mime=True)

    def _get_spec(self, **kwargs):
        if not self._obj.get('_id'):
            raise RuntimeError('This document is not saved, no files should be attached')
        spec = {'docid': self._obj['_id']}
        spec.update(kwargs)
        return spec

    def __getitem__(self, key):
        if not self._obj.get('_id'):
            raise RuntimeError('This document is not saved, no files should be attached')
        return self.get_last_version(key).read()

    def __setitem__(self, key, value):
        content_type = None
        #if value and Magic:
        #    content_type = self._magic.from_buffer(value)
        spec = self._get_spec(filename=key, content_type=content_type)
        try:
            self.put(value, **spec)
        except TypeError:
            raise TypeError("GridFS value mus be string not %s" % type(value))

    def __getattr__(self, key):
        if not key.startswith('_'):
            if key not in self._obj.gridfs.get('containers', []) and key in self._obj.gridfs.get('files', []):
                return self[key]
        return super(FS, self).__getattribute__(key)

    def __setattr__(self, key, value):
        if not key.startswith('_'):
            if key not in self._obj.gridfs.get('containers', []) and key in self._obj.gridfs.get('files', []):
                self[key] = value
        else:
            super(FS, self).__setattr__(key, value)

    def __delitem__(self, key):
        self._GridFS__files.remove(self._get_spec(filename=key))

    def __delattr__(self, key):
        if not key.startswith('_'):
            del self[key]
        else:
            super(FS, self).__delattr__(key)

    def __iter__(self):
        if self._obj.get('_id'):
            for metafile in self._GridFS__files.find(self._get_spec()):
                yield self.get(metafile['_id'])

    def __repr__(self):
        return "<%s of object '%s'>" % (self.__class__.__name__, self._obj.__class__.__name__)

    def new_file(self, filename):
        return super(FS, self).new_file(**self._get_spec(filename=filename))

    def put(self, data, **kwargs):
        return super(FS, self).put(data, **self._get_spec(**kwargs))

    def get_version(self, filename, version=-1, **kwargs):
        """Get a file from GridFS by ``"filename"`` or metadata fields.

        Returns a version of the file in GridFS whose filename matches
        `filename` and whose metadata fields match the supplied keyword
        arguments, as an instance of :class:`~gridfs.grid_file.GridOut`.

        Version numbering is a convenience atop the GridFS API provided
        by MongoDB. If more than one file matches the query (either by
        `filename` alone, by metadata fields, or by a combination of
        both), then version ``-1`` will be the most recently uploaded
        matching file, ``-2`` the second most recently
        uploaded, etc. Version ``0`` will be the first version
        uploaded, ``1`` the second version, etc. So if three versions
        have been uploaded, then version ``0`` is the same as version
        ``-3``, version ``1`` is the same as version ``-2``, and
        version ``2`` is the same as version ``-1``.

        Raises :class:`~gridfs.errors.NoFile` if no such version of
        that file exists.

        An index on ``{filename: 1, uploadDate: -1}`` will
        automatically be created when this method is called the first
        time.

        :Parameters:
          - `filename`: ``"filename"`` of the file to get, or `None`
          - `version` (optional): version of the file to get (defaults
            to -1, the most recent version uploaded)
          - `**kwargs` (optional): find files by custom metadata.

        .. versionchanged:: 1.11
           `filename` defaults to None;
        .. versionadded:: 1.11
           Accept keyword arguments to find files by custom metadata.
        .. versionadded:: 1.9
        """
        # This is took from pymongo source. We need to go a little deeper here
        self._GridFS__files.ensure_index([("filename", ASCENDING),
                                          ("uploadDate", DESCENDING)])
        ########## Begin of MongoKit hack ##########
        cursor = self._GridFS__files.find(self._get_spec(filename=filename, **kwargs))
        ########## end of MongoKit hack ############
        if version < 0:
            skip = abs(version) - 1
            cursor.limit(-1).skip(skip).sort("uploadDate", DESCENDING)
        else:
            cursor.limit(-1).skip(version).sort("uploadDate", ASCENDING)
        try:
            grid_file = cursor.next()
            return GridOut(self._GridFS__collection, grid_file["_id"])
        except StopIteration:
            raise NoFile("no version %d for filename %r" % (version, filename))


class FSContainer(FS):
    def __init__(self, container_name, obj):
        self._container_name = container_name
        super(FSContainer, self).__init__(obj)

    def _get_spec(self, **kwargs):
        if not self._obj.get('_id'):
            raise RuntimeError('This document is not saved, no files should be attached')
        spec = {'container': self._container_name, 'docid': self._obj['_id']}
        spec.update(kwargs)
        return spec

    def __repr__(self):
        return "<%s (%s) of object '%s'>" % (self.__class__.__name__,
                                             self._container_name, self._obj.__class__.__name__)
