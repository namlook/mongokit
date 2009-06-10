from mongokit import MongoDocument
from hashlib import sha512
import sha, os

class User(MongoDocument):
    structure = {
        "_id":unicode,
        "user":{
            "login":unicode,
            "password":unicode, # TODO validator
            "email":unicode,
        }
    }
    required_fields = ['user.password', 'user.email'] # what if openid ? password is None

    def set_login(self, login):
        self['_id'] = login
        self['user']['login'] = login

    def get_login(self):
        return self['_id']

    def del_login(self):
        self['_id'] = None
        self['user']['login'] = None

    login = property(get_login, set_login, del_login)

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

    def del_password(self):
        self['user']['password'] = None

    password = property(get_password, set_password, del_password)

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

    def get_email(self):
        return self['user']['email']

    def set_email(self, email):
        # TODO check if it's a well formated email
        self['user']['email'] = email

    def del_email(self):
        self['user']['email'] = None

    email = property(get_email, set_email, del_email)

    def save(self, *args, **kwargs):
        assert self['_id'] == self['user']['login']
        super(User, self).save(*args, **kwargs)
