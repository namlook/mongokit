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
from mongokit.schema_document import STRUCTURE_KEYWORDS, CustomType, SchemaTypeError
from mongokit.schema_document import totimestamp, fromtimestamp

from uuid import uuid4

log = logging.getLogger(__name__)

# field wich does not need to be declared into the structure
STRUCTURE_KEYWORDS += ['_id', '_ns', '_revision']

class RelatedProperties(object):
    def __init__(self, descriptor, doc):
        self._descriptor = descriptor
        self._doc = doc
        def call_func(self, query=None):
            _query = {}
            _query.update(self.query)
            if query is not None:
                _query.update(query)
            return self.obj.fetch(_query)
        for key in self._descriptor:
            desc = self._descriptor[key]
            if not callable(desc['target']):
                fuc = lambda x: {desc['target']:x}
            else:
                fuc = desc['target']
            if desc.get('autoref',False):
                desc['query'] = fuc(pymongo.dbref.DBRef(collection=self._doc.collection.name(), id=self._doc['_id']))
            else:
                desc['query'] = fuc(self._doc['_id'])
            methods = {
              'query':self._descriptor[key]['query'],
              '__call__':call_func,
              'obj':self._descriptor[key]['class'],
            }
            setattr(self, key, type(key, (object,), methods)())

class MongoProperties(SchemaProperties):
    def __new__(cls, name, bases, attrs):
        obj = super(MongoProperties, cls).__new__(cls, name, bases, attrs)
        if obj.collection_name:
            if not obj.db_name and not obj._use_pylons:
                raise ConnectionError('You must specify a db_name')
            elif obj._use_pylons:
                from mongokit.ext.pylons_env import MongoPylonsEnv
                log.debug("Pylons mode...")
                obj.connection = MongoPylonsEnv.mongo_conn()
                if obj.db_name:
                    obj.db = obj.connection[obj.db_name]
                else:
                    db_name = MongoPylonsEnv.get_default_db()
                    if db_name is None:
                        raise PylonsEnvError("It seems that you want to use"
                            " the Pylons environnement. But I can't found the"
                            " mongodb.db. Please check your configuration file.")
                    obj.db = obj.connection[db_name]
                    attrs['db_name'] = db_name
            else:
                if not obj.db_host:
                    raise ConnectionError('You must specify a db_host')
                if not obj.db_port:
                    raise ConnectionError('You must specify a db_port')
                if not hasattr(obj, 'connection'):
                    obj.connection = Connection(obj.db_host, obj.db_port)
                elif obj.db_host != obj.connection.host() or obj.db_port != obj.connection.port():
                    obj.connection = Connection(obj.db_host, obj.db_port)
                obj.db = obj.connection[obj.db_name]
            if obj.db_username and obj.db_password:
                # Password can't be empty or none or we ignore it
                # This *CAN* fail, in which case it throws ConnectionError
                log.debug("Username + Passwd set.  Authing against MongoDB.")
                authenticate_mongodb(obj.db, obj.db_username, obj.db_password)
            collection = obj.db[obj.collection_name]
            obj.create_index(collection)
            obj.collection = collection
            attrs['connection'] = obj.connection
            attrs['db'] = obj.db
            attrs['collection'] = obj.collection
        return type.__new__(cls, name, bases, attrs)        

class MongoDocument(SchemaDocument):
    """
    A MongoDocument brings all mongodb related staff to the SchemaDocument.
    This object defines all methods to deal with a mongod server.
    """
    __metaclass__ = MongoProperties
    
    indexes = []
    belongs_to = {}
    related_to = {}

    db_host = "localhost"
    db_port = 27017
    db_name = None
    collection_name = None

    # Optional auth support
    db_username = None
    db_password = None
    
    # If you are using Pylons, 
    # Connection will be overridden with the Pylons version
    # which sets up and manages the connection 
    _use_pylons = False

    # Support autoreference
    # When enabled, your DB will get NamespaceInjector
    # and AutoReference attached to it, to automatically resolve
    # See the autoreference example in the pymongo driver for more info
    # At the risk of overdocing, *ONLY* when your class has this
    # set to true, will a SchemaDocument subclass be permitted
    # as a valid type
    use_autorefs = False

    authorized_types = SchemaDocument.authorized_types + [
      pymongo.binary.Binary,
      pymongo.objectid.ObjectId,
      pymongo.dbref.DBRef,
      pymongo.code.Code,
      type(re.compile("")),
    ]

    def __init__(self, doc=None, gen_skel=True, db_host=None, db_port=None, db_name=None, collection_name=None, db_username=None, db_password=None):
        """
        :doc: a dictionnary. Usefull to convert a simple dict into a full MongoDocument
        :db_host: overide this if you don't want to use MongoDocument.db_host
        :db_port: overide this if you don't want to use MongoDocument.db_port
        :db_name: overide this if you don't want to use MongoDocument.db_name
        :collection_name: overide this if you don't want to use MongoDocument.collection_name
        :db_username: overide this if you don't want to use MongoDocument.db_username
        :db_password: overide this if you don't want to use MongoDocument.db_password
        :gen_skel: generate the skeleton by filling the doc with empty default values
        """
        self._authorized_types = self.authorized_types[:]
        # If using autorefs, we need another authorized
        # types : type(MongoDocument) (with is MongoProperties)
        if self.use_autorefs:
            self._authorized_types += [MongoProperties]
        super(MongoDocument, self).__init__(doc=doc, gen_skel=gen_skel, gen_auth_types=False)
        # indexing all embed doc if any
        self._dbrefs = {}
        if self.use_autorefs:
            self._make_reference(self, self.structure)
        self._belongs_to = None
        # related feature
        self._from_doc = False
        self._related_loaded = False
        if doc:
            self._from_doc = True
            if self.related_to:
                self.related = RelatedProperties(self.related_to, self)
                self._related_loaded = True
        # Check if a custom connection is pass to the constructor.
        # If yes, build the custom connection
        reset_connection = False
        if db_host is not None:
            self.db_host = db_host
            reset_connection = True
        if db_port is not None:
            self.db_port = db_port
            reset_connection = True
        if db_name is not None:
            self.db_name = db_name
            reset_connection = True
        if collection_name is not None:
            self.collection_name = collection_name
            reset_connection = True
        if db_username is not None:
            self.db_username = db_username
            reset_connection = True
        if db_password is not None:
            self.db_password = db_password
            reset_connection = True
        if reset_connection:
            if hasattr(self, 'connection'):
                if self.db_host != self.connection.host() or\
                  self.db_port != self.connection.port():
                    self.connection = Connection(self.db_host, self.db_port)
            else:
                self.connection = Connection(self.db_host, self.db_port)
            self.db = self.connection[self.db_name]
            self.collection = self.db[self.collection_name]
            MongoDocument.create_index(self.collection)

    def __getattr__(self, key):
        if key in ['collection', 'db'] and not hasattr(self, 'connection'):
            raise ConnectionError('You must specify a db_name and collection_name attribute') 
        try:
            return super(MongoDocument, self).__getattr__(key)
        except Exception, e:
            if key == 'connection':
                raise ConnectionError('You must specify a db_name and collection_name attribute') 
            return super(MongoDocument, self).__getattr__(key)
                

    def validate(self):
        if self.use_autorefs:
            self._make_reference(self, self.structure)
        super(MongoDocument, self).validate()

        
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
            if validate or self.belongs_to:
                self.validate()
        else:
            if not self.skip_validation or self.belongs_to:
                self.validate()
            else:
                if self.use_autorefs:
                    self._make_reference(self, self.structure)
        if '_id' not in self:
            if uuid:
                self['_id'] = unicode("%s-%s" % (self.__class__.__name__, uuid4()))
        if self._belongs_to:
            db_name, full_collection_path, doc_id = self._belongs_to
            if isinstance(doc_id, pymongo.dbref.DBRef):
                doc_id = doc_id.id
            self.connection[db_name]['_mongometa'].insert({
              '_id': '%s-%s' % (full_collection_path, self['_id']),
              'pobj':{'id':doc_id, 'col':full_collection_path},
              'cobj':{'id':self['_id'], 'col':self.collection.full_name()}})
        self._process_custom_type(True, self, self.structure)
        id = self.collection.save(self, safe=safe, *args, **kwargs)
        if not self._from_doc and self.related_to and not self._related_loaded:
            self.related = RelatedProperties(self.related_to, self)
        self._process_custom_type(False, self, self.structure)
        return self

    def delete(self, cascade=False):
        """
        delete the document from the collection from his _id.

        This is equivalent to "self.remove({'_id':self['_id']})"
        """
        if cascade:
            self._delete_cascade(self, self.db_name, self.collection_name, self.connection)
        else:
            self.collection.remove({'_id':self['_id']})

    #
    # class methods, they work on collection
    #
    @classmethod
    def get_collection(cls, db_host=None, db_port=None, db_name=None, collection_name=None, db_username=None, db_password=None, create_index=False):
        """
        return a collection filled by the passed variables. If a variable is None, it the
        value will be filled by the default value (ie set in class attribute)
        
        if create_index is True, the collection will be indexed using the indexes class attribute
        """
        if db_host is None:
            if hasattr(cls, 'connection'):
                db_host = cls.connection.host()
            else:
                db_host = cls.db_host
        if db_port is None:
            if hasattr(cls, 'connection'):
                db_port = cls.connection.port()
            else:
                db_port = cls.db_port
        if db_name is None:
            if cls.db_name:
                db_name = cls.db_name
            else:
                raise ConnectionError('You must specify a db_name')
        if collection_name is None:
            if cls.collection_name:
                collection_name = cls.collection_name
            else:
                raise ConnectionError('You must specify a db_collection')
        if db_username is None:
            db_username = cls.db_username
        if db_password is None:
            db_password = cls.db_password
        if hasattr(cls, 'connection'):
            if db_host != cls.connection.host() or\
              db_port != cls.connection.port():
                connection = Connection(db_host, db_port)
            else:
                connection = cls.connection
        else:
            connection = Connection(db_host, db_port)
        db = connection[db_name]
        collection = db[collection_name]
        if db_username and db_password:
            # Password can't be empty or none or we ignore it
            # This *CAN* fail, in which case it throws ConnectionError
            log.debug("Username + Passwd set.  Authing against MongoDB.")
            authenticate_mongodb(db, db_username, db_password)
        if create_index:
            MongoDocument.create_index(collection)
        return collection

    @classmethod
    def create_index(cls, collection):
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
            collection.ensure_index(fields, unique=unique, ttl=ttl)

    @classmethod
    def get_from_id(cls, id, collection=None):
        """
        return the document wich has the id

        The query is launch against the db and collection of the object.
        """
        if collection is None:
            collection = cls.collection
        bson_obj = collection.find_one({"_id":id})
        if bson_obj:
            return cls(bson_obj)

    @classmethod
    def all(cls, *args, **kwargs):
        """
        return all document wich match the query.
        `all()` takes the same arguments than the the pymongo.collection.find method.

        The query is launch against the db and collection of the object.
        """
        collection = kwargs.pop('collection', None)
        if collection is None:
            collection = cls.collection
        return MongoDocumentCursor(
          collection.find(*args, **kwargs), cls)

    @classmethod
    def fetch(cls, spec=None, fields=None, skip=0, limit=0, collection=None, slave_okay=None, timeout=True, snapshot=False, _sock=None):
        """
        return all document wich match the structure of the object
        `fetch()` takes the same arguments than the the pymongo.collection.find method.

        The query is launch against the db and collection of the object.
        """
        if collection is None:
            collection = cls.collection
        if spec is None:
            spec = {}
        for key in cls.structure:
            if key in spec:
                if isinstance(spec[key], dict):
                    spec[key].update({'$exists':True})
            else:
                spec[key] = {'$exists':True}
        return MongoDocumentCursor(
          collection.find(
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
    def fetch_one(cls, spec=None, fields=None, skip=0, limit=0, collection=None, slave_okay=None, timeout=True, snapshot=False, _sock=None):
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
            collection=collection,
            slave_okay=slave_okay,
            timeout=timeout,
            snapshot=snapshot,
            _sock=_sock)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            doc = bson_obj.next()
            db_name = doc.collection.database().name()
            collection_name = doc.collection.name()
            doc._process_custom_type(True, doc, doc.structure)
            return cls(doc, db_name=db_name, collection_name=collection_name)


    @classmethod
    def group(cls, *args, **kwargs):
        collection = kwargs.pop('collection', None)
        if collection is None:
            collection = cls.collection
        return MongoDocumentCursor(
          collection.group(*args, **kwargs), cls)

    @classmethod
    def one(cls, *args, **kwargs):
        """
        return on document wich match the query.
        `one()` takes the same arguments than the the pymongo.collection.find method.

        If multiple documents are found, raise a MultipleResultsFound exception.
        If no document is found, return None

        The query is launch against the db and collection of the object.
        """
        collection = kwargs.pop('collection', None)
        if collection is None:
            collection = cls.collection
        bson_obj = collection.find(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return cls(bson_obj.next())

    @classmethod
    def remove(cls, *args, **kwargs):
        """
        remove all document wich match the query
        `remove()` takes the same arguments than the the pymongo.collection.remove method.

        The query is launch against the db and collection of the object.
        """
        collection = kwargs.pop('collection', None)
        if collection is None:
            collection = cls.collection
            collection_name = cls.collection_name
            db_name = cls.db_name
            connection = cls.connection
        else:
            collection_name = collection.name()
            db_name = collection.database().name()
            connection = collection.database().connection()
        if kwargs.pop('cascade', None):
            for obj in  collection.find(*args, **kwargs):
                cls._delete_cascade(obj, db_name, collection_name, connection)
        else:
            return collection.remove(*args, **kwargs)

    def to_json_type(self):
        """
        convert all document field into json type
        and return the new converted object
        """
        def _convert_to_json(struct, doc):
            """
            convert all datetime to a timestamp from epoch
            """
            for key in struct:
                if isinstance(struct[key], datetime.datetime):
                    struct[key] = totimestamp(struct[key])
                elif isinstance(struct[key], pymongo.dbref.DBRef):
                    struct[key] = doc.get_from_id(struct[key].id)
                elif isinstance(struct[key], dict):
                    _convert_to_json(struct[key], doc)
                elif isinstance(struct[key], list) and len(struct[key]):
                    if isinstance(struct[key][0], dict):
                        for obj in struct[key]:
                            _convert_to_json(obj, doc)
                    elif isinstance(struct[key][0], datetime.datetime):
                        struct[key] = [totimestamp(obj) for obj in struct[key]]
        # we don't want to touch our document so we create another object
        from copy import deepcopy
        self._process_custom_type(True, self, self.structure)
        # pymongo's collection and db can't be deepcopied
        db = self.db
        collection = self.collection
        if hasattr(self, 'db'):
            self.db = None
        if hasattr(self, 'collection'):
            self.collection = None
        obj = deepcopy(self)
        if hasattr(self, 'db'):
            self.db = db
        if hasattr(self, 'collection'):
            self.collection = collection
        self._process_custom_type(False, self, self.structure)
        _convert_to_json(obj, obj)
        return obj

    def to_json(self):
        """
        convert the document into a json string and return it
        """
        try:
            import anyjson
        except ImportError:
            raise ImportError("can't import anyjson. Please install it before continuing.")
        return anyjson.serialize(self.to_json_type())

    @classmethod
    def from_json(cls, json):
        """
        convert a json string and return a SchemaDocument
        """
        def _convert_to_python(doc, struct, path = "", root_path=""):
            for key in struct:
                if type(key) is type:
                    new_key = "$%s" % key.__name__
                else:
                    new_key = key
                new_path = ".".join([path, new_key]).strip('.')
                if isinstance(struct[key], dict):
                    if doc: # we don't need to process an empty doc
                        if type(key) is type:
                            for doc_key in doc: # process type's key such {unicode:int}...
                                _convert_to_python(doc[doc_key], struct[key], new_path, root_path)
                        else:
                            if key in doc: # we don't care about missing fields
                                _convert_to_python(doc[key], struct[key], new_path, root_path)
                elif type(struct[key]) is list:
                    if struct[key]:
                        if struct[key][0] is datetime.datetime:
                            l_objs = []
                            for obj in doc[key]:
                                obj = fromtimestamp(obj)
                                l_objs.append(obj)
                            doc[key] = l_objs
                        elif isinstance(struct[key][0], MongoProperties):
                            l_objs = []
                            for obj in doc[key]:
                                obj = struct[key](obj)
                                l_objs.append(obj)
                            doc[key] = l_objs
                        elif isinstance(struct[key][0], dict):
                            if doc[key]:
                                for obj in doc[key]:
                                    _convert_to_python(obj, struct[key][0], new_path, root_path)
                else:
                    if struct[key] is datetime.datetime:
                            doc[key] = fromtimestamp(doc[key])
                    elif isinstance(struct[key], MongoProperties):
                        doc[key] = struct[key](doc[key])
        try:
            import anyjson
        except ImportError:
            raise ImportError("can't import anyjson. Please install it before continuing.")
        obj = anyjson.deserialize(json)
        _convert_to_python(obj, cls.structure)
        return obj
 
    #
    # end of public API
    #
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
        if self.indexes:
            for index in self.indexes:
                if 'fields' not in index:
                    raise BadIndexError("'fields' key must be specify in indexes")
                for key, value in index.iteritems():
                    if key not in ['fields', 'unique', 'ttl']:
                        raise BadIndexError("%s is unknown key for indexes" % key)
                    if key == "fields":
                        if isinstance(value, dict):
                            for field, direction in value.iteritems():
                                if not direction in [1, -1]:
                                    raise BadIndexError("index direction must be 1 or -1. Got %s" % direction)
                                if field not in self._namespaces:
                                    raise ValueError("Error in indexes: can't"
                                      " find %s in structure" % field )
                        elif isinstance(value, basestring):
                            if value not in self._namespaces:
                                raise ValueError("Error in indexes: can't"
                                  " find %s in structure" % value )
                        elif isinstance(value, list):
                            for field in value:
                                if field not in self._namespaces:
                                    raise ValueError("Error in indexes: can't"
                                      " find %s in structure" % field )
                    elif key == "ttl":
                        assert isinstance(value, int)
                    else:
                        assert value in [False, True], value
        if self.belongs_to:
            if not len(self.belongs_to) == 1:
                raise ValueError("belongs_to must contain only one item")
            if not issubclass(self.belongs_to.values()[0], MongoDocument):
                raise ValueError("self.belongs_to['%s'] must have a MongoDocument subclass (got %s instead)" % (
                  self.belongs_to.keys()[0], self.belongs_to.values()[0]))

    def _validate_doc(self, doc, struct, path = ""):
        """
        check it doc field types match the doc field structure
        """
        if path in self.belongs_to:
            if not self._belongs_to:
                db_name = self.belongs_to[path].db_name
                collection_name = self.belongs_to[path].collection_name
                full_collection_path = "%s.%s" % (db_name, collection_name)
                self._belongs_to = (db_name, full_collection_path, doc)
        super(MongoDocument, self)._validate_doc(doc, struct, path)

    def _make_reference(self, doc, struct, path=""):
        """
        * wrap all MongoDocument with the CustomType "R()"
        * create the list of Reference in self._dbrefs
        * track the embed doc changes and save it when self.save() is called
        """
        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], MongoProperties) or isinstance(struct[key], R):
                # if struct[key] is a MongoDocument, so we have to convert it into the
                # CustomType : R
                if not isinstance(struct[key], R):
                    struct[key] = R(struct[key])
                # be sure that we have an instance of MongoDocument
                if not isinstance(doc[key], struct[key]._doc) and doc[key] is not None:
                    raise SchemaTypeError(
                      "%s must be an instance of MongoDocument not %s" % (
                        new_path, type(doc[key]).__name__))
                # validate the embed doc
                if not self.skip_validation and doc[key] is not None:
                    doc[key].validate()
                # if we didn't index the embed obj yet, well, we do it
                if new_path not in self._dbrefs:
                    self._dbrefs[new_path] = doc[key]
                else:
                    # if the embed doc indexed was None but not the new embed one,
                    # we update the index
                    if self._dbrefs[new_path] is None and doc[key] is not None:
                        self._dbrefs[new_path] = doc[key]
                    # if the embed obj is already indexed, we check is the
                    # one we get has not changed. If so, we save the embed
                    # obj and update the reference
                    elif self._dbrefs[new_path] != doc[key] and doc[key] is not None:
                        doc[key].save()
                        self._dbrefs[new_path].update(doc[key])
            elif isinstance(struct[key], dict):
                #
                # if the dict is still empty into the document we build
                # it with None values
                #
                if len(struct[key]) and\
                  not [i for i in struct[key].keys() if type(i) is type]: 
                    if key in doc:
                        self._make_reference(doc[key], struct[key], new_path)
                else:# case {unicode:int}
                    pass
            elif isinstance(struct[key], list) and len(struct[key]):
                if isinstance( struct[key][0], MongoProperties) or isinstance(struct[key][0], R):
                    if not isinstance(struct[key][0], R):
                        struct[key][0] = R(struct[key][0])
                    l_objs = []
                    for no, obj in enumerate(doc[key]):
                        if not isinstance(obj, struct[key][0]._doc) and obj is not None:
                            raise SchemaTypeError(
                              "%s must be an instance of MongoDocument not %s" % (
                                new_path, type(obj).__name__))
                        full_new_path = "%s.%s" % (new_path, no)
                        # validate the embed doc
                        if not self.skip_validation:
                            obj.validate()
                        # if we didn't index the embed obj yet, well, we do it
                        if full_new_path not in self._dbrefs:
                            self._dbrefs[full_new_path] = obj
                        else:
                            # if the embed doc indexed was None but not the new embed one,
                            # we update the index
                            if self._dbrefs[full_new_path] is None:
                                self._dbrefs[full_new_path] = obj
                            # if the embed obj is already indexed, we check is the
                            # one we get has not changed. If so, we save the embed
                            # obj and update the reference
                            elif self._dbrefs[full_new_path] != obj:
                                obj.save()
                                self._dbrefs[full_new_path].update(obj)
                        l_objs.append(obj)
                    doc[key] = l_objs

class MongoPylonsDocument(MongoDocument):
    """Lazy helper base class to inherit from if you are
    sure you will always live in / require the pylons evironment.
    Keep in mind if you need CLI testing, "paster shell" will allow 
    you to test within a pylons environment (via an ipython shell)"""
    _use_pylons = True

class R(CustomType):
    """ CustomType to deal with autorefs documents """
    mongo_type = pymongo.dbref.DBRef
    python_type = MongoDocument

    def __init__(self, doc):
        super(R, self).__init__()
        self._doc = doc
    
    def to_bson(self, value):
        if value is not None:
            return pymongo.dbref.DBRef(collection=value.collection.name(), id=value['_id'])
        
    def to_python(self, value):
        if value is not None:
            col = self._doc.get_collection(collection_name=value.collection)
            doc = col.find_one({'_id':value.id})
            if doc is None:
                raise AutoReferenceError('Something wrong append. You probably change'
                  ' your object when passing it as a value to an autorefs enable document.\n'
                  'A document with id "%s" is not saved in the database but was giving as'
                  ' a reference to a %s document' % (value.id, self._doc.__name__))
            return self._doc(doc, collection_name=value.collection)


