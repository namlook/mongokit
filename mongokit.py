import datetime
import pymongo
from pymongo.connection import Connection
import re

authorized_types = [type(None), bool, int, float, unicode, list, dict,
  datetime.datetime, 
  pymongo.binary.Binary,
  pymongo.objectid.ObjectId,
  pymongo.dbref.DBRef,
  pymongo.code.Code,
  type(re.compile("")),
]

class RequireFieldError(Exception):pass
class StructureError(Exception):pass
class BadKeyError(Exception):pass
class AuthorizedTypeError(Exception):pass
class ValidationError(Exception):pass
class ConnectionError(Exception):pass
class DuplicateRequiredError(Exception):pass
class DuplicateDefaultValueError(Exception):pass

class MongoDocument(dict):
    """
    A dictionnary with a building structured schema
    The validate method will check that the document
    match the underling structure

    The structure take the followin form:

        structure = {
            "key1":{
                "foo":int,
                "bar:{unicode:int}
            },
            "key2":{
                "spam":unicode,
                "eggs":[int]
            },
            "bla":float
        }

    authorized_types are listed in `mongokit.authorized_types`
    
    We can describe fields as required with the required attribute:

        required = ["keys1.foo", "bla"]

    Validators can be added in order to validate some values :

        validators = {
            "key1.foo":lambda x: x>5,
            "key2.spam": lambda x: x.startswith("miam")
        }

    A MongoDocument works just like dict:

        >>> my_doc = MongoDocument()
        >>> my_doc['key1']['foo'] = 42
        >>> my_doc['bla'] = 7.0
    
    Validation is made with the `validate()` methode:
        
        >>> my_doc.validate()
        >>> my_doc['key2']['spam'] = 2
        >>> my_doc.validate()
        <type 'exceptions.AssertionError'>: spam : 2 must not be int...
        >>> del my_doc["bla"]
        >>> my_doc.validate()
        <type 'exceptions.ValueError'>: bla is required

    Signals can be mapped to a field. Each time a field will changed, the function
    will be called:
        
        signals = {
            "key1.foo": lambda doc, value: doc['bla'] = unicode(value)
        }

    This means that each time key1.foo will be changed, the value of field "bla" will
    change to. You can make more complicated signals. A signals return nothing.
    """
    
    auto_inheritance = True
    structure = None
    required_fields = []
    default_values = {}
    validators = {}
    signals = {}

    db_host = "localhost"
    db_port = 27017
    connection_path = None
    
    def __init__(self, doc={}, gen_skel=True, auto_inheritance=True):
        """
        doc : a document dictionnary
        gen_skel : if True, generate automaticly the skeleton of the doc
            filled with NoneType each time validate() is called
        auto_inheritance: enable the automatic inheritance (default)
        """
        #
        # inheritance
        #
        if self.auto_inheritance and auto_inheritance:
            parent = self.__class__.__mro__[1]
            if hasattr(parent, "structure") and parent is not MongoDocument:
                parent = parent()
                if parent.structure:
                    self.structure.update(parent.structure)
                if parent.required_fields:
                    self.required_fields = list(set(self.required_fields+parent.required_fields))
                if parent.default_values:
                    obj_default_values = self.default_values.copy()
                    self.default_values = parent.default_values.copy()
                    self.default_values.update(obj_default_values)
                if parent.validators:
                    obj_validators = self.validators.copy()
                    self.validators = parent.validators.copy()
                    self.validators.update(obj_validators)
        # init
        self.__signals = {}
        for k,v in doc.iteritems():
            self[k] = v
        if self.structure is None:
            raise StructureError("your document must have a structure defined")
        self.__validate_structure()
        self._namespaces = list(self.__walk_dict(self.structure))
        self.__gen_skel = gen_skel
        if gen_skel:
            self.__validate_doc(self, self.structure, check_required = False)
        self._collection = None

    def __walk_dict(self, dic):
        # thanks jean_b for the patch
        for key, value in dic.items():
            if hasattr(value, 'keys'):
                for child_key in self.__walk_dict(value):
                    yield '%s.%s' % (key, child_key)
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
        self.__gen_skel = True
        self.__validate_doc(self, self.structure, check_required = False)

    def __validate_structure(self, struct=None):
        if struct is None:
            struct = self.structure
        if self.required_fields:
            if len(self.required_fields) != len(set(self.required_fields)):
                raise DuplicateRequiredError("duplicate required_fields : %s" % self.required_fields)
        for key in struct:
            assert isinstance(key, basestring), "%s must be a basestring" % key
            if "." in key: raise BadKeyError("%s must not contain '.'" % key)
            if key.startswith('$'): raise BadKeyError("%s must not start with '$'" % key)
            if type(struct[key]) is dict:
                if type in [type(k) for k,v in struct[key].iteritems()]:
                    if k not in authorized_types: raise AuthorizedTypeError("%s is not an authorized type" % k.__name__)
                    if v not in authorized_types: raise AuthorizedTypeError("%s is not an authorized type" % v.__name__)
                else:
                    self.__validate_structure(struct[key])
            elif type(struct[key]) is list:
                for value in struct[key]:
                    assert value in authorized_types
            else:
                assert struct[key] in authorized_types, "%s must not be %s but a type like %s" % (key, struct[key], authorized_types )

    def __validate_doc(self, doc, struct, check_required = True, path = ""):
        if check_required:
            if len(doc) != len(struct):
                struct_doc_diff = list(set(struct).difference(set(doc)))
                if struct_doc_diff:
                    raise StructureError( "missed fields : %s" % struct_doc_diff )
                else:
                    raise StructureError( "unknown fields : %s" % list(set(doc).difference(set(struct))))
        for key in struct:
            new_path = ".".join([path, key]).strip(".")
            #
            # Automatique generate the skeleton with NoneType
            #
            if self.__gen_skel:
                if not key in doc:
                    if hasattr(struct[key], "keys"):
                        doc[key] = {}
                    elif isinstance(struct[key], list):
                        doc[key] = []
                    else:
                        doc[key] = None
            #
            # key must match the structure
            # and its type must be authorized
            #
            assert key in struct, "incorrect field name : %s" % key
            assert type(doc[key]) in authorized_types, "%s: %s must not be %s but a type like %s" % (key, doc[key],type(doc[key]), authorized_types)
            #
            # if the value is a dict, we have a another structure to validate
            #
            if type(struct[key]) is dict:
                #
                # we check that the type value in the document is correct (must be a dict like in the structure)
                #
                assert type(doc[key]) is dict, "the value of %s must be a dict, not %s" % (key, type(doc[key]).__name__)
                #
                # if the list is empty and there are default values, we fill them
                #
                if not len(doc[key]) and new_path in self.default_values:
                    doc[new_path.split('.')[-1]] = self.default_values[new_path]
                #
                # if the dict is still empty into the document we build it with None values
                #
                if not len(doc[key]) and new_path in self.required_fields and check_required:
                    raise RequireFieldError( "%s is required" % new_path )
                #
                # It the dict is not a schema but a simply dictionnary with attempted values,
                # we iterate over these values and check their type
                #
                if type in [type(k) for k,v in struct[key].iteritems()]:
                    for k,v in doc[key].iteritems():
                        assert type(k) is struct[key].keys()[0], "invalide type : key of %s must be %s not %s" % (
                          new_path, struct[key].keys()[0].__name__, type(k).__name__)
                        assert type(v) is struct[key].values()[0], "invalide type : value of %s must be %s not %s" % (
                          new_path, struct[key].keys()[0].__name__, type(v).__name__)
                #
                # If the dict is a schema, we call __validate_doc again
                #
                else:
                    self.__validate_doc(doc[key], struct[key], check_required, new_path)
            #
            # If the struct is a list, we have to validate all values into it
            #
            elif type(struct[key]) is list:
                #
                # confirme that the document match the structure
                #
                assert type(doc[key]) is list, "the value of %s must be a list, not %s" % (key, type(doc[key]).__name__)
                #
                # if the list is empty and there are default values, we fill them
                #
                if not len(doc[key]) and new_path in self.default_values:
                    doc[new_path.split('.')[-1]] = self.default_values[new_path]
                #
                # check if the list must not be null
                #
                if not len(doc[key]) and new_path in self.required_fields and check_required:
                    raise RequireFieldError( "%s is required" % new_path )
                #
                # iterate over the list to check values type
                #
                for v in doc[key]:
                    if len(struct[key]) == 0:
                        if type(v) not in authorized_types:
                            raise AuthorizedTypeError("%s is not an authorized type" % v) 
                    elif type(v) is not struct[key][0]:
                        raise TypeError( "%s must be a %s not %s" % (key,  struct[key][0].__name__, type(v).__name__) )
            #
            # It is not a dict nor a list but a simple key:value
            #
            else:
                #
                # check if the value type is matching the on into the structure or is a NoneType
                #
                assert type(doc[key]) is struct[key] or type(doc[key]) is type(None), "invalide type : %s must be a %s not %s" % (
                  key, struct[key].__name__, type(doc[key]).__name__)
                #
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
                # check if the value must not be null
                #
                if doc[key] is None and new_path in self.required_fields and check_required:
                    raise RequireFieldError( "%s is required" % new_path )
                #
                # check that the value pass througt the validator process
                #
                if new_path in self.validators and check_required and doc[key] is not None:
                    if not self.validators[new_path](doc[key]):
                        raise ValidationError("%s does not pass the validator %s" % (doc[key], self.validators[new_path].__name__))
                if new_path in self.signals and check_required:
                    make_signal = False
                    if new_path in self.__signals:
                        if doc[key] != self.__signals[new_path]:
                            make_signal = True
                    else:
                        make_signal = True
                    if make_signal:
                        self.signals[new_path](self, doc[key])
                        self.__signals[new_path] = doc[key]

    def validate(self):
        self.__validate_doc(self, self.structure)

    def save(self):
        self.validate()
        collection = self.__class__.collection()
        if collection is None:
            raise ValueError( "You must set a collection to this object before using save" )
        collection.save(self)

    @classmethod
    def collection(cls):
        print cls.connection_path
        if cls.connection_path is None:
            raise ConnectionError( "You must set a connection_path" )
        db_name, collection_name = cls.connection_path.split('.')
        return Connection(cls.db_host, cls.db_port)[db_name][collection_name]


