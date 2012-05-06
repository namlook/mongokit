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
import logging

logging.basicConfig(level=logging.DEBUG)

from mongokit import *
from bson.objectid import ObjectId

admin_created = False

class _ExtMongoDBAuthTestCase(unittest.TestCase):
    """Tests MongoDB Authentication.
    To prevent possibly screwing someone's DB, does NOT confirm "strict"
    authentication.  E.g. doesn't create a root password.
    Simply checks if, when a login & pass is added to a DB, you can auth
    with it in the case of proper configuration.
    """
    def setUp(self):
        # if no admin user is defined, create one
        import md5
        self.connection = Connection()
        if not self.connection.admin.system.users.find().count():
            username = "theadmin"
            self.connection.test.system.users.insert({"user": username, "pwd": md5.new(username + ":mongo:" + "anadminpassword").hexdigest()})
            #CONNECTION.admin.eval('db.addUser("theadmin", "anadminpassword")')
            admin_created = True
        self.db = CONNECTION['test']
        # Toss in a user
        username = "theadmin"
        self.connection.test.system.users.insert({"user": username, "pwd": md5.new(username + ":mongo:" + "bar").hexdigest()})
        self.collection = self.db['mongokit_auth']
        
    def tearDown(self):
        if admin_created:
            self.connection.admin.system.users.remove({})
        self.connection.test.system.users.remove({"user": "foo"})
        self.connection.test.drop_collection('mongokit_auth')

    def test_auth(self):
        class MyDoc(Document):
            db_username = "foo"
            db_password = "bar"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])
        mydoc = self.connection.test.mongokit_auth.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        id = mydoc.save()
        assert isinstance(id['_id'], ObjectId)

        saved_doc = self.collection.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

        mydoc = self.connection.test.mongokit_auth.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 43
        id = mydoc.save(uuid=False)
        assert isinstance(id['_id'], ObjectId)

        saved_doc = self.collection.find_one({"bla.bar":43})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value
        self.db.logout()

    def _test_badauth_no_admin(self):
        # XXX WARNING : uncommented this test will remove the root password of the mongodb instance !!!!
        CONNECTION.admin.system.users.remove({})
        class MyDoc(Document):
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
        self.assertRaises(MongoAuthException, mydoc.save)
        self.db.logout()

    def test_badauth(self):
        crash = False
        try:
            class MyDoc(Document):
                db_username = "foo"
                db_password = "spam"
                structure = {
                    "bla":{
                        "foo":unicode,
                        "bar":int,
                    },
                    "spam":[],
                }
            self.connection.register([MyDoc])
        except MongoAuthException:
            crash = True
        assert crash

 

