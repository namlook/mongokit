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

from uuid import uuid4

log = logging.getLogger(__name__)

from operators import MongokitOperator, IS

class CustomType(object): pass

authorized_types = [type(None), bool, int, float, unicode, list, dict,
  datetime.datetime, 
  pymongo.binary.Binary,
  pymongo.objectid.ObjectId,
  pymongo.dbref.DBRef,
  pymongo.code.Code,
  type(re.compile("")),
  CustomType,
]

__all__ = ['DotedDict', 'MongoDocument', 'VersionnedDocument', 'CustomType']

# field wich does not need to be declared into the structure
STRUCTURE_KEYWORDS = ['_id', '_ns', '_revision']

class DotedDict(dict):
    def __setattr__(self, key, value):
        if key in self:
            self[key] = value
        else:
           dict.__setattr__(self, key, value) 
    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
           dict.__getattribute__(self, key)

class SchemaProperties(type):
    def __new__(cls, name, bases, attrs):
        attrs['_protected_field_names'] = set(['_protected_field_names', '_namespaces', '_required_namespace'])
        for base in bases:
            parent = base.__mro__[0]
            if hasattr(parent, "structure") and\
              not parent.__module__.startswith('mongokit.document'):
                parent = parent()
                if parent.structure:
                    if 'structure' not in attrs and parent.structure:
                        attrs['structure'] = parent.structure
                    else:
                        obj_structure = attrs.get('structure', {}).copy()
                        attrs['structure'] = parent.structure.copy()
                        attrs['structure'].update(obj_structure)
                if parent.required_fields:
                    attrs['required_fields'] = list(set(
                      attrs.get('required_fields', [])+parent.required_fields))
                if parent.default_values:
                    obj_default_values = attrs.get('default_values', {}).copy()
                    attrs['default_values'] = parent.default_values.copy()
                    attrs['default_values'].update(obj_default_values)
                if parent.validators:
                    obj_validators = attrs.get('validators', {}).copy()
                    attrs['validators'] = parent.validators.copy()
                    attrs['validators'].update(obj_validators)
        for mro in bases[0].__mro__:
            attrs['_protected_field_names'] = attrs['_protected_field_names'].union(list(mro.__dict__))
        attrs['_protected_field_names'] = list(attrs['_protected_field_names'])
        return type.__new__(cls, name, bases, attrs)        


class MongoDocument(dict):
    """
    A MongoDocument is dictionnary with a building structured schema
    The validate method will check that the document match the underling
    structure. A structure must be specify in each MongoDocument.

    >>> class TestDoc(MongoDocument):
    ...     structure = {
    ...         "foo":unicode,
    ...         "bar":int,
    ...         "nested":{
    ...            "bla":float}} 

    `unicode`, `int`, `float` are python types listed in `mongokit.authorized_types`.
    
    >>> doc = TestDoc()
    >>> doc
    {'foo': None, 'bar': None, 'nested': {'bla': None}}
    
    A MongoDocument works just like dict:

    >>> doc['bar'] = 3
    >>> doc['foo'] = "test"

    We can describe fields as required with the required attribute:

    >>> TestDoc.required_fields = ['bar', 'nested.bla']
    >>> doc = TestDoc()
    >>> doc['bar'] = 2

    Validation is made with the `validate()` methode:

    >>> doc.validate()  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ...
    RequireFieldError: nested.bla is required


    Default values can be set by using the attribute default_values :

    >>> TestDoc.default_values = {"bar":3, "nested.bla":2.0}
    >>> doc = TestDoc()
    >>> doc
    {'foo': None, 'bar': 3, 'nested': {'bla': 2.0}}
    >>> doc.validate()

    Validators can be added in order to validate some values :

    >>> TestDoc.validators = {"bar":lambda x: x>0, "nested.bla": lambda x: x<0}
    >>> doc = TestDoc()
    >>> doc['bar'] = 3
    >>> doc['nested']['bla'] = 2.0
    >>> doc.validate()
    Traceback (most recent call last):
    ...
    ValidationError: nested.bla does not pass the validator <lambda>

    If you want to use the dot notation (ala json), you must set the
    `use_dot_notation` attribute to True:

    >>> class TestDotNotation(MongoDocument):
    ...     structure = {
    ...         "foo":{ "bar":unicode}
    ...     }
    ...     use_dot_notation=True

    >>> doc = TestDotNotation()
    >>> doc.foo.bar = u"bla"
    >>> doc
    {"foo":{"bar":u"bla}}
    """
    __metaclass__ = SchemaProperties
    
    structure = None
    required_fields = []
    default_values = {}
    validators = {}
    indexes = []
    belong_to = {}

    skip_validation = False
    
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
        
    # If you want to use the dot notation, set this to True:
    use_dot_notation = False

    # Support autoreference
    # When enabled, your DB will get NamespaceInjector
    # and AutoReference attached to it, to automatically resolve
    # See the autoreference example in the pymongo driver for more info
    # At the risk of overdocing, *ONLY* when your class has this
    # set to true, will a MongoDocument subclass be permitted
    # as a valid type
    use_autorefs = False

    custom_types = {}

    def __init__(self, doc=None, gen_skel=True):
        """
        doc : a dictionnary
        gen_skel : if True, generate automaticly the skeleton of the doc
            filled with NoneType each time validate() is called. Note that
            if doc is not {}, gen_skel is always False. If gen_skel is False,
            default_values cannot be filled.
        """
        # init
        if doc is None:
            doc = {}
        if self.structure is None:
            raise StructureError("your document must have a structure defined")
        if not self.skip_validation: 
            self._validate_structure()
            self._namespaces = list(self.__walk_dict(self.structure))
            self._validate_descriptors()
        for k, v in doc.iteritems():
            self[k] = v
        if doc:
            gen_skel = False
        if gen_skel:
            self.generate_skeleton()
            self._set_default_fields(self, self.structure)
        if self.custom_types:
            self._process_custom_type(False, self, self.structure)
        ## building required fields namespace
        if not self.skip_validation:
            self._required_namespace = set([])
            for rf in self.required_fields:
                splited_rf = rf.split('.')
                for index in range(len(splited_rf)):
                    self._required_namespace.add(".".join(splited_rf[:index+1]))
        self._belong_to = None
        
    def generate_skeleton(self):
        """
        validate and generate the skeleton of the document
        from the structure (unknown values are set to None)
        """
        self.__generate_skeleton(self, self.structure)

    def validate(self):
        """
        validate the document.

        This method will verify if :
          * the doc follow the structure,
          * all required fields are filled
        
        Additionnaly, this method will process all
        validators.
        
        """
        if self.custom_types:
            self._process_custom_type(True, self, self.structure)
        self._validate_doc(self, self.structure)
        if self.required_fields:
            self._validate_required(self, self.structure)
        if self.validators:
            self._process_validators(self, self.structure)
        if self.custom_types:
            self._process_custom_type(False, self, self.structure)

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
            if isinstance(index['fields'], list):
                fields = [(i, 1) for i in index['fields']]
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

    #
    # Public API end
    #
 
    def __walk_dict(self, dic):
        # thanks jean_b for the patch
        for key, value in dic.items():
            if isinstance(value, dict) and len(value):
                if type(key) is type:
                    yield '$%s' % key.__name__
                else:
                    yield key
                for child_key in self.__walk_dict(value):
                    if type(key) is type:
                        new_key = "$%s" % key.__name__
                    else:
                        new_key = key
                    if type(child_key) is type:
                        new_child_key = "$%s" % child_key.__name__
                    else:
                        new_child_key = child_key
                    yield '%s.%s' % (new_key, new_child_key)
            elif type(key) is type:
                yield '$%s' % key.__name__
            elif isinstance(value, list) and len(value):
                if isinstance(value[0], dict):
                    for child_key in self.__walk_dict(value[0]):
                        if type(key) is type:
                            new_key = "$%s" % key.__name__
                        else:
                            new_key = key
                        if type(child_key) is type:
                            new_child_key = "$%s" % child_key.__name__
                        else:
                            new_child_key = child_key
                        yield '%s.%s' % (new_key, new_child_key)
                else:
                    if type(key) is not type:
                        yield key
                    else:
                        yield ""
            else:
                if type(key) is not type:
                    yield key
                else:
                    yield ""

    def _validate_descriptors(self):
        for dv in self.default_values:
            if dv not in self._namespaces:
                raise ValueError(
                  "Error in default_values: can't find %s in structure" % dv )
        for required in self.required_fields:
            if required not in self._namespaces:
                raise ValueError( "Error in required_fields: "
                  "can't find %s in structure" % required )
        for validator in self.validators:
            if validator not in self._namespaces:
                raise ValueError("Error in validators: can't"
                  "find %s in structure" % validator )
        for custom_type in self.custom_types:
            if custom_type not in self._namespaces:
                raise ValueError("Error in custom_types: can't"
                  "find %s in structure" % custom_type )
        if self.belong_to:
            if not len(self.belong_to) == 1:
                raise ValueError("belong_to must contain only one item")
            if not issubclass(self.belong_to.values()[0], MongoDocument):
                raise ValueError("self.belong_to['%s'] must have a MongoDocument subclass (got %s instead)" % (
                  self.belong_to.keys()[0], self.belong_to.values()[0]))
        for validator in self.validators:
            if validator not in self._namespaces:
                raise ValueError("Error in validators: can't"
                  "find %s in structure" % validator )
        

    def _validate_structure(self):
        ##############
        def __validate_structure( struct):
            if type(struct) is type:
                if struct not in authorized_types:
                    raise StructureError("%s is not an authorized_types" % key)
            elif isinstance(struct, dict):
                for key in struct:
                    if isinstance(key, basestring):
                        if "." in key: raise BadKeyError(
                          "%s must not contain '.'" % key)
                        if key.startswith('$'): raise BadKeyError(
                          "%s must not start with '$'" % key)
                    elif type(key) is type:
                        if not key in authorized_types:
                            raise AuthorizedTypeError(
                              "%s is not an authorized type" % key)
                    else:
                        raise StructureError(
                          "%s must be a basestring or a type" % key)
                    if isinstance(struct[key], dict):
                        __validate_structure(struct[key])
                    elif isinstance(struct[key], list):
                        __validate_structure(struct[key])
                    elif isinstance(struct[key], MongokitOperator):
                        __validate_structure(struct[key])
                    elif hasattr(struct[key], 'structure'):
                        if not issubclass(struct[key], MongoDocument):
                            raise StructureError(
                              "%s is not an authorized type" % struct[key])
                        elif issubclass(struct[key], MongoDocument) and not self.use_autorefs:
                            raise StructureError(
                              "%s seems to be a embeded document wich is not permitted.\n"
                              "To be able to use autoreference, set the"
                              "'use_autorefs' as True" % (key)
                            )
                    elif (struct[key] not in authorized_types):
                        ok = False
                        for auth_type in authorized_types:
                            if issubclass(struct[key], auth_type):
                                ok = True
                        if not ok:
                            raise StructureError(
                              "%s is not an authorized type" % struct[key])
            elif isinstance(struct, list):
                for item in struct:
                    __validate_structure(item)
            elif isinstance(struct, MongokitOperator):
                if isinstance(struct, IS):
                    for operand in struct:
                        if type(operand) not in authorized_types:
                            raise StructureError(
                              "%s in %s is not an authorized type" % (operand, struct))
                else:
                    for operand in struct:
                        if operand not in authorized_types: 
                            raise StructureError(
                              "%s in %s is not an authorized type" % (operand, struct))
            else:
                raise StructureError("%s is not an authorized_types" % key)
        #################
        if self.structure is None:
            raise StructureError("self.structure must not be None")
        if not isinstance(self.structure, dict):
            raise StructureError("self.structure must be a dict instance")
        if self.required_fields:
            if len(self.required_fields) != len(set(self.required_fields)):
                raise DuplicateRequiredError(
                  "duplicate required_fields : %s" % self.required_fields)
        __validate_structure(self.structure)
                    
    def _validate_doc(self, doc, struct, path = ""):
        if path in self.belong_to:
            if not self._belong_to:
                db_name = self.belong_to[path].db_name
                collection_name = self.belong_to[path].collection_name
                full_collection_path = "%s.%s" % (db_name, collection_name)
                self._belong_to = (db_name, full_collection_path, doc)
        if type(struct) is type or struct is None:
            if struct is None:
                if type(doc) not in authorized_types:
                    raise AuthorizedTypeError(
                      "%s is not an authorized types" % type(doc).__name__)
            elif not isinstance(doc, struct) and doc is not None:
                raise SchemaTypeError(
                  "%s must be an instance of %s not %s" % (
                    path, struct.__name__, type(doc).__name__))
        elif isinstance(struct, SchemaProperties): #DBRef
            if not isinstance(doc, struct) and doc is not None:
                raise SchemaTypeError(
                  "%s must be an instance of %s not %s" % (
                    path, struct.__name__, type(doc).__name__))
            if doc is not None:
                doc._validate_doc(doc, doc.structure, path=path)
                doc._validate_required(doc, doc.structure, path="", root_path=path)
                doc._process_validators(doc, doc.structure, path=path)
        elif isinstance(struct, MongokitOperator):
            if not struct.validate(doc) and doc is not None:
                if isinstance(struct, IS):
                    raise SchemaTypeError(
                      "%s must be in %s not %s" % (
                        path, struct._operands, doc))
                else:
                    raise SchemaTypeError(
                      "%s must be an instance of %s not %s" % (
                        path, struct, type(doc).__name__))
        elif isinstance(struct, dict):
            if not isinstance(doc, type(struct)):
                raise SchemaTypeError(
                  "%s must be an instance of %s not %s" %(
                    path, type(struct).__name__, type(doc).__name__))
            if len(doc) != len(struct):
                struct_doc_diff = list(set(struct).difference(set(doc)))
                if struct_doc_diff:
                    for field in struct_doc_diff:
                        if type(field) is not type:
                            raise StructureError(
                              "missed fields : %s" % struct_doc_diff )
                else:
                    struct_struct_diff = list(set(doc).difference(set(struct)))
                    if not sum( 1 for s in struct_struct_diff if s in STRUCTURE_KEYWORDS):
                        raise StructureError( 
                          "unknown fields : %s" % struct_struct_diff)
            for key in struct:
                if type(key) is type:
                    new_key = "$%s" % key.__name__
                else:
                    new_key = key
                new_path = ".".join([path, new_key]).strip('.')
                if new_key.split('.')[-1].startswith("$"):
                    for doc_key in doc:
                        if not isinstance(doc_key, key):
                            raise SchemaTypeError(
                              "key of %s must be an instance of %s not %s" % (
                                path, key.__name__, type(doc_key).__name__))
                        self._validate_doc(doc[doc_key], struct[key], new_path)
                else:
                    self._validate_doc(doc[key], struct[key],  new_path)
        elif isinstance(struct, list):
            if not isinstance(doc, list):
                raise SchemaTypeError(
                  "%s must be an instance of list not %s" % (
                    path, type(doc).__name__))
            if not len(struct):
                struct = None
            else:
                struct = struct[0]
            for obj in doc:
                self._validate_doc(obj, struct, path)

    def _process_validators(self, doc, struct, path = ""):
        #################################################
        def __processval( self, new_path, doc, key ):
            #
            # check that the value pass througt the validator process
            #
            if new_path in self.validators and doc[key] is not None:
                if not hasattr(self.validators[new_path], "__iter__"):
                    validators = [self.validators[new_path]]
                else:
                    validators = self.validators[new_path]
                for validator in validators:
                    if not validator(doc[key]):
                        raise ValidationError(
                          "%s does not pass the validator %s" % (
                            new_path, validator.__name__))
        #################################################
        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict):
                #
                # if the dict is still empty into the document
                # we build it with None values
                #
                if type(key) is not type and key not in doc:
                    __processval(self, new_path, doc)
                elif type(key) is type:
                    for doc_key in doc:
                        self._process_validators(
                          doc[doc_key], struct[key], new_path)
                else:
                    self._process_validators(doc[key], struct[key], new_path)
            #
            # If the struct is a list, we have to validate all values into it
            #
            elif type(struct[key]) is list:
                #
                # check if the list must not be null
                #
                if not key in doc:
                    __processval(self, new_path, doc, key)
                elif not len(doc[key]):
                    __processval(self, new_path, doc, key)
            #
            # It is not a dict nor a list but a simple key:value
            #
            else:
                #
                # check if the value must not be null
                #
                __processval(self, new_path, doc, key)

    def _process_custom_type(self, to_bson, doc, struct, path=""):
        """
        if to_bson is True, then use the "to_bson" fonction from CustomType
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
            if isinstance(struct[key], dict):
                #
                # if the dict is still empty into the document we build
                # it with None values
                #
                if len(struct[key]) and\
                  not [i for i in struct[key].keys() if type(i) is type]: 
                    if key in doc:
                        self._process_custom_type(to_bson, doc[key], struct[key], new_path)
                else:# case {unicode:int}
                    pass
            elif isinstance(struct[key], list) and len(struct[key]):
                if isinstance( struct[key][0], dict):
                    for obj in doc[key]:
                        self._process_custom_type(to_bson=to_bson, doc=obj, struct=struct[key][0], path=new_path)
            else:
                if new_path in self.custom_types:
                    Custom_Type = self.custom_types[new_path]
                    ct = Custom_Type()
                    if to_bson:
                        doc[key] = ct.to_bson(doc[key])
                    else:
                        doc[key] = ct.to_python(doc[key])

            
    def _set_default_fields(self, doc, struct, path = ""):
        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # default_values :
            # if the value is None, check if a default value exist.
            # if exists, and it is a function then call it otherwise,
            # juste feed it
            #
            if type(key) is not type:
                if doc[key] is None and new_path in self.default_values:
                    new_value = self.default_values[new_path]
                    if callable(new_value):
                        doc[key] = new_value()
                    else:
                        doc[key] = new_value
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict):
                #
                # if the dict is still empty into the document we build
                # it with None values
                #
                if len(struct[key]) and\
                  not [i for i in struct[key].keys() if type(i) is type]:
                    self._set_default_fields(doc[key], struct[key], new_path)
                else:
                    if new_path in self.default_values:
                        new_value = self.default_values[new_path]
                        if callable(new_value):
                            doc[key] = new_value()
                        else:
                            doc[key] = new_value
            else: # list or what else
                if new_path in self.default_values:
                    new_value = self.default_values[new_path]
                    if callable(new_value):
                        doc[key] = new_value()
                    else:
                        doc[key] = new_value

    def _validate_required(self, doc, struct, path = "", root_path=""):
        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict):
                #
                # if the dict is still empty into the document we build
                # it with None values
                #
                if type(key) is not type and key not in doc:
                    if new_path in self._required_namespace:
                        if root_path:
                            new_path = ".".join([root_path, new_path])
                        raise RequireFieldError("%s is required" % new_path)
                elif type(key) is type:
                    if not len(doc):
                        if new_path in self._required_namespace:
                            if root_path:
                                new_path = ".".join([root_path, new_path])
                            raise RequireFieldError("%s is required" % new_path)
                    else:
                        for doc_key in doc:
                            self._validate_required(
                              doc[doc_key], struct[key], new_path)
                elif not len(doc[key]) and new_path in self._required_namespace:
                    if root_path:
                        new_path = ".".join([root_path, new_path])
                    raise RequireFieldError( "%s is required" % new_path )
                else:
                    self._validate_required(doc[key], struct[key], new_path, root_path)
            #
            # If the struct is a list, we have to validate all values into it
            #
            elif type(struct[key]) is list:
                #
                # check if the list must not be null
                #
                if not key in doc:
                    if new_path in self._required_namespace:
                        if root_path:
                            new_path = ".".join([root_path, new_path])
                        raise RequireFieldError( "%s is required" % new_path )
                elif not len(doc[key]) and new_path in self.required_fields:
                    if root_path:
                        new_path = ".".join([root_path, new_path])
                    raise RequireFieldError( "%s is required" % new_path )
            #
            # It is not a dict nor a list but a simple key:value
            #
            else:
                #
                # check if the value must not be null
                #
                if not key in doc:
                    if new_path in self._required_namespace:
                        if root_path:
                            new_path = ".".join([root_path, new_path])
                        raise RequireFieldError( "%s is required" % new_path )
                elif doc[key] is None and new_path in self._required_namespace:
                    if root_path:
                        new_path = ".".join([root_path, new_path])
                    raise RequireFieldError( "%s is required" % new_path )


    def __generate_skeleton(self, doc, struct, path = ""):
        for key in struct:
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is not type and key not in doc:
                if isinstance(struct[key], dict):
                    if type(struct[key]) is dict and self.use_dot_notation:
                        doc[key] = DotedDict()
                    else:
                        doc[key] = type(struct[key])()
                elif struct[key] is dict:
                    doc[key] = {}
                elif isinstance(struct[key], list):
                    doc[key] = type(struct[key])()
                elif struct[key] is list:
                    doc[key] = []
                else:
                    doc[key] = None
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and type(key) is not type:
                self.__generate_skeleton(doc[key], struct[key], path)

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
        

    def __setattr__(self, key, value):
        if key not in self._protected_field_names and self.use_dot_notation and key in self:
            self[key] = value
        else:
           dict.__setattr__(self, key, value) 

    def __getattr__(self, key):
        if key not in self._protected_field_names and self.use_dot_notation and key in self:
            return self[key]
        else:
           dict.__getattribute__(self, key) 

class RevisionDocument(MongoDocument):
    structure = {
        "id": unicode,
        "revision":int,
        "doc":dict
    }

class VersionnedDocument(MongoDocument):
    """
    This object implement a vesionnized mongo document
    """

    versioning_db_name = None
    versioning_collection_name = None

    _versioning_collection = None

    def __init__(self, *args, **kwargs):
        super(VersionnedDocument, self).__init__(*args, **kwargs)
        if not ( self.versioning_db_name or self.db_name):
            raise ValidationError( 
              "you must specify versioning_db_name or db_name" )
        if not (self.versioning_collection_name or self.collection_name):
            raise ValidationError( 
              "you must specify versioning_collection_name or collection_name" )
        if type(self.versioning_db_name) not in [type(None), str, unicode]:
            raise ValidationError(
              "versioning_db attribute must be None or basestring")
        if type(self.versioning_collection_name) not in\
          [type(None), str, unicode]:
            raise ValidationError(
              "versioning_collection attribute must be None or basestring")

    def save(self, versioning=True, *args, **kwargs):
        if versioning:
            if '_revision' in self:
                self.pop('_revision')
                self['_revision'] = self.get_last_revision_id()
            else:
                self['_revision'] = 0
            self['_revision'] += 1
            RevisionDocument._collection = self.get_versioning_collection()
            versionned_doc = RevisionDocument(
              {"id":unicode(self['_id']), "revision":self['_revision']})
            versionned_doc['doc'] = dict(self)
            versionned_doc.save()
        return super(VersionnedDocument, self).save(*args, **kwargs)

    def delete(self, versioning=False, *args, **kwargs):
        """
        if versioning is True delete revisions documents as well
        """
        if versioning:
            self.get_versioning_collection().remove({'id':self['_id']})
        super(VersionnedDocument, self).delete(*args, **kwargs)
        
    @classmethod
    def get_versioning_collection(cls):
        if not cls._versioning_collection:
            if cls._use_pylons:
                from mongokit.ext.pylons_env import MongoPylonsEnv
                db_name = MongoPylonsEnv.get_default_db()
            else:
                db_name = cls.db_name
            db_name = cls.versioning_db_name or db_name
            collection_name = cls.versioning_collection_name or\
              cls.collection_name
            if not db_name and not collection_name:
                raise ConnectionError( 
                  "You must set a db_name and a versioning collection name"
                )
            db = cls._get_connection()[db_name]
            cls._versioning_collection = db[collection_name]
            if db.collection_names():
                if not collection_name in db.collection_names():
                    cls._versioning_collection.create_index(
                      [('id', 1), ('revision', 1)], unique=True)
        return cls._versioning_collection

    def _get_versioning_collection(self):
        return self.__class__.get_versioning_collection()
    versioning_collection = property(_get_versioning_collection)

    def get_revision(self, revision_number):
        RevisionDocument._collection = self.get_versioning_collection()
        doc = RevisionDocument.one(
          {"id":self['_id'], 'revision':revision_number})
        if doc:
            return self.__class__(doc['doc'])

    def get_revisions(self):
        versionned_docs = self.versioning_collection.find({"id":self['_id']})
        for verdoc in versionned_docs:
            yield self.__class__(verdoc['doc'])

    def get_last_revision_id(self):
        last_doc = self.get_versioning_collection().find(
          {'id':self['_id']}).sort('revision', -1).next()
        if last_doc:
            return last_doc['revision']

class MongoPylonsDocument(MongoDocument):
    """Lazy helper base class to inherit from if you are
    sure you will always live in / require the pylons evironment.
    Keep in mind if you need CLI testing, "paster shell" will allow 
    you to test within a pylons environment (via an ipython shell)"""
    _use_pylons = True
