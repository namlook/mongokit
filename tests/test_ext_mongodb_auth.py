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
import logging

logging.basicConfig(level=logging.DEBUG)

from mongokit import *
from pymongo.objectid import ObjectId

CONNECTION = Connection()

class ExtMongoDBAuthTestCase(unittest.TestCase):
    """Tests MongoDB Authentication.
    To prevent possibly screwing someone's DB, does NOT confirm "strict"
    authentication.  E.g. doesn't create a root password.
    Simply checks if, when a login & pass is added to a DB, you can auth
    with it in the case of proper configuration.
    """
    def setUp(self):
        self.db = CONNECTION['test']
        # Toss in a user
        self.db.eval('db.addUser("foo", "bar")')
        self.collection = self.db['mongokit_auth']
        
    def tearDown(self):
        self.db.eval('db.system.users.remove({name: "foo"})')
        CONNECTION['test'].drop_collection('mongokit_auth')

    
    def test_auth(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            db_username = "foo"
            db_password = "bar"
            collection_name = "mongokit_auth"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        id = mydoc.save()
        assert isinstance(id['_id'], unicode)
        assert id['_id'].startswith("MyDoc"), id

        saved_doc = self.collection.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 43
        id = mydoc.save(uuid=False)
        assert isinstance(id['_id'], ObjectId)

        saved_doc = self.collection.find_one({"bla.bar":43})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value
        self.db.logout()
        
    def test_badauth(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            db_username = "foo"
            db_password = "bar"
            collection_name = "mongokit_auth"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc.save()
        self.assertRaises(ConnectionError, mydoc.save)
        self.db.logout()

 

