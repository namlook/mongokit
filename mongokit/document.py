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

from mongokit import SchemaDocument, MongoDocumentCursor, SchemaProperties, AutoReferenceError
from mongokit.mongo_exceptions import *
from mongokit.schema_document import STRUCTURE_KEYWORDS, CustomType, SchemaTypeError
import pymongo
from pymongo.bson import BSON
import re
from copy import deepcopy
from uuid import uuid4
import logging

STRUCTURE_KEYWORDS += ['_id', '_ns', '_revision']

log = logging.getLogger(__name__)

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
                desc['query'] = fuc(pymongo.dbref.DBRef(database=self._doc.db.name, collection=self._doc.collection.name, id=self._doc['_id']))
            else:
                desc['query'] = fuc(self._doc['_id'])
            methods = {
              'query':self._descriptor[key]['query'],
              '__call__':call_func,
              'obj':self._descriptor[key]['class'],
            }
            setattr(self, key, type(key, (object,), methods)())

class Document(SchemaDocument):

    belongs_to = {}
    related_to = {}
    skip_validation = False
    use_autorefs = False
    indexes = []

    authorized_types = SchemaDocument.authorized_types + [
      pymongo.binary.Binary,
      pymongo.objectid.ObjectId,
      pymongo.dbref.DBRef,
      pymongo.code.Code,
      type(re.compile("")),
    ]

    def __init__(self, doc=None, gen_skel=True, collection=None):
        self._authorized_types = self.authorized_types[:]
        # If using autorefs, we need another authorized
        if self.use_autorefs:
            self._authorized_types += [Document, SchemaProperties]
        super(Document, self).__init__(doc=doc, gen_skel=gen_skel, gen_auth_types=False)
        # collection
        self.collection = collection
        if collection:
            self.db = collection.database
            self.connection = self.db.connection
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
        self._non_callable = False

    def validate(self):
        if self.use_autorefs:
            self._make_reference(self, self.structure)
        if self.get_size() > 3999999:
            raise MaxDocumentSizeError("The document size is too big, documents lower than 4Mb is allowed (got %s bytes)" % self.get_size())
        super(Document, self).validate()

    def get_size(self):
        """
        return the size of the underlying bson object
        """
        return len(BSON.from_dict(self))

    def find(self, *args, **kwargs):
        return MongoDocumentCursor(
          self.collection.find(*args, **kwargs), cls=self.__class__, wrap=True)

    def find_one(self, *args, **kwargs):
        bson_obj = self.collection.find(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return self.__class__(doc=bson_obj.next(), collection=self.collection)

    def get_from_id(self, id):
        """
        return the document wich has the id
        """
        return self.find_one({"_id":id})

    def fetch(self, spec=None, fields=None, skip=0, limit=0, slave_okay=None, timeout=True, snapshot=False, _sock=None, wrap=True):
        """
        return all document wich match the structure of the object
        `fetch()` takes the same arguments than the the pymongo.collection.find method.

        The query is launch against the db and collection of the object.
        """
        if spec is None:
            spec = {}
        for key in self.structure:
            if key in spec:
                if isinstance(spec[key], dict):
                    spec[key].update({'$exists':True})
            else:
                spec[key] = {'$exists':True}
        return MongoDocumentCursor(
          self.collection.find(
            spec=spec, 
            fields=fields, 
            skip=skip,
            limit=limit,
            slave_okay=slave_okay,
            timeout=timeout,
            snapshot=snapshot,
            _sock=_sock,),
          cls=self.__class__, wrap=wrap)

    def fetch_one(self, spec=None, fields=None, skip=0, limit=0, slave_okay=None, timeout=True, snapshot=False, _sock=None):
        """
        return one document wich match the structure of the object
        `fetch_one()` takes the same arguments than the the pymongo.collection.find method.

        If multiple documents are found, raise a MultipleResultsFound exception.
        If no document is found, return None

        The query is launch against the db and collection of the object.
        """
        bson_obj = self.fetch(
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
            return bson_obj.next()

    def get_dbref(self):
        assert '_id' in self, "You must specify an '_id' for using this method"
        return pymongo.dbref.DBRef(database=self.db.name, collection=self.collection.name, id=self['_id'])

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
              'cobj':{'id':self['_id'], 'col':self.collection.full_name}})
        self._process_custom_type(True, self, self.structure)
        id = self.collection.save(self, safe=safe, *args, **kwargs)
        if not self._from_doc and self.related_to and not self._related_loaded:
            self.related = RelatedProperties(self.related_to, self)
        self._process_custom_type(False, self, self.structure)
        return self

    def delete(self):
        """
        delete the document from the collection from his _id.

        This is equivalent to "self.remove({'_id':self['_id']})"
        """
        self.collection.remove({'_id':self['_id']})

    def generate_index(self):
        # creating index if needed
        for index in self.indexes:
            unique = False
            if 'unique' in index.keys():
                unique = index['unique']
            ttl = 300
            if 'ttl' in index.keys():
                ttl = index['ttl']
            if isinstance(index['fields'], tuple):
                fields = [index['fields']]
            elif hasattr(index['fields'], '__iter__'):
                if isinstance(index['fields'][0], tuple):
                    fields = [(name, direction) for name, direction in index['fields']]
                else:
                    fields = [(name, 1) for name in index['fields']]
            else:
                fields = index['fields']
            log.debug('Creating index for %s' % str(index['fields']))
            self.collection.ensure_index(fields, unique=unique, ttl=ttl)

    #
    # End of public API
    #

    def __call__(self, doc=None, gen_skel=True):
        if self._non_callable:
            raise TypeError("'%s' is not callable" % self.__class__.__name__)
        obj = self.__class__(doc=doc, gen_skel=gen_skel, collection=self.collection)
        obj._non_callable = True
        return obj

    def _validate_descriptors(self):
        super(Document, self)._validate_descriptors()
        if self.indexes:
            for index in self.indexes:
                if 'fields' not in index:
                    raise BadIndexError("'fields' key must be specify in indexes")
                for key, value in index.iteritems():
                    if key not in ['fields', 'unique', 'ttl']:
                        raise BadIndexError("%s is unknown key for indexes" % key)
                    if key == "fields":
                        if isinstance(value, basestring):
                            if value not in self._namespaces and value not in STRUCTURE_KEYWORDS:
                                raise ValueError("Error in indexes: can't"
                                  " find %s in structure" % value )
                        elif isinstance(value, tuple):
                            if len(value) != 2:
                                raise BadIndexError("Error in indexes: a tuple must contain "
                                  "only two value the field name and the direction")
                            if not isinstance(value[1], int):
                                raise BadIndexError("Error in %s, the direction must be int (got %s instead)" % (value[0], type(value[1])))
                            if not isinstance(value[0], basestring):
                                raise BadIndexError("Error in %s, the field name must be string (got %s instead)" % (value[0], type(value[0])))
                            if value[0] not in self._namespaces and value[0] not in STRUCTURE_KEYWORDS:
                                raise ValueError("Error in indexes: can't"
                                  " find %s in structure" % value )
                            if not value[1] in [1, -1]:
                                raise BadIndexError("index direction must be 1 or -1. Got %s" % value[1])
                        elif isinstance(value, list):
                            for val in value:
                                if isinstance(val, tuple):
                                    for field, direction in value:
                                        if field not in self._namespaces and field not in STRUCTURE_KEYWORDS:
                                            raise ValueError("Error in indexes: can't"
                                              " find %s in structure" % field )
                                        if not direction in [1, -1]:
                                            raise BadIndexError("index direction must be 1 or -1. Got %s" % direction)
                                else:
                                    if val not in self._namespaces and val not in STRUCTURE_KEYWORDS:
                                        raise ValueError("Error in indexes: can't"
                                          " find %s in structure" % val )
                        else:
                            raise BadIndexError("fields must be a string, a tuple or a list of tuple (got %s instead)" % type(value))
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

    def __hash__(self):
        if '_id' in self:
            value = self['_id']
            if value == -1:
                value == -2
            return value.__hash__()
        else:
            raise TypeError("A Document is not hashable if it is not saved. Save the document before hashing it")

    def __deepcopy__(self, memo={}):
        obj = self.__class__(doc=deepcopy(dict(self), memo), gen_skel=False, collection=self.collection)
        obj.__dict__ = self.__dict__.copy()
        return obj

    def __getattribute__(self, key):
        if key in ['collection', 'db', 'connection']:
            if self.__dict__[key] is None:
                raise ConnectionError('No collection found') 
        return super(Document, self).__getattribute__(key)
 
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
            if isinstance(struct[key], SchemaProperties) or isinstance(struct[key], R):
                # if struct[key] is a MongoDocument, so we have to convert it into the
                # CustomType : R
                if not isinstance(struct[key], R):
                    struct[key] = R(struct[key], self.connection)
                # be sure that we have an instance of MongoDocument
                if not isinstance(doc[key], struct[key]._doc) and doc[key] is not None:
                    raise SchemaTypeError(
                      "%s must be an instance of Document not %s" % (
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
                if isinstance( struct[key][0], SchemaProperties) or isinstance(struct[key][0], R):
                    if not isinstance(struct[key][0], R):
                        struct[key][0] = R(struct[key][0], self.connection)
                    l_objs = []
                    for no, obj in enumerate(doc[key]):
                        if not isinstance(obj, struct[key][0]._doc) and obj is not None:
                            raise SchemaTypeError(
                              "%s must be an instance of Document not %s" % (
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

    # deprecated
    def all(self, *args, **kwargs):
        return self.find(*args, **kwargs)

class R(CustomType):
    """ CustomType to deal with autorefs documents """
    mongo_type = pymongo.dbref.DBRef
    python_type = Document

    def __init__(self, doc, connection):
        super(R, self).__init__()
        self._doc = doc
        self.connection = connection
    
    def to_bson(self, value):
        if value is not None:
            return pymongo.dbref.DBRef(database=value.db.name, collection=value.collection.name, id=value['_id'])
        
    def to_python(self, value):
        if value is not None:
            col = self.connection[value.database][value.collection]#get_collection(collection_name=value.collection)
            doc = col.find_one({'_id':value.id})
            if doc is None:
                raise AutoReferenceError('Something wrong append. You probably change'
                  ' your object when passing it as a value to an autorefs enable document.\n'
                  'A document with id "%s" is not saved in the database but was giving as'
                  ' a reference to a %s document' % (value.id, self._doc.__name__))
            return self._doc(doc, collection=col)#, collection=self._doc.db[value.collection])#collection_name=value.collection)


