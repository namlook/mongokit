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

__version__ = "0.9.1"

# W0401,W0614,W0611 wildcard/unused import
# pylint: disable=W0401,W0614,W0611

from bson.dbref import DBRef
from mongokit.cursor import Cursor
from mongokit.operators import *
from mongokit.schema_document import *
from mongokit.mongo_exceptions import *
from mongokit.document import Document, ObjectId
from mongokit.versioned_document import VersionedDocument
from mongokit.database import Database
from mongokit.collection import Collection
from mongokit.connection import Connection, MongoClient, MongoReplicaSetClient, ReplicaSetConnection
from mongokit.master_slave_connection import MasterSlaveConnection
from pymongo import (
    ASCENDING as INDEX_ASCENDING,
    DESCENDING as INDEX_DESCENDING,
    ALL as INDEX_ALL,
    GEO2D as INDEX_GEO2D,
    GEOHAYSTACK as INDEX_GEOHAYSTACK,
    GEOSPHERE as INDEX_GEOSPHERE,
    OFF as INDEX_OFF,
    HASHED as INDEX_HASHED
)
from mongokit.migration import DocumentMigration
# pylint: enable=W0401,W0614,W0611
