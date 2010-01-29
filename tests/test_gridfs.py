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

import unittest

from mongokit import *
from pymongo.objectid import ObjectId


class GridFSTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')

    def test_simple_gridfs(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = ['source']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        doc.save()

        assertion = False
        try:
            print doc.fs.source
        except IOError:
            assertion = True
        assert assertion
        doc.fs.source = "Hello World !"

        assert doc.fs.source == u"Hello World !"
        f = doc.fs.open("source", 'r')
        assert f.read() == "Hello World !"
        f.close()
        assert doc['title'] == u'Hello'
        assert len(doc.fs.__dict__) == 3

    def test_gridfs_with_open(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = ['source']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        doc.save()

        assertion = False
        try:
            print doc.fs.open('source', 'r')
        except IOError:
            assertion = True
        assert assertion
        doc.fs.source = "Hello World !"
        assert doc.fs.source == "Hello World !"
        f = doc.fs.open('source', 'w')
        f.write("Hello World Again !")
        f.close()
        assert doc.fs.source == u"Hello World Again !"
        f = doc.fs.open("source")
        assert f.read() == "Hello World Again !"
        f.close()
        assert len(doc.fs.__dict__) == 3

    def test_gridfs_without_saving(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = ['source']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        assertion = False
        try:
            doc.fs.source = "Hello World !"
        except KeyError:
            assertion = True
        assert assertion
        doc.save()
        doc.fs.source = 'Hello world !'
        assert len(doc.fs.__dict__) == 3

    def test_gridfs_bad_type(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = ['source']
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        doc.save()
        assertion = False
        try:
            doc.fs.source = 3
        except TypeError:
            assertion = True
        assert assertion
        assertion = False
        try:
            doc.fs.source = u"Hello World !"
        except TypeError:
            assertion = True
        assert assertion
        assert len(doc.fs.__dict__) == 3

