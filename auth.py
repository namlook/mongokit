from mongokit import MongoDocument
from hashlib import sha512
import sha, os

class User(MongoDocument):
    structure = {
        "_id":unicode,
        "user":{
            "password":unicode,
            "email":unicode,
        }
    }
    required_fields = ['user.password', 'user.email'] # what if openid ? password is None

    def set_password(self, password):
        """ Hash password on the fly """
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        password_salt = sha.new(os.urandom(60)).hexdigest()
        crypt = sha.new(password + password_salt).hexdigest()
        self['user']['password'] = unicode(password_salt + crypt, 'utf-8')

    def get_password(self):
        """ Return the password hashed """
        return self['user']['password']

    password = property(get_password, set_password)

    def verify_password(self, password):
        """ Check the password against existing credentials  """
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        password_salt = self['user']['password'][:40]
        crypt_pass = sha.new(password + password_salt).hexdigest()
        if crypt_pass == self['user']['password'][40:]:
            return True
        else:
            return False
