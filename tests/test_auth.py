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
from mongokit.auth import User
from bson.objectid import ObjectId

import logging
logging.basicConfig()

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection['test'].drop_collection('mongokit')
        self.connection['test'].drop_collection('versionned_mongokit')

    def test_password_validation(self):
        class SimpleUser(User): pass
        self.connection.register([SimpleUser])

        user = self.col.SimpleUser()
        user.login = u"user"
        self.assertRaises(RequireFieldError, user.validate)
        user.password = "myp4$$ord"

        assert user.verify_password("bla") == False
        assert user.verify_password("myp4$$ord") == True
        assert len(user.password) == len(user['user']['password']) == 80
        
        del user.password
        assert user.password is None
        assert user['user']['password'] is None
    
    def test_create_user(self):
        class SimpleUser(User): pass
        self.connection.register([SimpleUser])

        user = self.col.SimpleUser()
        user.login = u"user"
        user.email = u"user@foo.bar"
        user.password = u"u$ser_p4$$w0rd"
        print "°°°°°°°°°", user
        user.save()

        saved_user = self.col.SimpleUser.get_from_id('user')
        assert saved_user.verify_password("bad") == False
        assert saved_user.verify_password(u"u$ser_p4$$w0rd") == True

        assert user.login == u"user"
        assert user['_id'] == u'user'
        assert user['user']['login'] == u'user'
        del user.login
        assert user['_id'] is None
        assert user['user']['login'] is None
        assert user.login is None

        assert user.email == user['user']['email'] == u'user@foo.bar'
        del user.email
        assert user['user']['email'] is None
        assert user.email is None

    def test_overload_user(self):
        class SimpleUser(User):
            structure = {
                "auth":{
                    "session_id":unicode,
                },
                "profil":{
                    "name":unicode,
                }
            }
        self.connection.register([SimpleUser])

        user = self.col.SimpleUser()
        user.login = u"user"
        user.email = u"user@foo.bar"
        user.password = "u$ser_p4$$w0rd"
        user.save()

        saved_user = self.col.SimpleUser.get_from_id('user')
        assert saved_user.verify_password("bad") == False
        assert saved_user.verify_password("u$ser_p4$$w0rd") == True


