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
            gridfs = {'files': ['source']}
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

        f = doc.fs.open('source', 'r')
        print f.content_type
        print f.name
        f.close()
        del doc.fs.source

        assertion = False
        try:
            print doc.fs.source
        except IOError:
            assertion = True
        assert assertion

    def test_gridfs_with_open(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = {'files': ['source']}
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
        assert str(doc.fs) == "<FS of object '%s'>" % doc['_id'], str(doc.fs)
        doc.fs.source = "Hello World !"
        assert doc.fs.source == "Hello World !"
        f = doc.fs.open('source', 'w')
        f.write("Hello World Again !")
        f.close()
        assert doc.fs.source == u"Hello World Again !"
        f = doc.fs.open("source")
        assert f.read() == "Hello World Again !"
        f.close()

    def test_gridfs_without_saving(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = {'files': ['source']}
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

    def test_gridfs_bad_type(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = {'files': ['source']}
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

    def test_gridfs_with_container(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = {
                'files': ['source'],
                'containers': ['images']
            }

        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        doc.save()

        doc.fs.source = "Hello World !"
        assert doc.fs.source == "Hello World !"

        assertion = False
        try:
            doc.fs.images['first.jpg'] = 3
        except TypeError:
            assertion = True
        assert assertion

        doc.fs.images['first.jpg'] = "My first image"
        doc.fs.images['second.jpg'] = "My second image"

        assert doc.fs.images['first.jpg'] == 'My first image', doc.fs.images['first.jpg']
        assert doc.fs.images['second.jpg'] == 'My second image'

        doc.fs.images['first.jpg'] = "My very first image"
        assert doc.fs.images['first.jpg'] == 'My very first image', doc.fs.images['first.jpg']

        del doc.fs.images['first.jpg']
        
        assertion = False
        try:
            doc.fs.images['first.jpg']
        except IOError:
            assertion = True
        assert assertion

    def test_gridfs_multiple_values(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = {'files': ['source']}
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        doc.save()

        doc.fs.source = "Hello World !"
        assert doc.fs.source == "Hello World !"
        doc.fs.source = "1"
        assert doc.fs.source == "1"
        doc.fs.source = "Hello World !"
        assert doc.fs.source == "Hello World !"

        f = doc.fs.open('source', 'w')
        f.write("Hello World !")
        f.content_type = 'text/plain; charset=us-ascii'
        f.close()
        assert doc.fs.source == "Hello World !"
        f = doc.fs.open('source', 'w')
        f.write("1")
        f.content_type = 'application/octet-stream'
        f.close()
        assert doc.fs.source == "1"

    def test_gridfs_list(self):
        class Doc(Document):
            structure = {
                'title':unicode,
            }
            gridfs = {'files': ['foo', 'bla'], 'containers':['attachments']}
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['title'] = u'Hello'
        doc.save()

        doc.fs.foo = "Hello World !"
        doc.fs.bla = "Salut !"
        assert doc.fs.list() == ['foo', 'bla'], doc.fs.list()
        doc.fs.attachments['eggs.txt'] = "Ola !"
        doc.fs.attachments['spam.txt'] = "Saluton !"
        assert doc.fs.attachments.list() == [u'eggs.txt', u'spam.txt']
        assert doc.fs.list() == [u'foo', u'bla', u'attachments/eggs.txt', u'attachments/spam.txt']


