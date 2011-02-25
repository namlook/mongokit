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

import unittest

from mongokit import *
from mongokit.schema_document import DotExpandedDict

class HelpersTestCase(unittest.TestCase):
        
    def test_DotExpandedDict(self):
        d = DotExpandedDict({'a.$int.c.d': 3, 'a.$int.e': 5, '_id': u'user', 'a.g': 2, 'f': 6})
        assert d == {'_id': u'user', 'a':{int:{'c':{'d':3}, 'e':5}, "g":2}, 'f':6}, d

        d = DotExpandedDict({'foo.bla.$unicode': [unicode], 'foo.bar': {}})
        assert d == {'foo': {'bar': {}, 'bla': {unicode: [unicode]}}}, d

        self.assertRaises(EvalException, DotExpandedDict, {'foo.bla.$arf': [unicode], 'foo.bar': {}})

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

        dic = {'bar':{'foo':{}}}
        d = DotCollapsedDict(dic)
        assert d == {'bar.foo':{}}, d

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

    def test_DotCollapsedDict_with_reference(self):
        dic = {'foo':{}}
        d = DotCollapsedDict(dic, reference={'foo':{}})
        assert d == {'foo':{}}, d

        dic = {'bar':{'foo':{}}}
        d = DotCollapsedDict(dic, reference={'bar':{'foo':{}}})
        assert d == {'bar':{'foo':{}}}, d

        dic = {'bar':{'foo':3}, 'bla':{'g':2, 'h':3}}
        d = DotCollapsedDict(dic, reference={'bar.foo':None, 'bla':{'g':None, 'h':None}})
        assert d == {'bar.foo':3, 'bla':{'g':2, 'h':3}}, d

#        # XXX TODO
#        dic = {'bar':{'foo':3, 'bla':2}}
#        d = DotCollapsedDict(dic, reference={'bar.foo':None, 'bar':{'bla':None}})
#        assert d == {'bar.foo':3, 'bar':{'bla':2}}, d

        dic = {'_id': u'user', 'a':3, 'e':5, "g":2, 'f':6}
        d = DotCollapsedDict(dic,  reference=dic)
        assert d == {'_id': u'user', 'a':3, 'e':5, "g":2, 'f':6}, d

        dic = {'_id': u'user', 'a':{'b':1, 'd':3, 'e':{'g':5, 'h':0}}, 'f':6}
        d = DotCollapsedDict(dic, reference={'_id':None, 'a.b':1, 'a.d':3, 'a.e':{'g':5, 'h':0}, 'a.f':6})
        assert d == {'a.d': 3, 'a.b': 1, 'f': 6, 'a.e':{'g': 5, 'h':0}, '_id': u'user'}, d

        dic = {'_id': u'user', 'a':{'b':{'c':{'d':3}, 'e':5}, "g":2}, 'f':6}
        d = DotCollapsedDict(dic, reference={'_id':None, 'a.b':{'c':{'d':3}, 'e':5}, 'a.g':2, 'f':6})
        assert d == {'_id': u'user', 'a.b':{'c': {'d': 3}, 'e':5}, 'a.g': 2, 'f': 6}, d

    def test_DotCollapsedDict_with_remove_under_type(self):
        dic = {'_id': u'user', 'a':{int:{'c':{'d':3}, 'e':5}, "g":2}, 'f':6}
        d = DotCollapsedDict(dic, remove_under_type=True)
        assert d == {'a': {}, '_id': u'user', 'f': 6}, d

        dic = {'bla':{'foo':{unicode:{"bla":int}}, 'bar':unicode}}
        d = DotCollapsedDict(dic, remove_under_type=True)
        assert d == {'bla.foo':{}, 'bla.bar':unicode}, d

        dic = {'bla':{'foo':{unicode:[unicode]}, 'bar':"egg"}}
        d = DotCollapsedDict(dic, remove_under_type=True)
        assert d == {'bla.foo':{}, 'bla.bar':"egg"}, d

    def test_DotCollapsedDict_with_type(self):
        dic = {'_id': u'user', 'a':{int:{'c':{'d':3}, 'e':5}, "g":2}, 'f':6}
        d = DotCollapsedDict(dic)
        assert d == {'a.$int.c.d': 3, 'a.$int.e': 5, '_id': u'user', 'a.g': 2, 'f': 6}, d

        dic = {'bla':{'foo':{unicode:{"bla":3}}, 'bar':'egg'}}
        d = DotCollapsedDict(dic)
        assert d == {'bla.foo.$unicode.bla': 3, 'bla.bar': "egg"}, d

        dic = {'bla':{'foo':{unicode:['egg']}, 'bar':"egg"}}
        d = DotCollapsedDict(dic)
        assert d == {'bla.foo.$unicode': ['egg'], 'bla.bar': 'egg'}, d
