# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Nicolas Clairon
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
__author__ = 'n.namlook {at} gmail {dot} com'

import unittest

from mongokit import *
from mongokit.auth import User
from pymongo.objectid import ObjectId

CONNECTION = Connection()

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = CONNECTION['test']['mongokit']
        
    def tearDown(self):
        CONNECTION['test'].drop_collection('mongokit')
        CONNECTION['test'].drop_collection('versionned_mongokit')

    def test_password_validation(self):
        class SimpleUser(User):
            db_name = "test"
            collection_name = "mongokit"

        user = SimpleUser()
        user.login = u"user"
        self.assertRaises(RequireFieldError, user.validate)
        user.password = "myp4$$ord"

        assert user.verify_password("bla") == False
        assert user.verify_password("myp4$$ord") == True
    
    def test_create_user(self):
        class SimpleUser(User):
            db_name = "test"
            collection_name = "mongokit"

        user = SimpleUser()
        user.login = u"user"
        user.email = u"user@foo.bar"
        user.password = "u$ser_p4$$w0rd"
        user.save()

        saved_user = SimpleUser.get_from_id('user')
        assert saved_user.verify_password("bad") == False
        assert saved_user.verify_password("u$ser_p4$$w0rd") == True

    def test_overload_user(self):
        class SimpleUser(User):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "auth":{
                    "session_id":unicode,
                },
                "profil":{
                    "name":unicode,
                }
            }

        user = SimpleUser()
        user.login = u"user"
        user.email = u"user@foo.bar"
        user.password = "u$ser_p4$$w0rd"
        user.save()

        saved_user = SimpleUser.get_from_id('user')
        assert saved_user.verify_password("bad") == False
        assert saved_user.verify_password("u$ser_p4$$w0rd") == True


