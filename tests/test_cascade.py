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

import unittest

from mongokit import *

class CascadeTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = Connection()['test']['mongokit']
        
    def tearDown(self):
        Connection()['test'].drop_collection('mongokit')
        Connection()['test'].drop_collection('_mongometa')

    def test_delete_cascade(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "spam":{"egg":int}
            }

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":{"bar":unicode},
            }
            belong_to = {'foo.bar':DocA}

        l_a = list(DocA.fetch())
        assert len(l_a) == 0, (len(l_a), l_a)
        l_b = list(DocB.fetch())
        assert len(l_b) == 0, (len(l_b), l_b)

        doca = DocA()
        doca['spam']['egg'] = 3
        doca.save()

        docb = DocB()
        docb['foo']['bar'] = doca['_id']
        docb.save()

        assert Connection()['test']['_mongometa'].find().count() == 1

        assert len(list(DocB.fetch())) == 1, len(list(DocB.fetch()))
        assert len(list(DocA.fetch())) == 1, len(list(DocA.fetch()))

        doca.delete(cascade=True)

        assert Connection()['test']['_mongometa'].find({'pobj.id':doca['_id']}).count() == 0, Connection()['test']['_mongometa'].find({'pobj.id':doca['_id']}).count()

        l_a = list(DocA.fetch())
        assert len(l_a) == 0, (len(l_a), l_a)
        l_b = list(DocB.fetch())
        assert len(l_b) == 0, (len(l_b), l_b)

        l = list(docb.collection.find())
        assert len(l) == 0

    def test_remove_cascade(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "spam":{"egg":int}
            }

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":{"bar":unicode},
            }
            belong_to = {'foo.bar':DocA}

        l_a = list(DocA.fetch())
        assert len(l_a) == 0, (len(l_a), l_a)
        l_b = list(DocB.fetch())
        assert len(l_b) == 0, (len(l_b), l_b)

        doca = DocA()
        doca['spam']['egg'] = 3
        doca.save()

        docb = DocB()
        docb['foo']['bar'] = doca['_id']
        docb.save()

        doca2 = DocA()
        doca2['spam']['egg'] = 2
        doca2.save()

        docb2 = DocB()
        docb2['foo']['bar'] = doca2['_id']
        docb2.save()

        assert len(list(DocB.fetch())) == 2, len(list(DocB.fetch()))
        assert len(list(DocA.fetch())) == 2, len(list(DocA.fetch()))

        DocA.remove({}, cascade=True)

        l_a = list(DocA.fetch())
        assert len(l_a) == 0, (len(l_a), l_a)
        l_b = list(DocB.fetch())
        assert len(l_b) == 0, (len(l_b), l_b)

        l = list(docb.collection.find())
        assert len(l) == 0

    def test_delete_cascade_different_db(self):
        Connection().drop_database('bla')
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "spam":{"egg":int}
            }

        class DocB(MongoDocument):
            db_name = "bla"
            collection_name = "mongokit"
            structure = {
                "foo":{"bar":unicode},
            }
            belong_to = {'foo.bar':DocA}

        class DocC(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":{"bar":unicode},
            }
            belong_to = {'foo.bar':DocB}


        l_a = list(DocA.fetch())
        assert len(l_a) == 0, (len(l_a), l_a)
        l_b = list(DocB.fetch())
        assert len(l_b) == 0, (len(l_b), l_b)
        l_c = list(DocC.fetch())
        assert len(l_c) == 0, (len(l_c), l_c)

        doca = DocA()
        doca['spam']['egg'] = 3
        doca.save()

        docb = DocB()
        docb['foo']['bar'] = doca['_id']
        docb.save()

        docc = DocC()
        docc['foo']['bar'] = docb['_id']
        docc.save()

        assert Connection()['test']['_mongometa'].find().count() == 1
        assert Connection()['bla']['_mongometa'].find().count() == 1

        assert len(list(DocB.fetch())) == 1, len(list(DocB.fetch()))
        assert len(list(DocA.fetch())) == 1, len(list(DocA.fetch()))
        assert len(list(DocC.fetch())) == 1, len(list(DocC.fetch()))

        doca.delete(cascade=True)

        l_a = list(DocA.fetch())
        assert len(l_a) == 0, (len(l_a), l_a)
        l_b = list(DocB.fetch())
        assert len(l_b) == 0, (len(l_b), l_b)
        l_c = list(DocC.fetch())
        assert len(l_c) == 0, (len(l_c), l_c)

        l = list(docb.collection.find())
        assert len(l) == 0
        assert Connection()['test']['_mongometa'].find().count() == 0
        assert Connection()['bla']['_mongometa'].find().count() == 0
        Connection().drop_database('bla')


    def test_bad_belong_to(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "spam":{"egg":int}
            }

        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":{"bar":unicode},
            }
            belong_to = {'foo.bar':int}

        doca = DocA()
        doca['spam']['egg'] = 3
        doca.save()

        self.assertRaises(ValueError, DocB)




