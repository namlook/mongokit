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

from mongokit import Document
import hashlib
import os


class User(Document):
    structure = {
        "_id": unicode,
        "user": {
            "login": unicode,
            "password": unicode,  # TODO validator
            "email": unicode,
        }
    }
    required_fields = ['user.password', 'user.email']  # what if openid ? password is None

    def set_login(self, login):
        self['_id'] = login
        self['user']['login'] = login

    def get_login(self):
        return self['_id']

    def del_login(self):
        self['_id'] = None
        self['user']['login'] = None

    login = property(get_login, set_login, del_login)

    def set_password(self, password):
        """ Hash password on the fly """
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        password_salt = hashlib.sha1(os.urandom(60)).hexdigest()
        crypt = hashlib.sha1(password + password_salt).hexdigest()
        self['user']['password'] = unicode(password_salt + crypt, 'utf-8')

    def get_password(self):
        """ Return the password hashed """
        return self['user']['password']

    def del_password(self):
        self['user']['password'] = None

    password = property(get_password, set_password, del_password)

    def verify_password(self, password):
        """ Check the password against existing credentials  """
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        password_salt = self['user']['password'][:40]
        crypt_pass = hashlib.sha1(password + password_salt).hexdigest()
        if crypt_pass == self['user']['password'][40:]:
            return True
        else:
            return False

    def get_email(self):
        return self['user']['email']

    def set_email(self, email):
        # TODO check if it's a well formatted email
        self['user']['email'] = email

    def del_email(self):
        self['user']['email'] = None

    email = property(get_email, set_email, del_email)

    def save(self, *args, **kwargs):
        assert self['_id'] == self['user']['login']
        super(User, self).save(*args, **kwargs)
