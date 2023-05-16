""" Main module to run the PostgreSQL deployment tests

Raises:
    ValueError: If query row count doesn't match expected value raise an error.
"""
import os
import time
from connection_manager import ConnectionManager
from databases import Databases
from database_manager import DatabaseManager
from db_connection_type import DBConnectionType
from logging_manager import LoggingManager
from replica_manager import ReplicaManager
from sync_manager import SyncManager
from user_manager import UserManager


# initialize classes
lm = LoggingManager()
cm = ConnectionManager()
dbm = DatabaseManager()
rm = ReplicaManager()
um = UserManager()
sm = SyncManager()

global has_run_as_primary
global is_primary


def run_tests():
    """ Runs the PostgreSQL deployment tests

    Raises:
        ValueError: If query row count doesn't match
            expected value raise an error.
    """

    # Log entry for new test run
    LoggingManager.logger.info('******* STARTING NEW TEST RUN *******')

    try:
        # set locals
        conn = None
        primary_test_db_conn = None
        replica_test_db_conn = None
        replica_pod_db_conn = None
        cur = None
        primary_test_cur = None
        replica_test_cur = None
        replica_pod_cur = None

        # allow time for pod to full initialize
        time.sleep(5)
        global is_primary
        is_primary = is_host_primary_data_pod()
        if not is_primary:
            LoggingManager.logger.info("Not primary at test time. "
                                       "Please see primary data node "
                                       "self_test.log for test results.")

            # assigning last run state
            global has_run_as_primary
            has_run_as_primary = False
            return

        # get postgres database connection
        cm.connect_to_postgres_db()
        conn = cm.postgres_db_connection

        # get cursor
        if conn is not None:
            cur = conn.cursor()

            # print the current postgres version
            get_version(cur)

            # # create the test user
            um.create_test_user(cur)

            # switch from the postgres user to the test user
            um.switch_to_test_user(cur)

            # create the test database
            dbm.create_database(cur)
        else:
            err = 'Unable to connect to the postgres database'
            raise ConnectionError(err, conn)

        # connect to the primary test database with the test user
        cm.connect_to_primary_test_db()
        primary_test_db_conn = cm.primary_test_db_connection

        if primary_test_db_conn is not None:

            # get test_db cursor
            primary_test_cur = primary_test_db_conn.cursor()

            # create a test schema in the test database
            dbm.create_schema(primary_test_cur)

            # create a table with data in the test schema
            dbm.create_table(primary_test_cur)

            validate_data(primary_test_cur, DBConnectionType.PRIMARY_SERVICE)

        # allow time for replication to complete
        time.sleep(10)

        # connect to the replica test database
        # via the replica service with the test user
        rm.get_replica_pods()
        if rm.has_replicas is True:

            cm.connect_to_replica_test_db_via_replica_service()
            replica_test_db_conn = cm.replica_test_db_connection

            if replica_test_db_conn is not None:

                # get test_db cursor
                replica_test_cur = replica_test_db_conn.cursor()
                validate_data(replica_test_cur,
                              DBConnectionType.REPLICA_SERVICE)

            # validate data at each replica pod
            for pod in rm.replica_pod_list:
                cm.connect_to_replica_test_db_via_replica_pod(pod)
                replica_pod_db_conn = cm.replica_pod_db_connection
                replica_pod_cur = replica_pod_db_conn.cursor()
                validate_data(replica_pod_cur,
                              DBConnectionType.REPLICA_POD, pod)
                cleanup(replica_pod_cur, Databases.TEST_DB,
                        DBConnectionType.REPLICA_POD)
        else:
            LoggingManager.logger.warning("No replica pods detected. "
                                          "This postgres cluster is not "
                                          "highly available.")

        # assigning last run state
        has_run_as_primary = True

        # sync argocd app if auto-promote is enabled
        if os.getenv("AUTO_PROMOTE").lower() == "true":
            sm.synch_argocd_application()

        LoggingManager.logger.info('******* SUCCESS: ALL TESTS PASSED *******')

    except (Exception) as error:
        LoggingManager.logger.error(error, exc_info=True)
    finally:
        if is_primary is True:
            if rm.has_replicas is True:
                cleanup(replica_test_cur, Databases.TEST_DB,
                        DBConnectionType.REPLICA_SERVICE)
                cleanup(replica_pod_cur,
                        Databases.TEST_DB, DBConnectionType.REPLICA_POD)
            cleanup(primary_test_cur, Databases.TEST_DB,
                    DBConnectionType.PRIMARY_SERVICE)
            cleanup(cur, Databases.POSTGRES,
                    DBConnectionType.PRIMARY_SERVICE)

        # remove logging handlers from logger
        lm.remove_handlers(LoggingManager.logger)
        cm.close_kubernetes_connection()


def validate_data(db_cur, DBConnectionType, pod=None):
    """ Determines if the expected data actually exists

    Args:
        test_db_cur (psycopg2.connection.cursor): The cursor to the active
        connection being validated
        DBConnectionType (ENUM): Primary or Replica data node connection

    Raises:
        ConnectionError: Error received when attempting to validate data
    """
    if db_cur is not None:

        # validate data
        if pod is not None:
            msg = 'Validating {type} Data for pod {pod_name}: Expecting 1000 '\
                'Rows'.format(type=DBConnectionType,
                              pod_name=pod.metadata.name)
        else:
            msg = 'Validating {type} Data: Expecting 1000 '\
                'Rows'.format(type=DBConnectionType)

        LoggingManager.logger.info(msg)
        db_cur.execute('SELECT COUNT(0) from test_schema.test_table')

        # get the row count from the query result
        row_count = db_cur.fetchone()[0]

        assert row_count == 1000, "row count should be 1000"

        if pod is not None:
            msg = '*** {type} Validation Succeeded for pod {pod_name}! '\
                '***'.format(type=DBConnectionType, pod_name=pod.metadata.name)
        else:
            msg = '*** {type} Validation Succeeded! ***'.format(
                type=DBConnectionType)

        LoggingManager.logger.info(msg)

    else:
        err = 'Unable to validate data.  The cursor is not assigned.'
        raise ConnectionError(err, db_cur)


def cleanup(cur, Databases, DBConnectionType):
    """ Cleans all database users and objects created during the tests

    Args:
        conn psycopg2.connection: The database connection to be closed
        cur connection.cursor: The postgres db connection cursor
        primary_test_cur connection.cursor: the test db connection cursor
    """

    # switch to postgres user
    if cur is None:
        return

    # cleanup postgres db objects
    if Databases == Databases.POSTGRES:
        um.switch_to_postgres_user(cur)
        # drop test_db and test_user
        dbm.cleanup_postgres_db_objects(cur)

        # close cursor and postgres db connection
        cur.close()
        cm.close_connection(cm.postgres_db_connection,
                            Databases.POSTGRES, DBConnectionType)
    # cleanup test db objects
    else:
        match DBConnectionType:
            case DBConnectionType.PRIMARY_SERVICE:
                # drop test_table and test_schema
                dbm.cleanup_test_db_objects(cur)
                # close cursor and test_db connections
                cur.close()
                cm.close_connection(cm.primary_test_db_connection,
                                    Databases.TEST_DB, DBConnectionType)
            case DBConnectionType.REPLICA_SERVICE:
                cur.close()
                cm.close_connection(cm.replica_test_db_connection,
                                    Databases.TEST_DB, DBConnectionType)
            case _:
                cur.close()
                cm.close_connection(cm.replica_pod_db_connection,
                                    Databases.TEST_DB, DBConnectionType)


def get_version(cur):
    """ Connects to the postgres database and gets the current postgres version

    Args:
        cur (connection.cursor: The postgres db connection cursor
    """
    # get the postgres version
    LoggingManager.logger.info('PostgreSQL database version:')
    cur.execute('SELECT version()')

    # display the PostgreSQL database server version
    db_version = cur.fetchone()
    LoggingManager.logger.info(db_version)


def is_host_primary_data_pod():
    """ Determine if the container is running on a
    primary or replica data pod.

    Returns:
        bool: True if Primary
    """
    # cm.connect_to_kubernetes()
    kube = ConnectionManager.kubernetes_connection
    ns = os.getenv('NAMESPACE')
    host = os.getenv('HOSTNAME')
    cluster_name = os.getenv('CLUSTER_NAME')

    primary_label = 'postgres-operator.crunchydata.com/role=master'
    cluster_label = "postgres-operator.crunchydata.com/cluster=%s" \
        % (cluster_name)
    labels = primary_label + "," + cluster_label
    primary_pods = kube.list_namespaced_pod(namespace=ns,
                                            label_selector=labels)
    for pod in primary_pods.items:
        if pod.metadata.name == host:
            return True
        else:
            return False


def rerun_tests():
    """
        Rerun the tests on failover.
    """
    global is_primary
    is_primary = is_host_primary_data_pod()
    global has_run_as_primary
    if is_primary is True and has_run_as_primary is False:
        run_tests()


# entry point
if __name__ == '__main__':
    run_tests()
    while True:
        time.sleep(30)
        rerun_tests()
