"""
Replica Set integration with for MongoKit
Liyan Chang, liyan@filepicker.io
(same license as Mongokit)
"""

from pymongo.replica_set_connection import ReplicaSetConnection as PymongoReplicaSetConnection
from mongokit.connection import MongoKitConnection

class ReplicaSetConnection(MongoKitConnection, PymongoReplicaSetConnection):
    """ Replica Set support for MongoKit """

    def __init__(self, *args, **kwargs):
        # Specifying that it should run both the inits
        MongoKitConnection.__init__(self, *args, **kwargs)
        PymongoReplicaSetConnection.__init__(self, *args, **kwargs)

