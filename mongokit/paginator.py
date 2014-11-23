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


DEFAULT_LIMIT = 10


class Paginator(object):
    """ Provides pagination on a Cursor object

    Keyword arguments:
    cursor -- Cursor of a returned query
    page   -- The page number requested
    limit  -- The number of items per page

    Properties:
    items        -- Returns the paginated Cursor object
    is_paginated -- Boolean value determining if the cursor has multiple pages
    start_index  -- int index of the first item on the requested page
    end_index    -- int index of the last item on the requested page
    current_page -- int page number of the requested page
    previous_page-- int page number of the previous page w.r.t. current requested page
    next_page    -- int page number of the next page w.r.t. current requested page
    has_next     -- True or False if the Cursor has a next page
    has_previous -- True or False if the Cursor has a previous page
    page_range   -- list of page numbers
    num_pages    -- int of the number of pages
    count        -- int total number of items on the cursor
    """

    def __init__(self, cursor, page=1, limit=DEFAULT_LIMIT):
        self._cursor = cursor
        self._count = self._cursor.count() if cursor else 0
        self._limit = limit
        self._page = int(page)
        self._set_page(self._page)

    @property
    def items(self):
        return self._cursor

    @property
    def is_paginated(self):
        return self.num_pages > 1

    @property
    def start_index(self):
        if self._page == 1:
            return 1
        if self._limit == 1:
            return self._page
        return ((self._page-1) * self._limit) + 1

    @property
    def end_index(self):
        if self._limit == 1:
            return self._page

        if self._page == 1:
            return self._count if self._count < self._limit else self._limit

        calc_end = (self._page * self._limit)
        return calc_end if calc_end < self._count else self._count

    @property
    def current_page(self):
        return self._page

    @property
    def previous_page(self):
        return self._page - 1

    @property
    def next_page(self):
        return self._page + 1

    @property
    def has_next(self):
        return self.end_index < self._count

    @property
    def has_previous(self):
        return self.start_index - self._limit >= 0

    @property
    def page_range(self):
        return [p for p in xrange(1, self.num_pages+1)]

    @property
    def num_pages(self):
        if self._count <= 0:
            return 0
        if self._count <= self._limit:
            return 1

        pages_f = self._count / float(self._limit)
        pages_i = int(pages_f)

        return (pages_i + 1) if pages_f > pages_i else pages_i

    @property
    def count(self):
        return self._count

    def _set_page(self, _):
        if self._page > 1:
            self._cursor.skip(self.start_index - 1)

        if self._cursor:
            self._cursor.limit(self._limit)
