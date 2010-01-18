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

import datetime
import re
import logging
from copy import deepcopy

log = logging.getLogger(__name__)

from operators import SchemaOperator, IS
from helpers import *

__all__ = ['CustomType', 'SchemaProperties', 'SchemaDocument', 'DotedDict', 'DotExpandedDict', 'DotCollapsedDict',
  'RequireFieldError', 'StructureError', 'BadKeyError', 'AuthorizedTypeError', 'ValidationError',
  'DuplicateRequiredError', 'DuplicateDefaultValueError', 'ModifierOperatorError', 'SchemaDocument',
  'SchemaTypeError', 'DefaultFieldTypeError', 'totimestamp', 'fromtimestamp', 'i18n', 'i18nError']

class CustomType(object): 
    mongo_type = None
    python_type = None
    
    def __init__(self):
        if self.mongo_type is None:
            raise TypeError("`mongo_type` property must be specify in %s" % self.__class__.__name__)
        if self.python_type is None:
            raise TypeError("`python_type` property must be specify in %s" % self.__class__.__name__)

    def to_bson(self, value):
        """convert type to a mongodb type"""
        raise NotImplementedError

    def to_python(self, value):
        """convert type to a mongodb type"""
        raise NotImplementedError


# field wich does not need to be declared into the structure
STRUCTURE_KEYWORDS = []

class RequireFieldError(Exception):pass
class StructureError(Exception):pass
class BadKeyError(Exception):pass
class AuthorizedTypeError(Exception):pass
class ValidationError(Exception):pass
class DuplicateRequiredError(Exception):pass
class DuplicateDefaultValueError(Exception):pass
class ModifierOperatorError(Exception):pass
class SchemaTypeError(Exception):pass
class DefaultFieldTypeError(Exception):pass
class i18nError(Exception):pass

class SchemaProperties(type):
    def __new__(cls, name, bases, attrs):
        attrs['_protected_field_names'] = set(['_protected_field_names', '_namespaces', '_required_namespace'])
        for base in bases:
            parent = base.__mro__[0]
            if hasattr(parent, 'structure'):
                if parent.structure is not None:
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
                    if parent.i18n:
                        attrs['i18n'] = list(set(
                          attrs.get('i18n', [])+parent.i18n))
        for mro in bases[0].__mro__:
            attrs['_protected_field_names'] = attrs['_protected_field_names'].union(list(mro.__dict__))
        attrs['_protected_field_names'] = list(attrs['_protected_field_names'])
        return type.__new__(cls, name, bases, attrs)        


class SchemaDocument(dict):
    """
    A SchemaDocument is dictionnary with a building structured schema
    The validate method will check that the document match the underling
    structure. A structure must be specify in each SchemaDocument.

    >>> class TestDoc(SchemaDocument):
    ...     structure = {
    ...         "foo":unicode,
    ...         "bar":int,
    ...         "nested":{
    ...            "bla":float}} 

    `unicode`, `int`, `float` are python types listed in `mongokit.authorized_types`.
    
    >>> doc = TestDoc()
    >>> doc
    {'foo': None, 'bar': None, 'nested': {'bla': None}}
    
    A SchemaDocument works just like dict:

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

    >>> class TestDotNotation(SchemaDocument):
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
    i18n = []

    skip_validation = False

    # If you want to use the dot notation, set this to True:
    use_dot_notation = False

    authorized_types = [
      type(None),
      bool,
      int,
      long,
      float,
      unicode,
      list, 
      dict,
      datetime.datetime, 
      CustomType,
    ]

    def __init__(self, doc=None, gen_skel=True, gen_auth_types=True, validate=True, lang='en', fallback_lang='en'):
        """
        doc : a dictionnary
        gen_skel : if True, generate automaticly the skeleton of the doc
            filled with NoneType each time validate() is called. Note that
            if doc is not {}, gen_skel is always False. If gen_skel is False,
            default_values cannot be filled.
        gen_auth_types: if True, generate automaticly the self._authorized_types
            attribute from self.authorized_types
        """
        self._current_lang = lang
        self._fallback_lang = fallback_lang
        # init
        if gen_auth_types:
            self._authorized_types = self.authorized_types[:]
        if doc is None:
            doc = {}
        if not self.skip_validation and validate: 
            self._validate_structure()
            self._namespaces = list(self.__walk_dict(self.structure))
            self._validate_descriptors()
        for k, v in doc.iteritems():
            self[k] = v
        if doc:
            gen_skel = False
            if self.i18n or self.use_dot_notation:
                self.__generate_doted_dict(self, self.structure)
        if gen_skel:
            self.generate_skeleton()
            if self.default_values:
                self._set_default_fields(self, self.structure)
        else:
            self._process_custom_type('python', self, self.structure)
        ## building required fields namespace
        if not self.skip_validation:
            self._required_namespace = set([])
            for rf in self.required_fields:
                splited_rf = rf.split('.')
                for index in range(len(splited_rf)):
                    self._required_namespace.add(".".join(splited_rf[:index+1]))
        if self.i18n:
            self._make_i18n()

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
        self._process_custom_type('bson', self, self.structure)
        self._validate_doc(self, self.structure)
        if self.required_fields:
            self._validate_required(self, self.structure)
        if self.validators:
            self._process_validators(self, self.structure)
        self._process_custom_type('python', self, self.structure)

    def __setattr__(self, key, value):
        if key not in self._protected_field_names and self.use_dot_notation and key in self:
            if isinstance(self.structure[key], i18n):
                self[key][self._current_lang] = value
            else:
                self[key] = value
        else:
           dict.__setattr__(self, key, value) 

    def __getattr__(self, key):
        if key not in self._protected_field_names and self.use_dot_notation and key in self:
            if isinstance(self[key], i18n):
                if self._current_lang not in self[key]:
                    return self[key].get(self._fallback_lang)
                return self[key][self._current_lang]
            return self[key]
        else:
            return dict.__getattribute__(self, key) 

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
                    #if type(child_key) is type:
                    #    new_child_key = "$%s" % child_key.__name__
                    #else:
                    if type(child_key) is not type:
                        new_child_key = child_key
                    yield '%s.%s' % (new_key, new_child_key)
            elif type(key) is type:
                yield '$%s' % key.__name__
            elif isinstance(value, list) and len(value):
                if isinstance(value[0], dict):
                    for child_key in self.__walk_dict(value[0]):
                        #if type(key) is type:
                        #    new_key = "$%s" % key.__name__
                        #else:
                        if type(key) is not type:
                            new_key = key
                        #if type(child_key) is type:
                        #    new_child_key = "$%s" % child_key.__name__
                        #else:
                        if type(child_key) is not type:
                            new_child_key = child_key
                        yield '%s.%s' % (new_key, new_child_key)
                else:
                    if type(key) is not type:
                        yield key
                    #else:
                    #    yield ""
            else:
                if type(key) is not type:
                    yield key
                #else:
                #    yield ""

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

    def _validate_structure(self):
        """
        validate if all fields in self.structure are in authorized types.
        """
        ##############
        def __validate_structure( struct):
            if type(struct) is type:
                if struct not in self._authorized_types:
                    raise StructureError("%s is not an authorized_types" % struct)
            elif isinstance(struct, dict):
                for key in struct:
                    if isinstance(key, basestring):
                        if "." in key: raise BadKeyError(
                          "%s must not contain '.'" % key)
                        if key.startswith('$'): raise BadKeyError(
                          "%s must not start with '$'" % key)
                    elif type(key) is type:
                        if not key in self._authorized_types:
                            raise AuthorizedTypeError(
                              "%s is not an authorized type" % key)
                    else:
                        raise StructureError(
                          "%s must be a basestring or a type" % key)
                    if isinstance(struct[key], dict):
                        __validate_structure(struct[key])
                    elif isinstance(struct[key], list):
                        __validate_structure(struct[key])
                    elif isinstance(struct[key], tuple):
                        __validate_structure(struct[key])
                    elif isinstance(struct[key], CustomType):
                        __validate_structure(struct[key].mongo_type)
                    elif isinstance(struct[key], SchemaOperator):
                        __validate_structure(struct[key])
                    elif hasattr(struct[key], 'structure'):
                        __validate_structure(struct[key])
                    elif (struct[key] not in self._authorized_types):
                        ok = False
                        for auth_type in self._authorized_types:
                            if isinstance(struct[key], auth_type) or issubclass(struct[key], auth_type):
                                ok = True
                        if not ok:
                            raise StructureError(
                              "%s is not an authorized type" % struct[key])
            elif isinstance(struct, list):
                for item in struct:
                    __validate_structure(item)
            elif isinstance(struct, tuple):
                for item in struct:
                    __validate_structure(item)
            elif isinstance(struct, SchemaOperator):
                if isinstance(struct, IS):
                    for operand in struct:
                        if type(operand) not in self._authorized_types:
                            raise StructureError(
                              "%s in %s is not an authorized type" % (operand, struct))
                else:
                    for operand in struct:
                        if operand not in self._authorized_types: 
                            raise StructureError(
                              "%s in %s is not an authorized type" % (operand, struct))
            else:
                ok = False
                for auth_type in self._authorized_types:
                    if isinstance(struct, auth_type):
                        ok = True
                if not ok:
                    raise StructureError("%s is not an authorized_types" % struct)
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
        """
        check it doc field types match the doc field structure
        """
        if type(struct) is type or struct is None:
            if struct is None:
                if type(doc) not in self._authorized_types:
                    raise AuthorizedTypeError(
                      "%s is not an authorized types" % type(doc).__name__)
            elif not isinstance(doc, struct) and doc is not None:
                raise SchemaTypeError(
                  "%s must be an instance of %s not %s" % (
                    path, struct.__name__, type(doc).__name__))
        elif isinstance(struct, CustomType):
            if not isinstance(doc, struct.mongo_type) and doc is not None:
                raise SchemaTypeError(
                  "%s must be an instance of %s not %s" % (
                    path, struct.mongo_type.__name__, type(doc).__name__))
        elif isinstance(struct, SchemaOperator):
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
        elif isinstance(struct, tuple):
            if not isinstance(doc, list):
                raise SchemaTypeError(
                  "%s must be an instance of list not %s" % (
                    path, type(doc).__name__))
            if len(doc) != len(struct):
                raise SchemaTypeError(
                  "%s must have %s items not %s" % (
                    path, len(struct), len(doc)))
            for i in range(len(struct)):
                self._validate_doc(doc[i], struct[i], path)
            
    def _process_validators(self, doc, struct, path = ""):
        doted_doc = DotCollapsedDict(doc)
        doted_struct = DotCollapsedDict(self.structure)
        for key, validators in self.validators.iteritems():
            if doted_doc[key] is not None:
                if not hasattr(validators, "__iter__"):
                    validators = [validators]
                for validator in validators:
                    if not validator(doted_doc[key]):
                        raise ValidationError(
                          "%s does not pass the validator %s" % (
                            key, validator.__name__))

    def _process_custom_type(self, target, doc, struct, path = "", root_path=""):
        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # if the value is a dict, we have a another structure to validate
            #
            #
            # It is not a dict nor a list but a simple key:value
            #
            if isinstance(struct[key], CustomType):
                if target == 'bson':
                    if struct[key].python_type is not None:
                        if not isinstance(doc[key], struct[key].python_type) and doc[key] is not None:
                            raise SchemaTypeError(
                              "%s must be an instance of %s not %s" % (
                                new_path, struct[key].python_type.__name__, type(doc[key]).__name__))
                    doc[key] = struct[key].to_bson(doc[key])
                else:
                    doc[key] = struct[key].to_python(doc[key])
            elif isinstance(struct[key], dict):
                if doc: # we don't need to process an empty doc
                    if type(key) is type:
                        for doc_key in doc: # process type's key such {unicode:int}...
                            self._process_custom_type(target, doc[doc_key], struct[key], new_path, root_path)
                    else:
                        if key in doc: # we don't care about missing fields
                            self._process_custom_type(target, doc[key], struct[key], new_path, root_path)
            #
            # If the struct is a list, we have to validate all values into it
            #
            elif type(struct[key]) is list:
                #
                # check if the list must not be null
                #
                if struct[key]:
                    l_objs = []
                    if isinstance(struct[key][0], CustomType):
                        for obj in doc[key]:
                            if target=='bson':
                                if struct[key][0].python_type is not None:
                                    if not isinstance(obj, struct[key][0].python_type) and obj is not None:
                                        raise SchemaTypeError(
                                          "%s must be an instance of %s not %s" % (
                                            new_path, struct[key][0].python_type.__name__, type(obj).__name__))
                                obj = struct[key][0].to_bson(obj)
                            else:
                                obj = struct[key][0].to_python(obj)
                            l_objs.append(obj)
                        doc[key] = l_objs
                    elif isinstance(struct[key][0], dict):
                        if doc[key]:
                            for obj in doc[key]:
                                self._process_custom_type(target, obj, struct[key][0], new_path, root_path)
            
    def _set_default_fields(self, doc, struct, path = ""):
        # TODO check this out, this method must be restructured
        for key in struct:
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
                        new_value = new_value()
                    if isinstance(struct[key], CustomType):
                        if not isinstance(new_value, struct[key].python_type):
                            raise DefaultFieldTypeError(
                              "%s must be an instance of %s not %s" % (
                                new_path, struct[key].python_type.__name__, type(new_value).__name__))
                    doc[key] = new_value
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and new_path not in self.i18n:
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
                            new_value = new_value()
                        doc[key] = new_value
            elif isinstance(struct[key], list):
                if new_path in self.default_values:
                    for new_value in self.default_values[new_path]:
                        if callable(new_value):
                            new_value = new_value()
                        if isinstance(struct[key][0], CustomType):
                            if not isinstance(new_value, struct[key][0].python_type):
                                raise DefaultFieldTypeError(
                                  "%s must be an instance of %s not %s" % (
                                    new_path, struct[key][0].python_type.__name__, type(new_value).__name__))
                        doc[key].append(new_value)  
            else: # what else
                if new_path in self.default_values:
                    new_value = self.default_values[new_path]
                    if callable(new_value):
                        new_value = new_value()
                    if new_path in self.i18n:
                        doc[key] = i18n(
                          field_type = struct[key],
                          field_name = key
                        )
                        doc[key].update(new_value)
                    else:
                        doc[key] = new_value

    def _validate_required(self, doc, struct, path="", root_path=""):
        doted_doc = DotCollapsedDict(doc)
        doted_struct = DotCollapsedDict(self.structure)
        for req in self.required_fields:
            if doted_doc.get(req) is None:
                raise RequireFieldError("%s is required" % req)
            elif doted_doc.get(req) == []:
                raise RequireFieldError("%s is required" % req)
            elif doted_doc.get(req) == {}:
                raise RequireFieldError("%s is required" % req)

    def __generate_skeleton(self, doc, struct, path = ""):
        for key in struct:
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is not type and key not in doc:
                if isinstance(struct[key], dict):
                    if type(struct[key]) is dict and self.use_dot_notation:
                        if self.i18n:
                            doc[key] = i18nDotedDict(doc.get(key, {}), self)
                        else:
                            doc[key] = DotedDict(doc.get(key, {}))
                    else:
                        if callable(struct[key]):
                            doc[key] = struct[key]()
                        else:
                            doc[key] = type(struct[key])()
                elif struct[key] is dict:
                    doc[key] = {}
                elif isinstance(struct[key], list):
                    doc[key] = type(struct[key])()
                elif struct[key] is list:
                    doc[key] = []
                elif isinstance(struct[key], tuple):
                    doc[key] = [None for i in range(len(struct[key]))]
                else:
                    doc[key] = None
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and type(key) is not type:
                self.__generate_skeleton(doc[key], struct[key], path)

    def __generate_doted_dict(self, doc, struct):
        for key in struct:
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is not type:# and key not in doc:
                if isinstance(struct[key], dict):
                    if type(struct[key]) is dict:
                        if self.i18n:
                            doc[key] = i18nDotedDict(doc.get(key, {}), self)
                        else:
                            doc[key] = DotedDict(doc.get(key, {}))
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and type(key) is not type:
                self.__generate_doted_dict(doc[key], struct[key])


    def _make_i18n(self):
        doted_dict = DotCollapsedDict(self.structure)
        for field in self.i18n:
            if field not in doted_dict:
                raise ValidationError("%s not found in structure" % field)
            if not isinstance(doted_dict[field], i18n):
                doted_dict[field] = i18n(
                  field_type = doted_dict[field],
                  field_name = field
                )
        self.structure.update(DotExpandedDict(doted_dict))

    def set_lang(self, lang):
        self._current_lang = lang
    def get_lang(self):
        return self._current_lang

class i18n(dict, CustomType):
    """ CustomType to deal with i18n """
    mongo_type = list

    def __init__(self, field_type=None, field_name=None):
        super(i18n, self).__init__()
        self.python_type = self.__class__
        self._field_type = field_type
        self._field_name = field_name

    def __call__(self):
        return i18n(self._field_type, self._field_name)

    def to_bson(self, value):
        if value is not None:
            for l,v in value.iteritems():
                if isinstance(v, list) and isinstance(self._field_type, list):
                    for i in v:
                        if not isinstance(i, self._field_type[0]):
                            raise SchemaTypeError(
                              "%s (%s) must be an instance of %s not %s" % (
                                self._field_name, l, self._field_type[0], type(i).__name__))
                else:
                    if not isinstance(v, self._field_type):
                        raise SchemaTypeError(
                          "%s (%s) must be an instance of %s not %s" % (
                            self._field_name, l, self._field_type, type(v).__name__))
            return [{'lang':l, 'value':v} for l,v in value.iteritems()]
        
    def to_python(self, value):
        if value is not None:
            i18n_dict = self.__class__(self._field_type)
            for i in  value:
                i18n_dict[i['lang']] = i['value']
            return i18n_dict

