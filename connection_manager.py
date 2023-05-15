"""Contains the Connection Manager Class

Returns:
    psycopg2.connection: A connection to a postgres database
"""
import os
import psycopg2
import time
from config_manager import ConfigManager
from databases import Databases
from db_connection_type import DBConnectionType
from kubernetes import client, config
from logging_manager import LoggingManager


class ConnectionManager:
    """Opens and closes postgres database connections
    """

    def __init__(self):
        if not hasattr(ConnectionManager, 'kubernetes_connection'):
            ConnectionManager.kubernetes_connection = \
                self.connect_to_kubernetes()

    # initialize globals
    cm = ConfigManager()
    lm = LoggingManager()

    # provides postgres db connection
    @property
    def postgres_db_connection(self):
        """ Postgres db connection property

        Returns:
            psycopg2.connection: A connection to the postgres database
        """
        return self._conn

    # provides primary test db connection
    @property
    def primary_test_db_connection(self):
        """ Test primary test_db connection property

        Returns:
            psycopg2.connection: A connection to the test database
        """
        return self.primary_test_db_conn

    # provides replica test db connection
    @property
    def replica_test_db_connection(self):
        """ Test replica test_db connection property

        Returns:
            psycopg2.connection: A connection to the test database
        """
        return self.replica_test_db_conn

    # provides replica test db connection
    @property
    def replica_pod_db_connection(self):
        """ Test replica test_db connection property via replica pod

        Returns:
            psycopg2.connection: A connection to the test database
        """
        return self.replica_pod_db_conn

    # connects to postgres db and sets local connection variable
    def connect_to_postgres_db(self):
        """ Connects to the postgres database
            while allowing time to initialize
        """
        self._conn = None
        connection_attempt = 0
        connected = False

        # gets postgres wait for init values
        attempts = int(os.getenv('POSTGRES_CONN_ATTEMPTS'))
        interval = int(os.getenv('POSTGRES_CONN_INTERVAL'))

        # Allow time for postgres to initialize
        while connected is False:
            try:
                connection_attempt += 1
                LoggingManager.logger.debug('Connection attempt number:'
                                            + str(connection_attempt))

                # read connection parameters
                params = self.cm.get_postgres_connection_parameters()

                # connect to the PostgreSQL server
                self._conn = psycopg2.connect(**params)
                LoggingManager.logger.debug(
                    'Connecting to the postgres database...')
                self._conn.autocommit = True
                connected = True

            except (Exception, psycopg2.DatabaseError) as error:
                # wait for the desired period and try again
                # up to the allotted attempts
                if connection_attempt < attempts:
                    LoggingManager.logger.debug(
                        'Postgres is still initializing.')
                    time.sleep(interval)
                    continue
                else:
                    # log exception if postgres is not up within allotted time
                    LoggingManager.logger.error(error, exc_info=True)
                    self.close_connection(self._conn, Databases.POSTGRES,
                                          DBConnectionType.PRIMARY_SERVICE)

    # connects to test db and sets local connection variable
    def connect_to_primary_test_db(self):
        """ Connects to the primary test database
        """
        self.primary_test_db_conn = None

        try:
            # read connection parameters
            params = self.cm.get_test_db_connection_parameters(
                DBConnectionType.PRIMARY_SERVICE)
            # connect to the PostgreSQL server
            LoggingManager.logger.debug(
                'Connecting to the primary test database...')
            self.primary_test_db_conn = psycopg2.connect(**params)
            self.primary_test_db_conn.autocommit = True
        except (Exception, psycopg2.DatabaseError) as error:
            LoggingManager.logger.error(error, exc_info=True)
            self.close_connection(self.primary_test_db_conn,
                                  Databases.TEST_DB,
                                  DBConnectionType.PRIMARY_SERVICE)

    # connects to test db via replica service
    # and sets local connection variables
    def connect_to_replica_test_db_via_replica_service(self):
        """ Connects to the replica test database
        """
        self.replica_test_db_conn = None

        try:
            # read connection parameters
            params = self.cm.get_test_db_connection_parameters(
                DBConnectionType.REPLICA_SERVICE)
            # connect to the PostgreSQL server
            LoggingManager.logger.debug(
                'Connecting to the replica test '
                'database via the replica service...')
            self.replica_test_db_conn = psycopg2.connect(**params)
            self.replica_test_db_conn.autocommit = True
        except (Exception, psycopg2.DatabaseError) as error:
            LoggingManager.logger.error(error, exc_info=True)
            self.close_connection(self.replica_test_db_conn,
                                  Databases.TEST_DB,
                                  DBConnectionType.REPLICA_SERVICE)

        # connects to test db via replica service and
        # sets local connection variables
    def connect_to_replica_test_db_via_replica_pod(self, pod):
        """ Connects to the replica test database
        """
        self.replica_pod_db_conn = None

        try:
            # read connection parameters
            params = self.cm.get_test_db_connection_parameters(
                DBConnectionType.REPLICA_POD, pod)
            # connect to the PostgreSQL server
            LoggingManager.logger.debug(
                'Connecting to the replica test database via %s...',
                pod.metadata.name)
            self.replica_pod_db_conn = psycopg2.connect(**params)
            self.replica_pod_db_conn.autocommit = True
        except (Exception, psycopg2.DatabaseError) as error:
            LoggingManager.logger.error(error, exc_info=True)
            self.close_connection(self.replica_pod_db_conn,
                                  Databases.TEST_DB,
                                  DBConnectionType.REPLICA_POD)

    def connect_to_kubernetes(self):
        """Connects to the Kubernetes cluster that the container is running in.
        """

        LoggingManager.logger.debug("Connecting to kubernetes.")
        config.load_incluster_config()
        self.kube = client.CoreV1Api()

        return self.kube

    def close_connection(self, conn, Databases, DBConnectionType):
        """ Closes the database connection

        Args:
            conn psycopg2.connection: The database connection to be closed
            Databases Enum: The database whose connection is being closed
            DBConnectionType Enum: \
                The type of test_db connection being closed
        """
        if conn is None:
            return
        conn.close()

        if Databases == Databases.TEST_DB:
            match DBConnectionType:
                case DBConnectionType.PRIMARY_SERVICE:
                    LoggingManager.logger.debug('Primary Test Database '
                                                'connection closed.')
                    self.primary_test_db_conn = None
                case DBConnectionType.REPLICA_SERVICE:
                    LoggingManager.logger.debug('Replica Test Database '
                                                'connection closed.')
                    self.replica_test_db_conn = None
                case _:
                    LoggingManager.logger.debug('Replica Pod Database '
                                                'connection closed.')
                    self.replica_pod_db_conn = None
        else:
            LoggingManager.logger.debug('Postgres Database connection closed.')
            self._conn = None

    def close_kubernetes_connection(self):
        """Closes the connection to the Kubernetes cluster
        """
        ConnectionManager.kubernetes_connection.api_client.close()
        LoggingManager.logger.debug("Closed kubernetes connection.")
