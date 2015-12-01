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

import bson
import datetime
import logging
from copy import deepcopy

log = logging.getLogger(__name__)

from mongokit.operators import SchemaOperator, IS
from mongokit.helpers import DotCollapsedDict
from mongokit.helpers import DotExpandedDict
from mongokit.helpers import i18nDotedDict
from mongokit.helpers import DotedDict

__all__ = [
    'AuthorizedTypeError',
    'BadKeyError',
    'CustomType',
    'DefaultFieldTypeError',
    'DotCollapsedDict',
    'DotedDict',
    'DotExpandedDict',
    'DuplicateDefaultValueError',
    'DuplicateRequiredError',
    'i18n',
    'i18nError',
    'ModifierOperatorError',
    'RequireFieldError',
    'SchemaDocument',
    'SchemaDocumentError',
    'SchemaProperties',
    'SchemaTypeError',
    'Set',
    'StructureError',
    'ValidationError',
]


class CustomType(object):
    init_type = None
    mongo_type = None
    python_type = None

    def __init__(self):
        if self.mongo_type is None:
            raise TypeError("`mongo_type` property must be specify in %s" %
                            self.__class__.__name__)
        if self.python_type is None:
            raise TypeError("`python_type` property must be specify in %s" %
                            self.__class__.__name__)

    def to_bson(self, value):
        """convert type to a mongodb type"""
        raise NotImplementedError

    def to_python(self, value):
        """convert type to a mongodb type"""
        raise NotImplementedError

    def validate(self, value, path):
        """
        This method is optional. It add a validation layer.
        This method is been called in Document.validate()

        value: the value of the field
        path: the field name (ie, 'foo' or 'foo.bar' if nested)
        """
        pass


# field wich does not need to be declared into the structure
STRUCTURE_KEYWORDS = []


class SchemaDocumentError(Exception):
    pass


class RequireFieldError(SchemaDocumentError):
    pass


class StructureError(SchemaDocumentError):
    pass


class BadKeyError(SchemaDocumentError):
    pass


class AuthorizedTypeError(SchemaDocumentError):
    pass


class ValidationError(SchemaDocumentError):
    pass


class DuplicateRequiredError(SchemaDocumentError):
    pass


class DuplicateDefaultValueError(SchemaDocumentError):
    pass


class ModifierOperatorError(SchemaDocumentError):
    pass


class SchemaTypeError(SchemaDocumentError):
    pass


class DefaultFieldTypeError(SchemaDocumentError):
    pass


class i18nError(SchemaDocumentError):
    pass


class DeprecationError(Exception):
    pass


class DuplicateI18nError(Exception):
    pass


class SchemaProperties(type):
    def __new__(mcs, name, bases, attrs):
        attrs['_protected_field_names'] = set(
            ['_protected_field_names', '_namespaces', '_required_namespace'])
        for base in bases:
            parent = base.__mro__[0]
            if not hasattr(parent, 'structure'):
                continue

            if parent.structure is not None:
                #parent = parent()
                if parent.structure:
                    if 'structure' not in attrs and parent.structure:
                        attrs['structure'] = parent.structure.copy()
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
            if attrs.get('authorized_types'):
                attrs['authorized_types'] = list(set(parent.authorized_types).union(set(attrs['authorized_types'])))
        for mro in bases[0].__mro__:
            attrs['_protected_field_names'] = attrs['_protected_field_names'].union(list(mro.__dict__))
        attrs['_protected_field_names'] = list(attrs['_protected_field_names'])
        if attrs.get('structure') and name not in \
                ["SchemaDocument", "Document", "VersionedDocument", "RevisionDocument"]:
            base = bases[0]
            if not attrs.get('authorized_types'):
                attrs['authorized_types'] = base.authorized_types
            base._validate_structure(attrs['structure'], name, attrs.get('authorized_types'))
            attrs['_namespaces'] = list(base._SchemaDocument__walk_dict(attrs['structure']))
            if [1 for i in attrs['_namespaces'] if type(i) is type]:
                raise DeprecationError("%s: types are not allowed as structure key anymore" % name)
            mcs._validate_descriptors(attrs)
            ## building required fields namespace
            attrs['_required_namespace'] = set([])
            for rf in attrs.get('required_fields', []):
                splited_rf = rf.split('.')
                for index in range(len(splited_rf)):
                    attrs['_required_namespace'].add(".".join(splited_rf[:index+1]))
            attrs['_collapsed_struct'] = DotCollapsedDict(attrs['structure'], remove_under_type=True)
        elif attrs.get('structure') is not None and name not in \
                ["SchemaDocument", "Document", "VersionedDocument", "RevisionDocument"]:
            attrs['_collapsed_struct'] = {}
        attrs['_i18n_namespace'] = []
        if attrs.get('i18n'):
            attrs['_i18n_namespace'] = set(['.'.join(i.split('.')[:-1]) for i in attrs['i18n']])
        return type.__new__(mcs, name, bases, attrs)

    @classmethod
    def _validate_descriptors(mcs, attrs):
        # TODO i18n validator
        for dv in attrs.get('default_values', {}):
            if not dv in attrs['_namespaces']:
                raise ValueError("Error in default_values: can't find %s in structure" % dv)
        for required in attrs.get('required_fields', []):
            if required not in attrs['_namespaces']:
                raise ValueError("Error in required_fields: can't find %s in structure" % required)
        for validator in attrs.get('validators', {}):
            if validator not in attrs['_namespaces']:
                raise ValueError("Error in validators: can't find %s in structure" % validator)
        # required_field
        if attrs.get('required_fields'):
            if len(attrs['required_fields']) != len(set(attrs['required_fields'])):
                raise DuplicateRequiredError("duplicate required_fields : %s" % attrs['required_fields'])
        # i18n
        if attrs.get('i18n'):
            if len(attrs['i18n']) != len(set(attrs['i18n'])):
                raise DuplicateI18nError("duplicated i18n : %s" % attrs['i18n'])
            for _i18n in attrs['i18n']:
                if _i18n not in attrs['_namespaces']:
                    raise ValueError("Error in i18n: can't find {} in structure".format(_i18n))


class SchemaDocument(dict):
    """
    A SchemaDocument is dictionary with a building structured schema
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

    Validation is made with the `validate()` method:

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
    raise_validation_errors = True

    skip_validation = False

    # if you want to have all schemaless benefits (default False but should change)
    # warning, if use_schemaless is True, Migration features can not be used.
    use_schemaless = False

    # If you want to use the dot notation, set this to True:
    use_dot_notation = False
    dot_notation_warning = False

    authorized_types = [
        type(None),
        bool,
        int,
        long,
        float,
        unicode,
        basestring,
        list,
        dict,
        datetime.datetime,
        bson.binary.Binary,
        CustomType,
    ]

    def __init__(self, doc=None, gen_skel=True, _gen_auth_types=True, _validate=True, lang='en', fallback_lang='en'):
        """
        doc : a dictionary
        gen_skel : if True, generate automatically the skeleton of the doc
            filled with NoneType each time validate() is called. Note that
            if doc is not {}, gen_skel is always False. If gen_skel is False,
            default_values cannot be filled.
        gen_auth_types: if True, generate automatically the self.authorized_types
            attribute from self.authorized_types
        """
        super(SchemaDocument, self).__init__()
        if self.structure is None:
            self.structure = {}
        self._current_lang = lang
        self._fallback_lang = fallback_lang
        self.validation_errors = {}
        # init
        if doc:
            for k, v in doc.iteritems():
                self[k] = v
            gen_skel = False
        if gen_skel:
            self.generate_skeleton()
            if self.default_values:
                self._set_default_fields(self, self.structure)
        else:
            self._process_custom_type('python', self, self.structure)
        if self.use_dot_notation:
            self.__generate_doted_dict(self, self.structure)
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

        Additionally, this method will process all
        validators.

        """
        if self.validators:
            self._process_validators(self, self.structure)
        self._process_custom_type('bson', self, self.structure)
        self._validate_doc(self, self.structure)
        self._process_custom_type('python', self, self.structure)
        if self.required_fields:
            self._validate_required(self, self.structure)

    def __setattr__(self, key, value):
        if key not in self._protected_field_names and self.use_dot_notation and key in self:
            if isinstance(self.structure[key], i18n):
                self[key][self._current_lang] = value
            else:
                self[key] = value
        else:
            if self.dot_notation_warning and not key.startswith('_') and key not in \
                    ['db', 'collection', 'versioning_collection', 'connection', 'fs']:
                log.warning("dot notation: {} was not found in structure. Add it as attribute instead".format(key))
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

    @classmethod
    def __walk_dict(cls, dic):
        # thanks jean_b for the patch
        for key, value in dic.items():
            if isinstance(value, dict) and len(value):
                if type(key) is type:
                    yield '$%s' % key.__name__
                else:
                    yield key
                for child_key in cls.__walk_dict(value):
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
#            elif isinstance(value, list) and len(value):
#                if isinstance(value[0], dict):
#                    for child_key in cls.__walk_dict(value[0]):
#                        #if type(key) is type:
#                        #    new_key = "$%s" % key.__name__
#                        #else:
#                        if type(key) is not type:
#                            new_key = key
#                        #if type(child_key) is type:
#                        #    new_child_key = "$%s" % child_key.__name__
#                        #else:
#                        if type(child_key) is not type:
#                            new_child_key = child_key
#                        yield '%s.%s' % (new_key, new_child_key)
#                else:
#                    if type(key) is not type:
#                        yield key
#                    #else:
#                    #    yield ""
            else:
                if type(key) is not type:
                    yield key
                #else:
                #    yield ""

    @classmethod
    def _validate_structure(cls, structure, name, authorized_types):
        """
        validate if all fields in self.structure are in authorized types.
        """
        ##############
        def __validate_structure(struct, name, _authorized):
            if type(struct) is type:
                if struct not in authorized_types:
                    if struct not in authorized_types:
                        raise StructureError("%s: %s is not an authorized type" % (name, struct))
            elif isinstance(struct, dict):
                for key in struct:
                    if isinstance(key, basestring):
                        if "." in key:
                            raise BadKeyError("%s: %s must not contain '.'" % (name, key))
                        if key.startswith('$'):
                            raise BadKeyError("%s: %s must not start with '$'" % (name, key))
                    elif type(key) is type:
                        if not key in authorized_types:
                            raise AuthorizedTypeError("%s: %s is not an authorized type" % (name, key))
                    else:
                        raise StructureError("%s: %s must be a basestring or a type" % (name, key))
                    if struct[key] is None:
                        pass
                    elif isinstance(struct[key], dict):
                        __validate_structure(struct[key], name, authorized_types)
                    elif isinstance(struct[key], list):
                        __validate_structure(struct[key], name, authorized_types)
                    elif isinstance(struct[key], tuple):
                        __validate_structure(struct[key], name, authorized_types)
                    elif isinstance(struct[key], CustomType):
                        __validate_structure(struct[key].mongo_type, name, authorized_types)
                    elif isinstance(struct[key], SchemaProperties):
                        pass
                    elif isinstance(struct[key], SchemaOperator):
                        __validate_structure(struct[key], name, authorized_types)
                    elif hasattr(struct[key], 'structure'):
                        __validate_structure(struct[key], name, authorized_types)
                    elif struct[key] not in authorized_types:
                        ok = False
                        for auth_type in authorized_types:
                            if struct[key] is None:
                                ok = True
                            else:
                                try:
                                    if isinstance(struct[key], auth_type) or issubclass(struct[key], auth_type):
                                        ok = True
                                except TypeError:
                                    raise TypeError("%s: %s is not a type" % (name, struct[key]))
                        if not ok:
                            raise StructureError(
                                "%s: %s is not an authorized type" % (name, struct[key]))
            elif isinstance(struct, list) or isinstance(struct, tuple):
                for item in struct:
                    __validate_structure(item, name, authorized_types)
            elif isinstance(struct, SchemaOperator):
                if isinstance(struct, IS):
                    for operand in struct:
                        if type(operand) not in authorized_types:
                            raise StructureError("%s: %s in %s is not an authorized type (%s found)" % (
                                name, operand, struct, type(operand).__name__))
                else:
                    for operand in struct:
                        if operand not in authorized_types:
                            raise StructureError("%s: %s in %s is not an authorized type (%s found)" % (
                                name, operand, struct, type(operand).__name__))
            elif isinstance(struct, SchemaProperties):
                pass
            else:
                ok = False
                for auth_type in authorized_types:
                    if isinstance(struct, auth_type):
                        ok = True
                if not ok:
                    raise StructureError("%s: %s is not an authorized_types" % (name, struct))
        #################
        if structure is None:
            raise StructureError("%s.structure must not be None" % name)
        if not isinstance(structure, dict):
            raise StructureError("%s.structure must be a dict instance" % name)
        __validate_structure(structure, name, authorized_types)

    def _raise_exception(self, exception, field, message):
        if self.raise_validation_errors:
            raise exception(message)
        else:
            if not field in self.validation_errors:
                self.validation_errors[field] = []
            self.validation_errors[field].append(exception(message))

    def _validate_doc(self, doc, struct, path=""):
        """
        check if doc field types match the doc field structure
        """
        if type(struct) is type or struct is None:
            if struct is None:
                if type(doc) not in self.authorized_types:
                    self._raise_exception(AuthorizedTypeError, type(doc).__name__,
                                          "%s is not an authorized types" % type(doc).__name__)
            elif not isinstance(doc, struct) and doc is not None:
                self._raise_exception(SchemaTypeError, path,
                                      "%s must be an instance of %s not %s" % (
                                          path, struct.__name__, type(doc).__name__))
        elif isinstance(struct, CustomType):
            if not isinstance(doc, struct.mongo_type) and doc is not None:
                self._raise_exception(SchemaTypeError, path,
                                      "%s must be an instance of %s not %s" % (
                                          path, struct.mongo_type.__name__, type(doc).__name__))
            struct.validate(doc, path=path)
        elif isinstance(struct, SchemaOperator):
            if not struct.validate(doc) and doc is not None:
                if isinstance(struct, IS):
                    self._raise_exception(SchemaTypeError, path,
                                          "%s must be in %s not %s" % (path, struct._operands, doc))
                else:
                    self._raise_exception(SchemaTypeError, path,
                                          "%s must be an instance of %s not %s" % (path, struct, type(doc).__name__))
        elif isinstance(struct, dict):
            if not isinstance(doc, type(struct)):
                self._raise_exception(SchemaTypeError, path,
                                      "%s must be an instance of %s not %s" % (
                                          path, type(struct).__name__, type(doc).__name__))
            struct_length = len(struct) if not '_id' in struct else len(struct) - 1
            if len(doc) != struct_length:
                struct_doc_diff = list(set(struct).difference(set(doc)))
                if struct_doc_diff:
                    for field in struct_doc_diff:
                        if (type(field) is not type) and (not self.use_schemaless):
                            self._raise_exception(StructureError, None,
                                                  "missed fields %s in %s" % (struct_doc_diff, type(doc).__name__))
                else:
                    struct_struct_diff = list(set(doc).difference(set(struct)))
                    bad_fields = [s for s in struct_struct_diff if s not in STRUCTURE_KEYWORDS]
                    if bad_fields and not self.use_schemaless:
                        self._raise_exception(StructureError, None,
                                              "unknown fields %s in %s" % (bad_fields, type(doc).__name__))
            for key in struct:
                if type(key) is type:
                    new_key = "$%s" % key.__name__
                else:
                    new_key = key
                new_path = ".".join([path, new_key]).strip('.')
                if new_key.split('.')[-1].startswith("$"):
                    for doc_key in doc:
                        if not isinstance(doc_key, key):
                            self._raise_exception(SchemaTypeError, path,
                                                  "key of %s must be an instance of %s not %s" % (
                                                      path, key.__name__, type(doc_key).__name__))
                        self._validate_doc(doc[doc_key], struct[key], new_path)
                else:
                    if key in doc:
                        self._validate_doc(doc[key], struct[key],  new_path)
        elif isinstance(struct, list):
            if not isinstance(doc, list) and not isinstance(doc, tuple):
                self._raise_exception(SchemaTypeError, path,
                                      "%s must be an instance of list not %s" % (path, type(doc).__name__))
            if not len(struct):
                struct = None
            else:
                struct = struct[0]
            for obj in doc:
                self._validate_doc(obj, struct, path)
        elif isinstance(struct, tuple):
            if not isinstance(doc, list) and not isinstance(doc, tuple):
                self._raise_exception(SchemaTypeError, path,
                                      "%s must be an instance of list not %s" % (
                                          path, type(doc).__name__))
            if len(doc) != len(struct):
                self._raise_exception(SchemaTypeError, path, "%s must have %s items not %s" % (
                    path, len(struct), len(doc)))
            for i in range(len(struct)):
                self._validate_doc(doc[i], struct[i], path)

    def _process_validators(self, doc, _struct, _path=""):
        doted_doc = DotCollapsedDict(doc)
        for key, validators in self.validators.iteritems():
            if key in doted_doc and doted_doc[key] is not None:
                if not hasattr(validators, "__iter__"):
                    validators = [validators]
                for validator in validators:
                    try:
                        if not validator(doted_doc[key]):
                            raise ValidationError("%s does not pass the validator " + validator.__name__)
                    except Exception, e:
                        self._raise_exception(ValidationError, key,
                                              unicode(e) % key)

    def _process_custom_type(self, target, doc, struct, path="", root_path=""):
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
                    if key in doc:
                        if struct[key].python_type is not None:
                            if not isinstance(doc[key], struct[key].python_type) and doc[key] is not None:
                                self._raise_exception(SchemaTypeError, new_path,
                                                      "%s must be an instance of %s not %s" % (
                                                          new_path, struct[key].python_type.__name__,
                                                          type(doc[key]).__name__))
                        doc[key] = struct[key].to_bson(doc[key])
                else:
                    if key in doc:
                        doc[key] = struct[key].to_python(doc[key])
            elif isinstance(struct[key], dict):
                if doc:  # we don't need to process an empty doc
                    if type(key) is type:
                        for doc_key in doc:  # process type's key such {unicode:int}...
                            self._process_custom_type(target, doc[doc_key], struct[key], new_path, root_path)
                    else:
                        if key in doc:  # we don't care about missing fields
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
                            if target == 'bson':
                                if struct[key][0].python_type is not None:
                                    if not isinstance(obj, struct[key][0].python_type) and obj is not None:
                                        self._raise_exception(SchemaTypeError, new_path,
                                                              "%s must be an instance of %s not %s" % (
                                                                  new_path, struct[key][0].python_type.__name__,
                                                                  type(obj).__name__))
                                obj = struct[key][0].to_bson(obj)
                            else:
                                obj = struct[key][0].to_python(obj)
                            l_objs.append(obj)
                        doc[key] = l_objs
                    elif isinstance(struct[key][0], dict):
                        if doc.get(key):
                            for obj in doc[key]:
                                self._process_custom_type(target, obj, struct[key][0], new_path, root_path)

    def _set_default_fields(self, doc, struct, path=""):
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
                    elif isinstance(new_value, dict):
                        new_value = deepcopy(new_value)
                    elif isinstance(new_value, list):
                        new_value = new_value[:]
                    if isinstance(struct[key], CustomType):
                        if not isinstance(new_value, struct[key].python_type):
                            self._raise_exception(DefaultFieldTypeError, new_path,
                                                  "%s must be an instance of %s not %s" % (
                                                      new_path, struct[key].python_type.__name__,
                                                      type(new_value).__name__))
                    doc[key] = new_value
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and new_path not in self.i18n:
                #
                # if the dict is still empty into the document we build
                # it with None values
                #
                if len(struct[key]) and not [i for i in struct[key].keys() if type(i) is type]:
                    self._set_default_fields(doc[key], struct[key], new_path)
                else:
                    if new_path in self.default_values:
                        new_value = self.default_values[new_path]
                        if callable(new_value):
                            new_value = new_value()
                        elif isinstance(new_value, dict):
                            new_value = deepcopy(new_value)
                        elif isinstance(new_value, list):
                            new_value = new_value[:]
                        doc[key] = new_value
            elif isinstance(struct[key], list):
                if new_path in self.default_values:
                    for new_value in self.default_values[new_path]:
                        if callable(new_value):
                            new_value = new_value()
                        elif isinstance(new_value, dict):
                            new_value = deepcopy(new_value)
                        elif isinstance(new_value, list):
                            new_value = new_value[:]
                        if isinstance(struct[key][0], CustomType):
                            if not isinstance(new_value, struct[key][0].python_type):
                                self._raise_exception(DefaultFieldTypeError, new_path,
                                                      "%s must be an instance of %s not %s" % (
                                                          new_path, struct[key][0].python_type.__name__,
                                                          type(new_value).__name__))
                        doc[key].append(new_value)
            else:  # what else
                if new_path in self.default_values:
                    new_value = self.default_values[new_path]
                    if callable(new_value):
                        new_value = new_value()
                    elif isinstance(new_value, dict):
                        new_value = deepcopy(new_value)
                    elif isinstance(new_value, list):
                        new_value = new_value[:]
                    if new_path in self.i18n:
                        doc[key] = i18n(
                            field_type=struct[key],
                            field_name=key
                        )
                        doc[key].update(new_value)
                    else:
                        doc[key] = new_value

    def _validate_required(self, doc, _struct, _path="", _root_path=""):
        doted_struct = DotCollapsedDict(self.structure)
        doted_doc = DotCollapsedDict(doc, reference=doted_struct)
        for req in self.required_fields:
            if doted_doc.get(req) is None and doted_struct.get(req) is not dict:
                if not isinstance(doted_struct.get(req), CustomType):
                    self._raise_exception(RequireFieldError, req, "%s is required" % req)
                elif isinstance(doted_struct.get(req), CustomType) and doted_struct[req].mongo_type is not dict:
                    self._raise_exception(RequireFieldError, req, "%s is required" % req)
            elif doted_doc.get(req) == []:
                self._raise_exception(RequireFieldError, req, "%s is required" % req)
            elif doted_doc.get(req) == {}:
                self._raise_exception(RequireFieldError, req, "%s is required" % req)

    def __generate_skeleton(self, doc, struct, path=""):
        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is not type and key not in doc:
                if isinstance(struct[key], dict):
                    if type(struct[key]) is dict and self.use_dot_notation:
                        if new_path in self._i18n_namespace:
                            doc[key] = i18nDotedDict(doc.get(key, {}), self)
                        else:
                            doc[key] = DotedDict(doc.get(key, {}), warning=self.dot_notation_warning)
                    else:
                        if callable(struct[key]):
                            doc[key] = struct[key]()
                        else:
                            doc[key] = type(struct[key])()
                elif struct[key] is dict:
                    doc[key] = {}
                elif isinstance(struct[key], list):
                    doc[key] = type(struct[key])()
                elif isinstance(struct[key], CustomType):
                    if struct[key].init_type is not None:
                        doc[key] = struct[key].init_type()
                    else:
                        doc[key] = None
                elif struct[key] is list:
                    doc[key] = []
                elif isinstance(struct[key], tuple):
                    doc[key] = [None for _ in range(len(struct[key]))]
                else:
                    doc[key] = None
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and type(key) is not type:
                self.__generate_skeleton(doc[key], struct[key], new_path)

    def __generate_doted_dict(self, doc, struct, path=""):
        for key in struct:
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            if type(key) is not type:  # and key not in doc:
                if isinstance(struct[key], dict):
                    if type(struct[key]) is dict:
                        if new_path in self._i18n_namespace:
                            doc[key] = i18nDotedDict(doc.get(key, {}), self)
                        else:
                            doc[key] = DotedDict(doc.get(key, {}), warning=self.dot_notation_warning)
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and type(key) is not type:
                self.__generate_doted_dict(doc[key], struct[key], new_path)

    def _make_i18n(self):
        doted_dict = DotCollapsedDict(self.structure)
        for field in self.i18n:
            if field not in doted_dict:
                self._raise_exception(ValidationError, field,
                                      "%s not found in structure" % field)
            if not isinstance(doted_dict[field], i18n):
                doted_dict[field] = i18n(
                    field_type=doted_dict[field],
                    field_name=field
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
            for l, v in value.iteritems():
                if isinstance(v, list) and isinstance(self._field_type, list):
                    for i in v:
                        if not isinstance(i, self._field_type[0]):
                            raise SchemaTypeError("%s (%s) must be an instance of %s not %s" % (
                                self._field_name, l, self._field_type[0], type(i).__name__))
                else:
                    if not isinstance(v, self._field_type):
                        raise SchemaTypeError("%s (%s) must be an instance of %s not %s" % (
                                              self._field_name, l, self._field_type, type(v).__name__))
            return [{'lang': l, 'value': v} for l, v in value.iteritems()]

    def to_python(self, value):
        if value is not None:
            i18n_dict = self.__class__(self._field_type)
            for i in value:
                i18n_dict[i['lang']] = i['value']
            return i18n_dict


class Set(CustomType):
    """ SET custom type to handle python set() type """
    init_type = set
    mongo_type = list
    python_type = set

    def __init__(self, structure_type=None):
        super(Set, self).__init__()
        self._structure_type = structure_type

    def to_bson(self, value):
        if value is not None:
            return list(value)

    def to_python(self, value):
        if value is not None:
            return set(value)

    def validate(self, value, path):
        if value is not None and self._structure_type is not None:
            for val in value:
                if not isinstance(val, self._structure_type):
                    raise ValueError('%s must be an instance of %s not %s' %
                                     (path, self._structure_type.__name__, type(val).__name__))
