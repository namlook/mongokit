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

import unittest

from mongokit import *

class HelpersTestCase(unittest.TestCase):
        
    def test_DotExpandedDict(self):
        from mongokit.schema_document import DotExpandedDict
        d = DotExpandedDict({'person.1.firstname': ['Simon'],
          'person.1.lastname': ['Willison'],
          'person.2.firstname': ['Adrian'], 
          'person.2.lastname': ['Holovaty']}) 
        assert d == {'person': {'1': {'lastname': ['Willison'], 'firstname': ['Simon']}, '2': {'lastname': ['Holovaty'], 'firstname': ['Adrian']}}} 
        assert d['person'] == {'1': {'lastname': ['Willison'], 'firstname': ['Simon']}, '2': {'lastname': ['Holovaty'], 'firstname': ['Adrian']}} 
        assert d['person']['1'] == {'lastname': ['Willison'], 'firstname': ['Simon']} 
        # Gotcha: Results are unpredictable if the dots are "uneven": 
        assert DotExpandedDict({'c.1': 2, 'c.2': 3, 'c': 1}) == {'c': 1} 

    def test_DotCollapsedDict(self):
        dic = {'foo':{}}
        d = DotCollapsedDict(dic)
        assert d == {'foo':{}}, d

        dic = {'_id': u'user', 'a':3, 'e':5, "g":2, 'f':6}
        d = DotCollapsedDict(dic)
        assert d == {'_id': u'user', 'a':3, 'e':5, "g":2, 'f':6}, d

        dic = {'_id': u'user', 'a':{'b':{'c':{'d':3}, 'e':5}, "g":2}, 'f':6}
        d = DotCollapsedDict(dic)
        assert d == {'a.b.c.d': 3, '_id': u'user', 'a.b.e': 5, 'a.g': 2, 'f': 6}, d

        dic = {'_id': u'user', 'a':{'b':1, 'd':3, 'e':5}, 'f':6}
        d = DotCollapsedDict(dic)
        assert d == {'_id': u'user', 'a.b': 1, 'a.d': 3, 'a.e': 5, 'f': 6}, d

        dic = {'_id': u'user', 'a':{'b':1, 'd':3, 'e':{'g':5, 'h':0}}, 'f':6}
        d = DotCollapsedDict(dic)
        assert d == {'a.d': 3, 'a.e.h': 0, 'a.b': 1, 'f': 6, 'a.e.g': 5, '_id': u'user'}, d

        dic = {'_id': u'user', 'a':{int:{'c':{'d':3}, 'e':5}, "g":2}, 'f':6}
        d = DotCollapsedDict(dic)
        assert d == {'a.$int.c.d': 3, 'a.$int.e': 5, '_id': u'user', 'a.g': 2, 'f': 6}, d


