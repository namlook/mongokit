#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009, Brendan W. McAdams <bwmcadams@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of any future
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging

import pymongo.database
from mongokit.mongo_exceptions import ConnectionError, MongoAuthException

log = logging.getLogger(__name__)


def parse_mongo_url(mongo_url):
    """Parses a MongoDB connection string.  String format::

        >>> mongodb.url = \
            mongodb://bwmcadams@passW0Rd?@localhost:27017/blog

        Standard URL similar to SQLAlchemy. Use #fragment for collection name.
        Uses modified code from Python's urlparse
    """
    log.debug("Parsing Mongo Connection string '%s'" % mongo_url)
    if not mongo_url.startswith("mongodb://"):
        log.error("Invalid / unparseable MongoDB connection string.")
        raise ValueError("Invalid MongoDB connection string.")

    scheme = mongo_url.lower()
    mongo_url = mongo_url.split("mongodb://", 1)[1]
    if '#' in mongo_url:
        mongo_url, collection = mongo_url.split('#', 1)
        log.debug("Found a collection specification '%s'" % collection)

    if '/' in mongo_url:
        mongo_url, database = mongo_url.split('/', 1)
        log.debug("Found a database specification '%s'" % database)

    # Parse URL / password if they exist
    head, sep, tail = mongo_url.partition('@')
    username = password = None
    if sep:
        if head.find(':') > -1:
            username, password = head.split(':', 1)
            log.debug("Found auth information (l: %s p: %s )" %
                       (username, password))
        mongo_url = tail

    port = 27017
    if mongo_url.find(':') > -1:
        mongo_url, port = mongo_url.split(':')
        try:
            port = int(port)
        except:
            port = 27017
            pass
        log.debug("Port configured as %d" % port)
    
    log.debug("data parsed; returning.")

    return {'username': username,
            'password': password,
            'host': mongo_url,
            'port': port,
            'database': database,
            'collection': collection}


def authenticate_mongodb(dbh, username, password):
    """Attempts to authenticate a MongoDB connection.
    DBH should be a Database object, and not a Connection,
    as MongoDB's authentication hooks go on a db basis.
    """
    if not dbh._Database__connection.admin.system.users.find().count():
        raise MongoAuthException('no admin user found in database')
    if not isinstance(dbh, pymongo.database.Database):
        raise TypeError("authenicate_mongodb excepts an object of " +
                        " pymongo.database.Database for param 'dbh'." +
                        " Supplied type '%s' is invalid. " % type(dbh))

    log.info("Attempting to authenticate %s/%s " % (username, password))
    if not dbh.authenticate(username, password):
        log.exception("Failed to authenticate.")
        raise MongoAuthException('bad username or password')
    log.debug("Auth success.")
    
