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

    Validators can be add in order to validate some values :

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
    """
    
    structure = None
    required_fields = []
    validators = {}

    db_host = "localhost"
    db_port = "21017"
    connection_path = None
    
    def __init__(self, doc={}, gen_skel=True):
        """
        doc : a document dictionnary
        gen_skel : if True, generate automaticly the skeleton of the doc
            filled with NoneType each time validate() is called
        """
        for k,v in doc.iteritems():
            self[k] = v
        if self.structure is None:
            raise ValueError("your document must have a structure defined")
        self.__validate_structure()
        self._namespaces = list(self.__walk_dict(self.structure))
        self.__gen_skel = gen_skel
        self.__validate_doc(self, self.structure, check_required = False)

    def __walk_dict(self, dic):
        for key, value in dic.items():
            if hasattr(value, 'keys'):
                for child_key in self.__walk_dict(value):
                    yield '%s.%s' % (key, child_key)
            else:
                if type(key) is not type:
                    yield key
                else:
                    yield ""

    def __validate_structure(self, struct=None):
        if struct is None:
            struct = self.structure
        for key in struct:
            assert isinstance(key, basestring), "%s must be a basestring" % key
            assert "." not in key
            assert not key.startswith('$')
            if type(struct[key]) is dict:
                if type in [type(k) for k,v in struct[key].iteritems()]:
                    assert k in authorized_types
                    assert v in authorized_types
                else:
                    self.__validate_structure(struct[key])
            elif type(struct[key]) is list:
                for value in struct[key]:
                    assert value in authorized_types
            else:
                assert struct[key] in authorized_types, "%s must not be %s but a type like %s" % (key, struct[key], authorized_types )

    def __validate_doc(self, doc, struct, check_required = True, path = ""):
        #if len(doc) != len(struct):
        #    raise ValueError( "missed fields : %s" % list(set(struct).difference(set(doc))))
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
                # if the dict is empty into the document we build it with None values
                #
                if not len(doc[key]) and new_path in self.required_fields and check_required:
                    raise ValueError( "%s is required" % new_path )
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
                    raise ValueError( "%s is required" % new_path )
                #
                # iterate over the list to check values type
                #
                for v in doc[key]:
                    assert type(v) is struct[key][0], "invalide type: %s must be a %s not %s" % (key,  struct[key][0].__name__, type(v).__name__)
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
                    raise ValueError( "%s is required" % new_path )
                #
                # check that the value pass througt the validator process
                #
                if new_path in self.validators:
                    assert self.validators[new_path](doc[key]), "%s does not pass the validator %s" % (doc[key], self.validators[new_path].__name__)

    def validate(self):
        self.__validate_doc(self, self.structure)

    def _get_connection(self):
        if self._connection is None:
            if connection_path is None:
                raise ValueError( "You must set a connection_path" )
            db_name, collection_name = self.connection_path.split('.')
            self._connection = Connection(self.db_host, self.db_port)[db_name][collection_name]
        return self._connection

    def save(self):
        if validate:
            self.validate()
        collection = self._get_collection()
        if collection is None:
            raise ValueError( "You must set a collection to this object before using save" )
        collection.save(self._doc)
