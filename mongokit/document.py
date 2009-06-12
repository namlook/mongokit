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
import re

from uuid import uuid4

authorized_types = [type(None), bool, int, float, unicode, list, dict,
  datetime.datetime, 
  pymongo.binary.Binary,
  pymongo.objectid.ObjectId,
  pymongo.dbref.DBRef,
  pymongo.code.Code,
  type(re.compile("")),
]

__all__ = ['MongoDocument', 'VersionnedDocument']

STRUCTURE_KEYWORDS = ['_id', '_revision']

class SchemaProperties(type):
    def __new__(cls, name, bases, attrs):
        for base in bases:
            parent = base.__mro__[0]
            if hasattr(parent, "structure") and not parent.__module__.startswith('mongokit.document'):
                parent = parent()
                if parent.structure:
                    if 'structure' not in attrs and parent.structure:
                        attrs['structure'] = parent.structure
                    else:
                        obj_structure = attrs.get('structure', {}).copy()
                        attrs['structure'] = parent.structure.copy()
                        attrs['structure'].update(obj_structure)
                if parent.required_fields:
                    attrs['required_fields'] = list(set(attrs.get('required_fields', [])+parent.required_fields))
                if parent.default_values:
                    obj_default_values = attrs.get('default_values', {}).copy()
                    attrs['default_values'] = parent.default_values.copy()
                    attrs['default_values'].update(obj_default_values)
                if parent.validators:
                    obj_validators = attrs.get('validators', {}).copy()
                    attrs['validators'] = parent.validators.copy()
                    attrs['validators'].update(obj_validators)
                if parent.signals:
                    obj_signals = attrs.get('signals', {}).copy()
                    attrs['signals'] = parent.signals.copy()
                    attrs['signals'].update(obj_signals)
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
    """
    __metaclass__ = SchemaProperties
    
    auto_inheritance = True
    structure = None
    required_fields = []
    default_values = {}
    validators = {}
    signals = {}

    db_host = "localhost"
    db_port = 27017
    db_name = None
    collection_name = None

    _collection = None
    
    def __init__(self, doc={}, gen_skel=True, process_signals=True):
        """
        doc : a dictionnary
        gen_skel : if True, generate automaticly the skeleton of the doc
            filled with NoneType each time validate() is called. Note that
            if doc is not {}, gen_skel is always False. If gen_skel is False,
            default_values cannot be filled.
        """
        # init
        if self.structure is None:
            raise StructureError("your document must have a structure defined")
        self._validate_structure()
        self._namespaces = list(self.__walk_dict(self.structure))
        self._validate_descriptors()
        self.__signals = {}
        for k,v in doc.iteritems():
            self[k] = v
        if doc:
            gen_skel = False
        if gen_skel:
            self.generate_skeleton()
            self._set_default_fields(self, self.structure)
        if process_signals:
            self._process_signals(self, self.structure)
        self._collection = None
        ## building required fields namespace
        self._required_namespace = set([])
        for rf in self.required_fields:
            splited_rf = rf.split('.')
            for index in range(len(splited_rf)):
                self._required_namespace.add(".".join(splited_rf[:index+1]))

    def validate(self):
        self._process_signals(self, self.structure)
        self._validate_doc(self, self.structure)
        self._validate_required(self, self.structure)
        self._process_validators(self, self.structure)

    def save(self, uuid=True, validate=True, safe=True, *args, **kwargs):
        if validate:
            self.validate()
        if '_id' not in self and uuid:
            self['_id'] = unicode("%s-%s" % (self.__class__.__name__, uuid4()))
        id = self.collection.save(self, safe=safe, *args, **kwargs)
        return self

    def delete(self):
        self.collection.remove({'_id':self['_id']})

    @classmethod
    def get_collection(cls):
        if not cls._collection:
            if not cls.db_name or not cls.collection_name:
                raise ConnectionError( "You must set a db_name and a collection_name" )
            db = Connection(cls.db_host, cls.db_port)[cls.db_name]
            cls._collection = db[cls.collection_name]
        return cls._collection

    def _get_collection(self):
        return self.__class__.get_collection()
    collection = property(_get_collection)

    @classmethod
    def get_from_id(cls, id):
        bson_obj = cls.get_collection().find_one({"_id":id})
        if bson_obj:
            return cls(bson_obj, process_signals=False)

    @classmethod
    def all(cls, *args, **kwargs):
        return MongoDocumentCursor(cls.get_collection().find(*args, **kwargs), cls)

    @classmethod
    def one(cls, *args, **kwargs):
        bson_obj = cls.get_collection().find(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return cls(list(bson_obj)[0], process_signals=False)

    @classmethod
    def remove(cls, *args, **kwargs):
        return cls.get_collection().remove(*args, **kwargs)

#    def __setitem__(self, key, value):
#        dict.__setitem__(self, key, value)

 
    def __walk_dict(self, dic):
        # thanks jean_b for the patch
        for key, value in dic.items():
            if isinstance(value, dict) and len(value):
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
            else:
                if type(key) is not type:
                    yield key
                else:
                    yield ""

    def generate_skeleton(self):
        """
        validate and generate the skeleton of the document
        from the structure (unknown values are set to None)
        """
        self.__generate_skeleton(self, self.structure)

    def _validate_descriptors(self):
        for dv in self.default_values:
            if dv not in self._namespaces:
                raise ValueError("Error in default_values: can't find %s in structure" % dv )
        for required in self.required_fields:
            if required not in self._namespaces:
                raise ValueError("Error in required_fields: can't find %s in structure" % required )
        for signal in self.signals:
            if signal not in self._namespaces:
                raise ValueError("Error in signals: can't find %s in structure" % signal )
        for validator in self.validators:
            if validator not in self._namespaces:
                raise ValueError("Error in validators: can't find %s in structure" % validator )

    def _validate_structure(self):
        ##############
        def __validate_structure( struct):
            if type(struct) is type:
                if struct not in authorized_types:
                    raise StructureError("%s is not an authorized_types" % key)
            elif isinstance(struct, dict):
                for key in struct:
                    if isinstance(key, basestring):
                        if "." in key: raise BadKeyError("%s must not contain '.'" % key)
                        if key.startswith('$'): raise BadKeyError("%s must not start with '$'" % key)
                    elif type(key) is type:
                        if not key in authorized_types:
                            raise AuthorizedTypeError("%s is not an authorized type" % key)
                    else:
                        raise StructureError("%s must be a basestring or a type" % key)
                    if isinstance(struct[key], dict):
                        __validate_structure(struct[key])
                    elif isinstance(struct[key], list):
                        __validate_structure(struct[key])
                    elif struct[key] not in authorized_types:
                        raise StructureError("%s is not an authorized type" % struct[key])
            elif isinstance(struct, list):
                for item in struct:
                    __validate_structure(item)
        #################
        if self.structure is None:
            raise StructureError("self.structure must not be None")
        if not isinstance(self.structure, dict):
            raise StructureError("self.structure must be a dict instance")
        if self.required_fields:
            if len(self.required_fields) != len(set(self.required_fields)):
                raise DuplicateRequiredError("duplicate required_fields : %s" % self.required_fields)
        __validate_structure(self.structure)
                    
    def _validate_doc(self, doc, struct, path = ""):
        if type(struct) is type or struct is None:
            if struct is None:
                if type(doc) not in authorized_types:
                    raise AuthorizedTypeError("%s is not an authorized types" % type(doc).__name__)
            elif not isinstance(doc, struct) and doc is not None:
                raise SchemaTypeError("%s must be an instance of %s not %s" % (path, struct.__name__, type(doc).__name__))
        elif isinstance(struct, dict):
            if not isinstance(doc, type(struct)):
                raise SchemaTypeError("%s must be an instance of %s not %s" %(path, type(struct).__name__, type(doc).__name__))
            if len(doc) != len(struct):
                struct_doc_diff = list(set(struct).difference(set(doc)))
                if struct_doc_diff:
                    for field in struct_doc_diff:
                        if type(field) is not type:
                            raise StructureError( "missed fields : %s" % struct_doc_diff )
                else:
                    struct_struct_diff = list(set(doc).difference(set(struct)))
                    if not sum( 1 for s in struct_struct_diff if s in STRUCTURE_KEYWORDS):
                        raise StructureError( "unknown fields : %s" % struct_struct_diff)
            for key in struct:
                if type(key) is type:
                    new_key = "$%s" % key.__name__
                else:
                    new_key = key
                new_path = ".".join([path, new_key]).strip('.')
                if new_key.split('.')[-1].startswith("$"):
                    for doc_key in doc:
                        if not isinstance(doc_key, key):
                            raise SchemaTypeError("key of %s must be an instance of %s not %s" % (path, key.__name__, type(doc_key).__name__))
                        self._validate_doc(doc[doc_key], struct[key], new_path)
                else:
                    self._validate_doc(doc[key], struct[key],  new_path)
        elif isinstance(struct, list):
            if not isinstance(doc, list):
                raise SchemaTypeError("%s must be an instance of list not %s" % (path, type(doc).__name__))
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
                            raise ValidationError("%s does not pass the validator %s" % (new_path, validator.__name__))
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
                # if the dict is still empty into the document we build it with None values
                #
                if type(key) is not type and key not in doc:
                    __processval(self, new_path, doc)
                elif type(key) is type:
                    for doc_key in doc:
                        self._process_validators(doc[doc_key], struct[key], new_path)
                        #self._process_validators(doc[key], struct[key], new_path)
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
            # if exists, and it is a function then call it otherwise, juste feed it
            #
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
                # if the dict is still empty into the document we build it with None values
                #
                if len(struct[key]) and not [i for i in struct[key].keys() if type(i) is type]:
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

    def _process_signals(self, doc, struct, path = ""):
        #################################################
        def __procsignals(self, new_path, doc):
            if new_path in self.signals:
                launch_signals = True
            else:
                launch_signals = False
            if new_path in self.signals and launch_signals:
                make_signal = False
                if new_path in self.__signals:
                    if doc[key] != self.__signals[new_path]:
                        make_signal = True
                else:
                    make_signal = True
                if make_signal:
                    if not hasattr(self.signals[new_path], "__iter__"):
                        signals = [self.signals[new_path]]
                    else:
                        signals = self.signals[new_path]
                    for signal in signals:
                        signal(self, doc[key])
                    self.__signals[new_path] = doc[key]
        ##################################################
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
                # if the dict is still empty into the document we build it with None values
                #
                if key in doc:
                    self._process_signals(doc[key], struct[key], new_path)
                else:
                    pass
                    # TODO signals_namespace
            #
            # It is not a dict nor a list but a simple key:value
            #
            else:
                #
                # check if the value must not be null
                #
                if new_path in self.signals:
                    __procsignals(self, new_path, doc)

    def _validate_required(self, doc, struct, path = ""):
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
                # if the dict is still empty into the document we build it with None values
                #
                if type(key) is not type and key not in doc:
                    if new_path in self._required_namespace:
                        raise RequireFieldError("%s is required" % new_path)
                elif type(key) is type:
                    if not len(doc):
                        if new_path in self._required_namespace:
                            raise RequireFieldError("%s is required" % new_path)
                    else:
                        for doc_key in doc:
                            self._validate_required(doc[doc_key], struct[key], new_path)
                elif not len(doc[key]) and new_path in self._required_namespace:
                    raise RequireFieldError( "%s is required" % new_path )
                else:
                    self._validate_required(doc[key], struct[key], new_path)
            #
            # If the struct is a list, we have to validate all values into it
            #
            elif type(struct[key]) is list:
                #
                # check if the list must not be null
                #
                if not key in doc:
                    if new_path in self._required_namespace:
                        raise RequireFieldError( "%s is required" % new_path )
                elif not len(doc[key]) and new_path in self.required_fields:
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
                        raise RequireFieldError( "%s is required" % new_path )
                elif doc[key] is None and new_path in self._required_namespace:
                    raise RequireFieldError( "%s is required" % new_path )


    def __generate_skeleton(self, doc, struct, path = ""):
        for key in struct:
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is not type and key not in doc:
                if isinstance(struct[key], dict):
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

    def __init__(self,*args, **kwargs):
        super(VersionnedDocument, self).__init__(*args, **kwargs)
        if not ( self.versioning_db_name or self.db_name):
            raise ValidationError( "you must specify versioning_db_name or db_name" )
        if not (self.versioning_collection_name or self.collection_name):
            raise ValidationError( "you must specify versioning_collection_name or collection_name" )
        if type(self.versioning_db_name) not in [type(None), str, unicode]:
            raise ValidationError("versioning_db attribute must be None or basestring")
        if type(self.versioning_collection_name) not in [type(None), str, unicode]:
            raise ValidationError("versioning_collection attribute must be None or basestring")

    def save(self, versioning=True, *args, **kwargs):
        if versioning:
            if '_revision' in self:
                self.pop('_revision')
                self['_revision'] = self.get_last_revision_id()
            else:
                self['_revision'] = 0
            self['_revision'] += 1
            RevisionDocument._collection = self.get_versioning_collection()
            versionned_doc = RevisionDocument({"id":unicode(self['_id']), "revision":self['_revision']})
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
            db_name = cls.versioning_db_name or cls.db_name
            collection_name = cls.versioning_collection_name or cls.collection_name
            if not  db_name and not collection_name:
                raise ConnectionError( "You must set a db_name and a versioning collection name" )
            db = Connection(cls.db_host, cls.db_port)[db_name]
            cls._versioning_collection = db[collection_name]
            if db.collection_names():
                if not collection_name in db.collection_names():
                    cls._versioning_collection.create_index([('id',1), ('revision', 1)], unique=True)
        return cls._versioning_collection

    def _get_versioning_collection(self):
        return self.__class__.get_versioning_collection()
    versioning_collection = property(_get_versioning_collection)

    def get_revision(self, revision_number):
        RevisionDocument._collection = self.get_versioning_collection()
        doc = RevisionDocument.one({"id":self['_id'], 'revision':revision_number})
        if doc:
            return self.__class__(doc['doc'], process_signals=False)

    def get_revisions(self):
        versionned_docs = self.versioning_collection.find({"id":self['_id']})
        for verdoc in versionned_docs:
            yield self.__class__(verdoc['doc'], process_signals=False)

    def get_last_revision_id(self):
        last_doc = self.get_versioning_collection().find({'id':self['_id']}).sort('revision', -1).next()
        if last_doc:
            return last_doc['revision']

