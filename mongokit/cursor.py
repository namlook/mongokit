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

from pymongo.cursor import Cursor as PymongoCursor
from collections import deque


class Cursor(PymongoCursor):
    def __init__(self, *args, **kwargs):
        self.__wrap = None
        if kwargs:
            self.__wrap = kwargs.pop('wrap', None)
        super(Cursor, self).__init__(*args, **kwargs)

    def next(self):
        if self._Cursor__empty:
            raise StopIteration
        if len(self.__data) or self._refresh():
            if isinstance(self._Cursor__data, deque):
                item = self._Cursor__data.popleft()
            else:
                item = self._Cursor__data.pop(0)

            return self.__manipulate_item(item)

        else:
            raise StopIteration

    def __getitem__(self, index):
        # This will be a cursor if `index` is a slice
        item_or_cursor = super(Cursor, self).__getitem__(index)

        if isinstance(item_or_cursor, dict):
            return self.__manipulate_item(item_or_cursor)
        else:
            return item_or_cursor

    def __manipulate_item(self, item):
        if self._Cursor__manipulate:
            db = self._Cursor__collection.database
            son = db._fix_outgoing(item, self._Cursor__collection)
        else:
            son = item
        if self.__wrap is not None:
            if self.__wrap.type_field in son:
                return getattr(self._Cursor__collection,
                               son[self.__wrap.type_field])(son)
            return self.__wrap(son, collection=self._Cursor__collection)
        else:
            return son
