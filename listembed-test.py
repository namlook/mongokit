try:
     import unittest2 as unittest
except ImportError:
     import unittest

from mongokit import Document, Connection

class DescriptorsTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit']
        
    def tearDown(self):
        self.connection.drop_database('test')
    
    def test_list_embed_dot_notation(self):
        """Attempt to set a default for a sub element using dot notation

        Either this or test_list_embed_list_notation should pass
        """

        class ListEmbed(Document):
            use_dot_notation = True
            structure = {
                'list': [
                    {
                        'name': basestring,
                        'age': int
                    }
                ]
            }

            default_values = {
                'list.name': 'default'
            }

        self.connection.register([ListEmbed])

        doc = self.col.ListEmbed()
        self.assertDictEqual(doc, {'list': []})

        doc.list.append({'age': 23})

        self.assertDictEqual(
            doc, {
                'list': [
                    {
                        'name': 'default',
                        'age': 23
                    }
                ]
            }
        )
    
    def test_list_embed_list_notation(self):
        """Attempt to set a default for a sub element using list notation

        Either this or test_list_embed_dot_notation should pass
        """

        class ListEmbed(Document):
            use_dot_notation = True
            structure = {
                'list': [
                    {
                        'name': basestring,
                        'age': int
                    }
                ]
            }

            default_values = {
                'list': [
                    {
                        'name': 'default'
                    }
                ]
            }

        self.connection.register([ListEmbed])

        doc = self.col.ListEmbed()
        self.assertDictEqual(doc, {'list': []})

        doc.list.append({'age': 23})

        self.assertDictEqual(
            doc, {
                'list': [
                    {
                        'name': 'default',
                        'age': 23
                    }
                ]
            }
        )

    def test_list_embed_non_required_fields(self):
        """Confirm all fields are not required"""

        class ListEmbed(Document):
            use_dot_notation = True
            structure = {
                'list': [
                    {
                        'name': basestring,
                        'age': int
                    }
                ]
            }

        self.connection.register([ListEmbed])

        doc = self.col.ListEmbed()
        self.assertDictEqual(doc, {'list': []})

        doc.list.append({'age': 23})

        self.assertDictEqual(
            doc, {
                'list': [
                    {
                        'age': 23
                    }
                ]
            }
        )

        # Should validate fine
        doc.validate()

    def test_list_embed_required_fields_dot_notation(self):
        """Confirm list of object required field validation works"""

        class ListEmbed(Document):
            use_dot_notation = True
            structure = {
                'list': [
                    {
                        'name': basestring,
                        'age': int
                    }
                ]
            }

            required_fields = ['list.name']

        self.connection.register([ListEmbed])

        doc = self.col.ListEmbed()
        self.assertDictEqual(doc, {'list': []})

        doc.list = [{'name': 'bob'}]

        self.assertDictEqual(
            doc, {
                'list': [
                    {
                        'name': 'bob'
                    }
                ]
            }
        )

        # Should validate fine
        doc.validate()

        doc.list = [{'age': 23}]

        self.assertDictEqual(
            doc, {
                'list': [
                    {
                        'age': 23
                    }
                ]
            }
        )

        try:
            doc.validate()
            self.fail('Not a valid document')
        except:
            pass


if __name__ == '__main__':
    unittest.main()

