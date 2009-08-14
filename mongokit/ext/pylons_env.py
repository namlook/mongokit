#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009, Brendan W. McAdams <bwmcadams@gmail.com>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the 
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of any future
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR 
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import threading
import logging
from pymongo.connection import Connection
from pymongo.errors import ConnectionFailure, InvalidName

from pylons import config, tmpl_context as c

log = logging.getLogger(__name__)

# NOTE: ThreadLocal will become problematic in the issue of running concurrent pylons apps
# in the same webserver.  The alternative is Pylons' StackedObjectProxy, but I found it 
# to act slightly weird for this type of use.  
# As SQLAlchemy uses threadlocal and works like a charm, so shall we.
# For details of the debate, see: 
# http://groups.google.com/group/pylons-devel/browse_thread/thread/508e7365164cc254

_threadlocal = threading.local()

class MongoPylonsEnv(object):
    """
    Helper class for using MongoKit inside of Pylons
    The recommended deployment is to add a call to init_mongo()
    in config/environment.py for your pylons project.
    Like with SQLAlchemy, this will setup your connections
    at Pylons boot; the MongoDB Pool code should ensure you have enough connections.
    
    Add the import at the top:
    
        >>> from mongokit.pylons_env import MongoPylonsEnv
    
    And lower down, in load_environment():

        >>> MongoPylonsEnv.init_mongo()
        
    Additionally, you'll need to add several items to your configuration ini file:
    
    
        ... # Mongo Database settings
        ... mongodb.host = localhost
        ... mongodb.port = 27017
        ... mongodb.db = your_db_name
        ... mongodb.connection_timeout = 30
        ... mongodb.pool.enable = True
        ... mongodb.pool.size = 20

    Then, you can pass keyword argument 'use_pylons' to your Document constructor, or 
    define attribute
        >>> _use_pylons = True 
    on your subclass.
    
    Alternately, for the ultimate in lazy: 
        
        >>> from mongokit.document import MongoPylonsDocument
        
    And then subclass from that (It's a proxy subclass of MongoDocument that enables use_pylons)    
    """
    @staticmethod
    def init_mongo():
        """
        Helper method for Pylons environment
        to initialize mongo.
        Calls mongo_conn() and ignores it's return value.
        """
        # Invoke to set it up but ignore return value
        MongoPylonsEnv.mongo_conn()


    @staticmethod
    def get_default_db():
        return config.get("mongodb.db", None)
        
    @staticmethod
    def mongo_conn():
        """
        Returns a copy of the threadlocal mongo connection.
        
        If one does not exist, it creates one and saves it in the threadlocal.
        
        The parameters for the connection are defined in the ini file, and pulled using 
        pylons.config()
        
        
        """
        if not hasattr(_threadlocal, 'mongo_conn'):
            try:
                conn_params = {'auto_start_request': True}
                conn_params['host'] = config.get('mongodb.host', 'localhost')
                conn_params['port'] = int(config.get('mongodb.port', 27017))
                conn_params['timeout'] = int(config.get('mongodb.connection_timeout', -1))
                if config.get('mongodb.pool.enable', False):
                    conn_params['pool_size'] = int(config.get('mongodb.pool.size', 0))

                # Make a connection to Mongo.
                try:
                    log.info("Attempting to open a Mongo connection with params: %s" % conn_params)
                    mongo_conn = Connection(**conn_params)
                except ConnectionFailure:
                    log.error("Failed to connect to Mongo with params %s.  Please check the service and try again." % conn_params)
                    raise
            
                _threadlocal.mongo_conn = mongo_conn
            except:
                log.exception("Error during Mongo connection / setup.")
                # Probably not ideal to kill the whole app, allow the upper stack to determine
                # An alternative
                #abort(500, 'Unable to connect to MongoDB Backend.')
                raise
            
        return _threadlocal.mongo_conn

