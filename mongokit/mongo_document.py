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

import datetime
import pymongo
from pymongo.connection import Connection
from generators import MongoDocumentCursor
from mongo_exceptions import *
from mongokit.ext.mongodb_auth import authenticate_mongodb
from pymongo.son_manipulator import AutoReference, NamespaceInjector
import re
import logging

from mongokit.schema_document import SchemaDocument, SchemaProperties

from mongokit import authorized_types

authorized_types += [
  pymongo.binary.Binary,
  pymongo.objectid.ObjectId,
  pymongo.dbref.DBRef,
  pymongo.code.Code,
  type(re.compile("")),
]

from uuid import uuid4

log = logging.getLogger(__name__)

#__all__ = ['DotedDict', 'MongoDocument', 'VersionnedDocument', 'CustomType']

class MongoDocument(SchemaDocument):
    indexes = []
    belong_to = {}

    db_host = "localhost"
    db_port = 27017
    db_name = None
    collection_name = None

    # Optional auth support
    db_username = None
    db_password = None
    
    _connection = None
    _collection = None

    # If you are using Pylons, 
    # Connection will be overridden with the Pylons version
    # which sets up and manages the connection 
    _use_pylons = False
        
    def __init__(self, doc=None, gen_skel=True):
        super(MongoDocument, self).__init__(doc=doc, gen_skel=gen_skel)
        self._belong_to = None
        
    def save(self, uuid=True, validate=None, safe=True, *args, **kwargs):
        """
        save the document into the db.

        if uuid is True, a uuid4 will be automatiquely generated
        else, the pymongo.ObjectId will be used.

        If validate is True, the `validate` method will be called before
        saving. Not that the `validate` method will be called *before* the
        uuid is generated.

        `save()` follow the pymongo.collection.save arguments
        """
        if validate is not None:
            if validate or self.belong_to:
                self.validate()
        else:
            if not self.skip_validation or self.belong_to:
                self.validate()
        if '_id' not in self:
            if uuid:
                self['_id'] = unicode("%s-%s" % (self.__class__.__name__, uuid4()))
        if self._belong_to:
            db_name, full_collection_path, doc_id = self._belong_to
            self._get_connection()[db_name]['_mongometa'].insert({
              '_id': '%s-%s' % (full_collection_path, self['_id']),
              'pobj':{'id':doc_id, 'col':full_collection_path},
              'cobj':{'id':self['_id'], 'col':self.collection.full_name()}})
        if self.custom_types:
            self._process_custom_type(True, self, self.structure)
        id = self.collection.save(self, safe=safe, *args, **kwargs)
        if self.custom_types:
            self._process_custom_type(False, self, self.structure)
        return self

    def delete(self, cascade=False):
        """
        delete the document from the collection from his _id.

        This is equivalent to "self.remove({'_id':self['_id']})"
        """
        if cascade:
            self._delete_cascade(self, self.db_name, self.collection_name, self._get_connection())
        else:
            self.collection.remove({'_id':self['_id']})

    #
    # class methods, they work on collection
    #
    @classmethod
    def _get_connection(cls):
        """
        Utility method to abstract away the determination
        of which connection to utilize.
        If Pylons is setup and enabled for the class,
        it returns the threadlocal Pylons connection
        """
        if cls._connection is None:
            if cls._use_pylons:
                from mongokit.ext.pylons_env import MongoPylonsEnv
                log.debug("Pylons mode...")
                cls._connection = MongoPylonsEnv.mongo_conn()
            else:
                cls._connection = Connection(cls.db_host, cls.db_port)
        return cls._connection
            
    @classmethod
    def get_collection(cls):
        """
        return the collection associated to the object
        """
        if not cls._collection:
            if cls._use_pylons:
                from mongokit.ext.pylons_env import MongoPylonsEnv
                db_name = MongoPylonsEnv.get_default_db()
            else:
                db_name = cls.db_name
            if not db_name or not cls.collection_name:
                raise ConnectionError( 
                  "You must set a db_name and a collection_name" )
            db = cls._get_connection()[db_name]
            if cls.db_username and cls.db_password:
                # Password can't be empty or none or we ignore it
                # This *CAN* fail, in which case it throws ConnectionError
                log.debug("Username + Passwd set.  Authing against MongoDB.")
                authenticate_mongodb(db, cls.db_username, cls.db_password)
            if cls.use_autorefs:
                db.add_son_manipulator(NamespaceInjector()) # inject _ns
                db.add_son_manipulator(AutoReference(db))
            cls._collection = db[cls.collection_name]
        # creating index if needed
        for index in cls.indexes:
            unique = False
            if 'unique' in index.keys():
                unique = index['unique']
            ttl = 300
            if 'ttl' in index.keys():
                ttl = index['ttl']
            if isinstance(index['fields'], dict):
                fields = [(name, direction) for (name, direction) in sorted(index['fields'].items())]
            elif hasattr(index['fields'], '__iter__'):
                fields = [(name, 1) for name in index['fields']]
            else:
                fields = index['fields']
            log.debug('Creating index for %s' % index['fields'])
            cls._collection.ensure_index(fields, unique=unique, ttl=ttl)
        return cls._collection

    def _get_collection(self):
        return self.__class__.get_collection()
    collection = property(_get_collection)

    @classmethod
    def get_from_id(cls, id):
        """
        return the document wich has the id

        The query is launch against the db and collection of the object.
        """
        bson_obj = cls.get_collection().find_one({"_id":id})
        if bson_obj:
            return cls(bson_obj)

    @classmethod
    def all(cls, *args, **kwargs):
        """
        return all document wich match the query.
        `all()` takes the same arguments than the the pymongo.collection.find method.

        The query is launch against the db and collection of the object.
        """
        return MongoDocumentCursor(
          cls.get_collection().find(*args, **kwargs), cls)

    @classmethod
    def fetch(cls, spec=None, fields=None, skip=0, limit=0, slave_okay=None, timeout=True, snapshot=False, _sock=None):
        """
        return all document wich match the structure of the object
        `fetch()` takes the same arguments than the the pymongo.collection.find method.

        The query is launch against the db and collection of the object.
        """
        if spec is None:
            spec = {}
        for key in cls.structure:
            if key in spec:
                if isinstance(spec[key], dict):
                    spec[key].update({'$exists':True})
            else:
                spec[key] = {'$exists':True}
        return MongoDocumentCursor(
          cls.get_collection().find(
            spec=spec, 
            fields=fields, 
            skip=skip,
            limit=limit,
            slave_okay=slave_okay,
            timeout=timeout,
            snapshot=snapshot,
            _sock=_sock),
          cls)

    @classmethod
    def fetch_one(cls, spec=None, fields=None, skip=0, limit=0, slave_okay=None, timeout=True, snapshot=False, _sock=None):
        """
        return one document wich match the structure of the object
        `fetch_one()` takes the same arguments than the the pymongo.collection.find method.

        If multiple documents are found, raise a MultipleResultsFound exception.
        If no document is found, return None

        The query is launch against the db and collection of the object.
        """
        bson_obj = cls.fetch(
            spec=spec, 
            fields=fields, 
            skip=skip,
            limit=limit,
            slave_okay=slave_okay,
            timeout=timeout,
            snapshot=snapshot,
            _sock=_sock)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return cls(list(bson_obj)[0])


    @classmethod
    def group(cls, *args, **kwargs):
        return MongoDocumentCursor(
          cls.get_collection().group(*args, **kwargs), cls)

    @classmethod
    def one(cls, *args, **kwargs):
        """
        return on document wich match the query.
        `one()` takes the same arguments than the the pymongo.collection.find method.

        If multiple documents are found, raise a MultipleResultsFound exception.
        If no document is found, return None

        The query is launch against the db and collection of the object.
        """
        bson_obj = cls.get_collection().find(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return cls(list(bson_obj)[0])

    @classmethod
    def remove(cls, *args, **kwargs):
        """
        remove all document wich match the query
        `remove()` takes the same arguments than the the pymongo.collection.remove method.

        The query is launch against the db and collection of the object.
        """
        if kwargs.pop('cascade', None):
            for obj in  cls.get_collection().find(*args, **kwargs):
                cls._delete_cascade(obj, cls.db_name, cls.collection_name, cls._get_connection())
        else:
            return cls.get_collection().remove(*args, **kwargs)

    @classmethod 
    def _delete_cascade(cls, doc, db_name, collection_name, connection):
        full_collection_path = "%s.%s" % (db_name, collection_name)
        rel_list = connection[db_name]['_mongometa'].find({'pobj.id':doc['_id'], 'pobj.col':full_collection_path})
        if rel_list.count():
            for rel_doc in rel_list:
                belong_db_name, belong_collection_name = rel_doc['cobj']['col'].split('.', 1)
                belonging_doc = connection[belong_db_name][belong_collection_name].find_one({'_id':rel_doc['cobj']['id']})
                if belonging_doc:
                    cls._delete_cascade(belonging_doc, belong_db_name, belong_collection_name, connection)
                connection[db_name][collection_name].remove({'_id':doc['_id']})
                connection[db_name]['_mongometa'].remove({'_id':rel_doc['_id']})
        else:
            connection[db_name][collection_name].remove({'_id':doc['_id']})
        
    def _validate_descriptors(self):
        super(MongoDocument, self)._validate_descriptors()
        # XXX indexes validation
        if self.belong_to:
            if not len(self.belong_to) == 1:
                raise ValueError("belong_to must contain only one item")
            if not issubclass(self.belong_to.values()[0], MongoDocument):
                raise ValueError("self.belong_to['%s'] must have a MongoDocument subclass (got %s instead)" % (
                  self.belong_to.keys()[0], self.belong_to.values()[0]))

    def _validate_doc(self, doc, struct, path = ""):
        if path in self.belong_to:
            if not self._belong_to:
                db_name = self.belong_to[path].db_name
                collection_name = self.belong_to[path].collection_name
                full_collection_path = "%s.%s" % (db_name, collection_name)
                self._belong_to = (db_name, full_collection_path, doc)
        super(MongoDocument, self)._validate_doc(doc, struct, path)
 
class MongoPylonsDocument(MongoDocument):
    """Lazy helper base class to inherit from if you are
    sure you will always live in / require the pylons evironment.
    Keep in mind if you need CLI testing, "paster shell" will allow 
    you to test within a pylons environment (via an ipython shell)"""
    _use_pylons = True
