Descriptors
===========

In the MongoKit philosophy, the structure must be simple, clear and readable.
So all descriptors (validation, requirement, default values, etc.) are
described outside the structure. Descriptors can be combined and applied to
the same field.

required
--------

This descriptor describes the required fields::

    class MyDoc(Document):
        structure = {
            'bar': basestring,
            'foo':{
                'spam': basestring,
                'eggs': int,
            }
        }
        required = ['bar', 'foo.spam']

If you want to reach nested fields, just use the dot notation.

default_values
--------------

This descriptor allows to specify a default value at the creation of the
document::

   class MyDoc(Document):
        structure = {
            'bar': basestring,
            'foo':{
                'spam': basestring,
                'eggs': int,
            }
        }
        default_values = {'bar': 'hello', 'foo.eggs': 4}

Note that the default value must be a valid type. Again, to reach nested
fields, use dot notation.

validators
----------

This descriptor brings a validation layer to a field. It takes a function which
returns ``False`` if the validation fails, ``True`` otherwise::

    import re
    def email_validator(value):
       email = re.compile(r'(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)',re.IGNORECASE)
       return bool(email.match(value))

    class MyDoc(Document):
       structure = {
          'email': basestring,
          'foo': {
            'eggs': int,
          }
       }
       validators = {
           'email': email_validator,
           'foo.eggs': lambda x: x > 10
       }

You can add custom message to your validators by throwing a ``ValidationError``
instead of returning ``False`` ::

    def email_validator(value):
       email = re.compile(r'(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)',re.IGNORECASE)
       if not email.match(value):
          raise ValidationError('%s is not a valid email' % value)

*Do you need to throw ValidatorError or any Exception -Ed *
Validato
Make sure to include one '%s' in the message. This will be used to refer to
the name of the field containing errors.

You can also pass params to your validator by wrapping it in a class::

    class MinLengthValidator(object):
        def __init__(self, min_length):
            self.min_length = min_length

        def __call__(self, value):
            if len(value) >= self.min_length:
                return True
            else:
                raise Exception('%s must be at least %d characters long.' % (value, self.min_length))

    class Client(Document):
        structure = {
          'first_name': basestring
        }
        validators = { 'first_name': MinLengthValidator(2) }

In this example, ``first_name`` must contain at least 2 characters.

Adding Complex Validation
^^^^^^^^^^^^^^^^^^^^^^^^^

If the use of a validator is not enough, you can overload the validation method
to fit your needs.

For example, take the following document::

    class MyDoc(Document):
        structure = {
            'foo': int,
            'bar': int,
            'baz': basestring
        }

We want to be sure before saving our object that foo is greater than bar. To
do that, we just overload the validation method::

    def validate(self, *args, **kwargs):
        assert self['foo'] > self['bar']
        super(MyDoc, self).validate(*args, **kwargs)

Skipping Validation
^^^^^^^^^^^^^^^^^^^

Once your application is ready for production and you are sure that the data is
consistent, you might want to skip the validation layer. This will make
MongoKit significantly faster (as fast as pymongo). In order to do that, just
set the ``skip_validation`` attribute to ``True``.

TIP: It is a good idea to create a ``RootDocument`` and to inherit all your
document classes from it. This will allow you to control the default behavior
of all your objects by setting attributes on the RootDocument::

    class RootDocument(Document):
        structure = {}
        skip_validation = True
        use_autorefs = True

    class MyDoc(RootDocument):
        structure = {
            'foo': int
        }

Note that you can always force the validation at any moment on saving even if
``skip_validation`` is ``True``:

>>> con.register([MyDoc]) # No need to register RootDocument as we do not instantiate it
>>> mydoc = tutorial.MyDoc()
>>> mydoc['foo'] = 'bar'
>>> mydoc.save(validate=True)
Traceback (most recent call last):
...
SchemaTypeError: foo must be an instance of int not basestring


Quiet Validation Detection
^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, when validation is on, each error raises an Exception. Sometimes,
you just want to collect all errors in one place. This is possible by setting
the ``raise_validation_errors`` to ``False``. This causes all errors to be stored
in the ``validation_errors`` attribute::

    class MyDoc(Document):
        raise_validation_errors = False
        structure = {
            'foo': set,
        }

>>> con.register([MyDoc])
>>> doc = tutorial.MyDoc()
>>> doc.validate()
>>> doc.validation_errors
{'foo': [StructureError("<type 'set'> is not an authorized type",), RequireFieldError('foo is required',)]}

``validation_errors`` is a dictionary which takes the field name as key and the
Python exception as value. There are two issues with foo here: one with it's structure (``set``
is not an authorized type) and another with required field (``foo`` is required
field but is not specified).

>>> doc.validation_errors['foo'][0].message
"<type 'set'> is not an authorized type"

Validate Keys
^^^^^^^^^^^^^

If the value of key is not known but we want to validate some deeper structure, 
we use the "$<type>" descriptor::

    class MyDoc(Document):
      structure = {
        'key': {
          unicode: {
            'first': int,
            'secondpart: {
              unicode: int
            }
          }
        }
      }

      required_fields = ["key1.$unicode.bla"]

Note that if you use a Python type as a key in structure, generate_skeleton
won't be able to build the entire underlying structure :

>>> con.register([MyDoc])
>>> tutorial.MyDoc() == {'key1': {}, 'bla': None}
True

So, neither default_values nor validators will work.

