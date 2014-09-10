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

from mongokit.mongo_exceptions import AutoReferenceError
from mongokit.mongo_exceptions import OptionConflictError
from mongokit.mongo_exceptions import BadIndexError
from mongokit.mongo_exceptions import MaxDocumentSizeError
from mongokit.mongo_exceptions import MultipleResultsFound
from mongokit.mongo_exceptions import ConnectionError
from mongokit.mongo_exceptions import OperationFailure

from mongokit.schema_document import (
    STRUCTURE_KEYWORDS,
    CustomType,
    SchemaTypeError,
    SchemaProperties,
    SchemaDocument,
    StructureError)
from mongokit.helpers import (
    totimestamp,
    fromtimestamp,
    DotedDict)
from mongokit.grid import FS
import pymongo
from bson import BSON
from bson.binary import Binary
from bson.code import Code
from bson.dbref import DBRef
from bson.objectid import ObjectId
import re
from copy import deepcopy
from uuid import UUID, uuid4
import logging
import datetime

STRUCTURE_KEYWORDS += ['_id', '_ns', '_revision', '_version']

log = logging.getLogger(__name__)


class DocumentProperties(SchemaProperties):
    def __new__(mcs, name, bases, attrs):
        for base in bases:
            parent = base.__mro__[0]
            if hasattr(parent, 'structure'):
                if parent.structure is not None:
                    #parent = parent()
                    if parent.indexes:
                        if 'indexes' not in attrs:
                            attrs['indexes'] = []
                        for index in attrs['indexes']+parent.indexes:
                            if index not in attrs['indexes']:
                                attrs['indexes'].append(index)
        return SchemaProperties.__new__(mcs, name, bases, attrs)

    @classmethod
    def _validate_descriptors(mcs, attrs):
        SchemaProperties._validate_descriptors(attrs)
        # validate index descriptor
        if attrs.get('migration_handler') and attrs.get('use_schemaless'):
            raise OptionConflictError('You cannot set a migration_handler with use_schemaless set to True')
        if attrs.get('indexes'):
            for index in attrs['indexes']:
                if index.get('check', True):
                    if 'fields' not in index:
                        raise BadIndexError(
                            "'fields' key must be specify in indexes")
                    for key, value in index.iteritems():
                        if key == "fields":
                            if isinstance(value, basestring):
                                if value not in attrs['_namespaces'] and value not in STRUCTURE_KEYWORDS:
                                    raise ValueError(
                                        "Error in indexes: can't find %s in structure" % value)
                            elif isinstance(value, tuple):
                                if len(value) != 2:
                                    raise BadIndexError(
                                        "Error in indexes: a tuple must contain "
                                        "only two value : the field name and the direction")
                                if not (isinstance(value[1], int) or isinstance(value[1], basestring)):
                                    raise BadIndexError(
                                        "Error in %s, the direction must be int or basestring "
                                        "(got %s instead)" % (value[0], type(value[1])))
                                if not isinstance(value[0], basestring):
                                    raise BadIndexError(
                                        "Error in %s, the field name must be string "
                                        "(got %s instead)" % (value[0], type(value[0])))
                                if value[0] not in attrs['_namespaces'] and value[0] not in STRUCTURE_KEYWORDS:
                                    raise ValueError(
                                        "Error in indexes: can't find %s in structure" % value[0])
                                if not value[1] in [pymongo.DESCENDING, pymongo.ASCENDING, pymongo.OFF, pymongo.ALL,
                                                    pymongo.GEO2D, pymongo.GEOHAYSTACK, pymongo.GEOSPHERE,
                                                    pymongo.HASHED, "text"]:
                                    raise BadIndexError(
                                        "index direction must be INDEX_DESCENDING, INDEX_ASCENDING, "
                                        "INDEX_OFF, INDEX_ALL, INDEX_GEO2D, INDEX_GEOHAYSTACK, "
                                        "or INDEX_GEOSPHERE. Got %s" % value[1])  # Omit text because it's still beta
                            elif isinstance(value, list):
                                for val in value:
                                    if isinstance(val, tuple):
                                        field, direction = val
                                        if field not in attrs['_namespaces'] and field not in STRUCTURE_KEYWORDS:
                                            raise ValueError(
                                                "Error in indexes: can't find %s in structure" % field)
                                        if not direction in [pymongo.DESCENDING, pymongo.ASCENDING, pymongo.OFF,
                                                             pymongo.ALL, pymongo.GEO2D, pymongo.GEOHAYSTACK,
                                                             pymongo.GEOSPHERE, "text"]:
                                            raise BadIndexError(
                                                "index direction must be INDEX_DESCENDING, INDEX_ASCENDING, INDEX_OFF, "
                                                "INDEX_ALL, INDEX_GEO2D, INDEX_GEOHAYSTACK, or INDEX_GEOSPHERE."
                                                " Got %s" % direction)  # Omit text because it's still beta
                                    else:
                                        if val not in attrs['_namespaces'] and val not in STRUCTURE_KEYWORDS:
                                            raise ValueError("Error in indexes: can't find %s in structure" % val)
                            else:
                                raise BadIndexError("fields must be a string, a tuple or a list of tuple "
                                                    "(got %s instead)" % type(value))
                        elif key == "ttl":
                            assert isinstance(value, int)


class Document(SchemaDocument):

    __metaclass__ = DocumentProperties

    type_field = '_type'

    atomic_save = False  # XXX Deprecated
    skip_validation = False
    use_autorefs = False
    force_autorefs_current_db = False
    indexes = []
    gridfs = []
    migration_handler = None

    authorized_types = SchemaDocument.authorized_types + [
        Binary,
        ObjectId,
        DBRef,
        Code,
        UUID,
        type(re.compile("")),
    ]

    def __init__(self, doc=None, gen_skel=True, collection=None, lang='en', fallback_lang='en'):
        self._authorized_types = self.authorized_types[:]
        # If using autorefs, we need another authorized
        if self.use_autorefs:
            self._authorized_types += [Document, SchemaProperties]
        super(Document, self).__init__(doc=doc, gen_skel=gen_skel, _gen_auth_types=False,
                                       lang=lang, fallback_lang=fallback_lang)
        if self.type_field in self:
            self[self.type_field] = unicode(self.__class__.__name__)
        # collection
        self.collection = collection
        if collection:
            self.db = collection.database
            self.connection = self.db.connection
            # indexing all embed doc if any (autorefs feature)
            self._dbrefs = {}
            if self.use_autorefs and collection:
                self._make_reference(self, self.structure)
            # gridfs
            if self.gridfs:
                self.fs = FS(self)
        else:
            self.fs = None
        if self.migration_handler:
            self.skip_validation = False
            self._migration = self.migration_handler(self.__class__)
            if self.get('_id'):
                Document.validate(self, auto_migrate=True)
        if self.atomic_save is True:
            raise DeprecationWarning('atomic_save is not supported anymore. Please update you code')

    def migrate(self, safe=True, _process_to_bson=True):
        """
        migrate the document following the migration_handler rules

        safe : if True perform a safe update (see pymongo documentation for more details
        """
        self._migrate(safe=safe)

    def _migrate(self, safe=True, process_to_bson=True):
        if process_to_bson:
            self._process_custom_type('bson', self, self.structure)
        self._migration.migrate(self, safe=safe)
        # reload
        old_doc = self.collection.get_from_id(self['_id'])
        if not old_doc:
            raise OperationFailure('Can not reload an unsaved document.'
                                   ' %s is not found in the database' % self['_id'])
        else:
            self.update(DotedDict(old_doc))
        self._process_custom_type('python', self, self.structure)

    def _get_size_limit(self):
        server_version = tuple(self.connection.server_info()['version'].split("."))
        mongo_1_8 = tuple("1.8.0".split("."))

        if server_version < mongo_1_8:
            return (3999999, '4MB')
        else:
            return (15999999, '16MB')

    def validate(self, auto_migrate=False):
        if self.use_autorefs:
            if not auto_migrate:
                # don't make reference if auto_migrate is True because this
                # mean validate was called from __init__ and no collection is
                # found when validating at __init__ with autorefs
                self._make_reference(self, self.structure)
        size = self.get_size()
        (size_limit, size_limit_str) = self._get_size_limit()

        if size > size_limit:
            raise MaxDocumentSizeError("The document size is too big, documents "
                                       "lower than %s is allowed (got %s bytes)" % (size_limit_str, size))
        if auto_migrate:
            error = None
            try:
                super(Document, self).validate()
            except StructureError, e:
                error = e
            except KeyError, e:
                error = e
            except SchemaTypeError, e:
                error = e
            if error:
                if not self.migration_handler:
                    raise StructureError(str(error))
                else:
                    # if we are here that's becose super.validate failed
                    # but it has processed custom type to bson.
                    self._migrate(process_to_bson=False)
        else:
            super(Document, self).validate()

    def get_size(self):
        """
        return the size of the underlying bson object
        """
        try:
            size = len(BSON.encode(self))
        except:
            self._process_custom_type('bson', self, self.structure)
            size = len(BSON.encode(self))
            self._process_custom_type('python', self, self.structure)
        return size

    def find(self, *args, **kwargs):
        """
        Query the database.

        The `spec` argument is a prototype document that all results must
        match. For example if self si called MyDoc:

        >>> mydocs = db.test.MyDoc.find({"hello": "world"})

        only matches documents that have a key "hello" with value "world".
        Matches can have other keys *in addition* to "hello". The `fields`
        argument is used to specify a subset of fields that should be included
        in the result documents. By limiting results to a certain subset of
        fields you can cut down on network traffic and decoding time.

        `mydocs` is a cursor which yield MyDoc object instances.

        See pymongo's documentation for more details on arguments.
        """
        return self.collection.find(wrap=self._obj_class, *args, **kwargs)

    def find_and_modify(self, *args, **kwargs):
        """
        Update and return an object.
        """
        return self.collection.find_and_modify(wrap=self._obj_class, *args, **kwargs)

    def find_one(self, *args, **kwargs):
        """
        Get the first object found from the database.

        See pymongo's documentation for more details on arguments.
        """
        return self.collection.find_one(wrap=self._obj_class, *args, **kwargs)

    def one(self, *args, **kwargs):
        """
        `one()` act like `find()` but will raise a
        `mongokit.MultipleResultsFound` exception if there is more than one
        result.

        If no document is found, `one()` returns `None`
        """
        bson_obj = self.find(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            try:
                doc = bson_obj.next()
            except StopIteration:
                doc = None
            return doc

    def find_random(self):
        """
        return one random document from the collection
        """
        import random
        max = self.collection.count()
        if max:
            num = random.randint(0, max-1)
            return self.find().skip(num).next()

    def find_fulltext(self, search, **kwargs):
        """
        Executes a full-text search. Additional parameters may be passed as keyword arguments.
        """
        rv = self.collection.database.command("text", self.collection.name, search=search, **kwargs)
        if 'results' in rv:
            for res in rv['results']:
                res['obj'] = self._obj_class(res['obj'])
        return rv

    def get_from_id(self, id):
        """
        return the document which has the id
        """
        return self.find_one({"_id": id})

    def fetch(self, spec=None, *args, **kwargs):
        """
        return all document which match the structure of the object
        `fetch()` takes the same arguments than the the pymongo.collection.find method.

        The query is launch against the db and collection of the object.
        """
        if spec is None:
            spec = {}
        for key in self.structure:
            if key in spec:
                if isinstance(spec[key], dict):
                    spec[key].update({'$exists': True})
            else:
                spec[key] = {'$exists': True}
        return self.find(spec, *args, **kwargs)

    def fetch_one(self, *args, **kwargs):
        """
        return one document which match the structure of the object
        `fetch_one()` takes the same arguments than the the pymongo.collection.find method.

        If multiple documents are found, raise a MultipleResultsFound exception.
        If no document is found, return None

        The query is launch against the db and collection of the object.
        """
        bson_obj = self.fetch(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return bson_obj.next()

    def reload(self):
        """
        allow to refresh the document, so after using update(), it could reload
        its value from the database.

        Be careful : reload() will erase all unsaved values.

        If no _id is set in the document, a KeyError is raised.
        """
        self._process_custom_type('bson', self, self.structure)
        old_doc = self.collection.get_from_id(self['_id'])
        if not old_doc:
            raise OperationFailure('Can not reload an unsaved document.'
                                   ' %s is not found in the database' % self['_id'])
        else:
            self.update(DotedDict(old_doc))
        self._process_custom_type('python', self, self.structure)

    def get_dbref(self):
        """
        return a pymongo DBRef instance related to the document
        """
        assert '_id' in self, "You must specify an '_id' for using this method"
        return DBRef(database=self.db.name, collection=self.collection.name, id=self['_id'])

    def save(self, uuid=False, validate=None, safe=True, *args, **kwargs):
        """
        save the document into the db.

        if uuid is True, a uuid4 will be automatically generated
        else, the bson.ObjectId will be used.

        If validate is True, the `validate` method will be called before
        saving. Not that the `validate` method will be called *before* the
        uuid is generated.

        `save()` follow the pymongo.collection.save arguments
        """
        if validate is True or (validate is None and self.skip_validation is False):
            self.validate(auto_migrate=False)
        else:
            if self.use_autorefs:
                self._make_reference(self, self.structure)
        if '_id' not in self:
            if uuid:
                self['_id'] = unicode("%s-%s" % (self.__class__.__name__, uuid4()))
        self._process_custom_type('bson', self, self.structure)
        self.collection.save(self, safe=safe, *args, **kwargs)
        self._process_custom_type('python', self, self.structure)

    def delete(self):
        """
        delete the document from the collection from his _id.
        """
        self.collection.remove({'_id': self['_id']})

    @classmethod
    def generate_index(cls, collection):
        """generate indexes from ``indexes`` class-attribute

        supports additional index-creation-keywords supported by pymongos ``ensure_index``.
        """
        # creating index if needed
        for index in deepcopy(cls.indexes):
            unique = False
            if 'unique' in index:
                unique = index.pop('unique')
            ttl = 300
            if 'ttl' in index:
                ttl = index.pop('ttl')

            given_fields = index.pop("fields", list())

            if isinstance(given_fields, tuple):
                fields = [given_fields]
            elif isinstance(given_fields, basestring):
                fields = [(given_fields, 1)]
            else:
                fields = []
                for field in given_fields:
                    if isinstance(field, basestring):
                        field = (field, 1)
                    fields.append(field)
            log.debug('Creating index for {}'.format(str(given_fields)))
            collection.ensure_index(fields, unique=unique, ttl=ttl, **index)

    def to_json_type(self):
        """
        convert all document field into json type
        and return the new converted object
        """
        def _convert_to_json(struct, doc):
            """
            convert all datetime to a timestamp from epoch
            """
            if struct is not None:
                for key in struct:
                    if isinstance(struct[key], datetime.datetime):
                        struct[key] = totimestamp(struct[key])
                    elif isinstance(struct[key], ObjectId):
                        #struct[key] = str(struct[key])
                        struct[key] = {'$oid': str(struct[key])}
                    elif isinstance(struct[key], dict):
                        _convert_to_json(struct[key], doc)
                    elif isinstance(struct[key], list) and len(struct[key]):
                        if isinstance(struct[key][0], dict):
                            for obj in struct[key]:
                                _convert_to_json(obj, doc)
                        elif isinstance(struct[key][0], datetime.datetime):
                            struct[key] = [totimestamp(obj) for obj in struct[key]]
                        elif isinstance(struct[key][0], ObjectId):
                            #struct[key] = [str(obj) for obj in struct[key]]
                            struct[key] = [{'$oid': str(obj)} for obj in struct[key]]
        # we don't want to touch our document so we create another object
        self._process_custom_type('bson', self, self.structure)
        obj = deepcopy(self)
        self._process_custom_type('python', self, self.structure)
        _convert_to_json(obj, obj)
        if '_id' in obj:
            if isinstance(obj['_id'], ObjectId):
                obj['_id'] = {'$oid': str(obj['_id'])}
        return obj

    def to_json(self):
        """
        convert the document into a json string and return it
        """
        def _convert_to_python(doc, struct):
            for key in struct:
                if isinstance(struct[key], dict):
                    if doc:  # we don't need to process an empty doc
                        if key in doc:  # we don't care about missing fields
                            _convert_to_python(doc[key], struct[key])
                elif type(struct[key]) is list:
                    if struct[key]:
                        if isinstance(struct[key][0], R):
                            l_objs = []
                            for obj in doc[key]:
                                obj['_collection'] = self.collection.name
                                obj['_database'] = self.db.name
                                l_objs.append(obj)
                            doc[key] = l_objs
                        elif isinstance(struct[key][0], dict):
                            if doc[key]:
                                for obj in doc[key]:
                                    _convert_to_python(obj, struct[key][0])
                else:
                    if isinstance(struct[key], R) and doc[key] is not None:
                        doc[key]['_collection'] = self.collection.name
                        doc[key]['_database'] = self.db.name
        try:
            from json import dumps
        except ImportError:
            from anyjson import serialize as dumps
        except ImportError:
            raise ImportError("can't import anyjson. Please install it before continuing.")
        obj = self.to_json_type()
        _convert_to_python(obj, self.structure)
        return unicode(dumps(obj))

    def from_json(self, json):
        """
        convert a json string and return a SchemaDocument
        """
        def _convert_to_python(doc, struct, path="", root_path=""):
            for key in struct:
                if type(key) is type:
                    new_key = '$%s' % key.__name__
                else:
                    new_key = key
                new_path = ".".join([path, new_key]).strip('.')
                if isinstance(struct[key], dict):
                    if doc:  # we don't need to process an empty doc
                        if key in doc:  # we don't care about missing fields
                            _convert_to_python(doc[key], struct[key], new_path, root_path)
                elif type(struct[key]) is list:
                    if struct[key]:
                        if struct[key][0] is datetime.datetime:
                            l_objs = []
                            for obj in doc[key]:
                                obj = fromtimestamp(obj)
                                l_objs.append(obj)
                            doc[key] = l_objs
                        elif isinstance(struct[key][0], R):
                            l_objs = []
                            for obj in doc[key]:
                                db = obj.get('_database') or obj.get('$db')
                                col = obj.get('_collection') or obj.get('$ref')
                                if '_id' in obj:
                                    id_ref = '_id'
                                    if '$oid' in obj['_id']:
                                        obj['_id'] = ObjectId(obj['_id']['$oid'])
                                elif '$id' in obj:
                                    id_ref = '$id'
                                obj_class = struct[key][0]._doc
                                _id = obj[id_ref]
                                obj = getattr(self.connection[db][col], obj_class.__name__).one({'_id': _id})
                                #obj = struct[key][0]._doc(obj, collection=self.connection[db][col]).get_dbref()
                                l_objs.append(obj)
                            doc[key] = l_objs
                        elif isinstance(struct[key][0], dict):
                            if doc[key]:
                                for obj in doc[key]:
                                    _convert_to_python(obj, struct[key][0], new_path, root_path)
                elif struct[key] is datetime.datetime and doc[key] is not None:
                    doc[key] = fromtimestamp(doc[key])
                elif (isinstance(struct[key], R) or isinstance(struct[key],
                                                               DocumentProperties)) and doc[key] is not None:
                    db = doc[key].get('_database') or doc[key].get('$db')
                    col = doc[key].get('_collection') or doc[key].get('$ref')
                    if '_id' in doc[key]:
                        id_ref = '_id'
                    elif '$id' in doc[key]:
                        id_ref = '$id'
                    if '$oid' in doc[key][id_ref]:
                        doc[key][id_ref] = ObjectId(doc[key][id_ref]['$oid'])
                    if isinstance(struct[key], R):
                        obj_class = struct[key]._doc
                    else:
                        obj_class = struct[key]
                    #_id = obj_class(doc[key], collection=self.connection[db][col])[id_ref]
                    _id = doc[key][id_ref]
                    doc[key] = getattr(self.connection[db][col], obj_class.__name__).one({'_id': _id})
        try:
            from json import loads
        except ImportError:
            from anyjson import deserialize as loads
        except ImportError:
            raise ImportError("can't import anyjson. Please install it before continuing.")
        obj = loads(json)
        _convert_to_python(obj, self.structure)
        if '_id' in obj:
            if '$oid' in obj['_id']:
                obj['_id'] = ObjectId(obj['_id']['$oid'])
        return self._obj_class(obj, collection=self.collection)

    #
    # End of public API
    #

    def __hash__(self):
        if '_id' in self:
            value = self['_id']
            return value.__hash__()
        else:
            raise TypeError("A Document is not hashable if it is not saved. Save the document before hashing it")

    def __deepcopy__(self, memo={}):
        obj = self.__class__(doc=deepcopy(dict(self), memo), gen_skel=False, collection=self.collection)
        obj.__dict__ = self.__dict__.copy()
        return obj

    def __getattribute__(self, key):
        if key in ['collection', 'db', 'connection']:
            if self.__dict__.get(key) is None:
                raise ConnectionError('No collection found')
        return super(Document, self).__getattribute__(key)

    def _make_reference(self, doc, struct, path=""):
        """
        * wrap all MongoDocument with the CustomType "R()"
        * create the list of Reference in self._dbrefs
        * track the embed doc changes and save it when self.save() is called
        """
        for key in struct:
            new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], SchemaProperties) or isinstance(struct[key], R):
                # if struct[key] is a MongoDocument, so we have to convert it into the
                # CustomType : R
                if not isinstance(struct[key], R):
                    db_name = None
                    if self.force_autorefs_current_db:
                        db_name = self.db.name
                    struct[key] = R(struct[key], self.connection, db_name)
                # if we have DBRef into the document we have to call
                # _process_custom_type another time.
                if isinstance(doc[key], DBRef):
                    # XXX check this
                    if doc[key].database:
                        db = doc[key].database
                    else:
                        db = self.db.name
                    col = doc[key].collection
                    _id = doc[key].id
                    obj_class = struct[key]._doc
                    doc[key] = getattr(self.connection[db][col], obj_class.__name__).one({'_id': _id})
                    #doc._process_custom_type('python', doc, doc.structure)
                # be sure that we have an instance of MongoDocument
                if not isinstance(doc[key], struct[key]._doc) and doc[key] is not None:
                    self._raise_exception(SchemaTypeError, new_path, "%s must be an instance of %s not %s" % (
                        new_path, struct[key]._doc.__name__, type(doc[key]).__name__))
                # validate the embed doc
                if not self.skip_validation and doc[key] is not None:
                    doc[key].validate()
                # if we didn't index the embed obj yet, well, we do it
                if new_path not in self._dbrefs:
                    if doc[key]:
                        self._dbrefs[new_path] = deepcopy(dict(doc[key]))
                    else:
                        self._dbrefs[new_path] = None
                else:
                    # if the embed doc indexed was None but not the new embed one,
                    # we update the index
                    if self._dbrefs[new_path] is None and doc[key] is not None:
                        doc[key].save()
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
                if len(struct[key]) and \
                        not [i for i in struct[key].keys() if type(i) is type]:
                    if key in doc:
                        self._make_reference(doc[key], struct[key], new_path)
                else:  # case {unicode:int}
                    pass
            elif isinstance(struct[key], list) and len(struct[key]):
                if isinstance(struct[key][0], SchemaProperties) or isinstance(struct[key][0], R):
                    if not isinstance(struct[key][0], R):
                        db_name = None
                        if self.force_autorefs_current_db:
                            db_name = self.db.name
                        struct[key][0] = R(struct[key][0], self.connection, db_name)
                    l_objs = []
                    for no, obj in enumerate(doc[key]):
                        if isinstance(obj, DBRef):
                            obj = getattr(self.connection[obj.database][obj.collection],
                                          struct[key][0]._doc.__name__).get_from_id(obj.id)
                        if not isinstance(obj, struct[key][0]._doc) and obj is not None:
                            self._raise_exception(SchemaTypeError, new_path, "%s must be an instance of Document "
                                                                             "not %s" % (new_path, type(obj).__name__))
                        full_new_path = "%s.%s" % (new_path, no)
                        # validate the embed doc
                        if not self.skip_validation:
                            obj.validate()
                        # if we didn't index the embed obj yet, well, we do it
                        if full_new_path not in self._dbrefs:
                            self._dbrefs[full_new_path] = obj
                        else:
                            # if the embed obj is already indexed, we check is the
                            # one we get has not changed. If so, we save the embed
                            # obj and update the reference
                            if self._dbrefs[full_new_path]['_id'] == obj['_id'] and self._dbrefs[full_new_path] != obj:
                                obj.save()
                                self._dbrefs[full_new_path].update(obj)
                        l_objs.append(obj)
                        doc[key] = l_objs
                elif isinstance(struct[key][0], dict):
                    for no, obj in enumerate(doc[key]):
                        self._make_reference(obj, struct[key][0], "%s.%s" % (new_path, no))


class R(CustomType):
    """ CustomType to deal with autorefs documents """
    mongo_type = DBRef
    python_type = Document

    def __init__(self, doc, connection, fallback_database=None):
        super(R, self).__init__()
        self._doc = doc
        self._fallback_database = fallback_database
        self.connection = connection

    def to_bson(self, value):
        if value is not None:
            return DBRef(database=value.db.name, collection=value.collection.name, id=value['_id'])

    def to_python(self, value):
        if value is not None:
            if not isinstance(value, DBRef):
                if '$ref' not in value:
                    value = value.get_dbref()
                else:
                    value = DBRef(database=value.get('$db'), collection=value['$ref'], id=value['$id'])
            if value.database:
                database = value.database
            else:
                database = self._fallback_database
            if database is None:
                raise RuntimeError("It appears that you try to use autorefs. I found a DBRef without"
                                   " database specified.\n If you do want to use the current database, you"
                                   " have to add the attribute `force_autorefs_current_db` as True. Please see the doc"
                                   " for more details.\n The DBRef without database is : %s " % value)
            col = self.connection[database][value.collection]
            doc = col.find_one({'_id': value.id})
            if doc is None:
                raise AutoReferenceError('Something wrong append. You probably change'
                                         ' your object when passing it as a value to an autorefs enable document.\n'
                                         'A document with id "%s" is not saved in the database "%s" but was giving as'
                                         ' a reference to a %s document' % (value.id, database, self._doc.__name__))
            return self._doc(doc, collection=col)
