"""Contains ConfigManager Class

    Raises:
        Exception: database.ini parsing error for postgresql
        Exception: database.ini parsing error for testpostgresql

    Returns:
       dict: Dictionary containing postgres connection string values
"""
import os
from db_connection_type import DBConnectionType
from password_manager import PasswordManager


class ConfigManager:
    """The ConfigManager Class

        Raises:
            Exception: database.ini parsing error for postgresql
            Exception: database.ini parsing error for testpostgresql

        Returns:
            dict: Dictionary containing postgres connection string values
    """

    def __init__(self):
        self.set_default_config_values()

    # initialize PasswordManager
    pm = PasswordManager()

    def get_postgres_connection_parameters(self):
        """ Add postgres db connection parameters to the collection

        Returns:
            dictionary: Contains postgres db connection parameters
        """
        params = self.get_db_service_connection_parameters(
            DBConnectionType.PRIMARY_SERVICE)
        params["database"] = "postgres"
        params["user"] = os.getenv('DB_USER')
        params["password"] = PasswordManager.postgres_password
        return params

    def get_test_db_connection_parameters(self, DBConnectionType, pod=None):
        """ Gets the test_db connection string parameters \
            based on DBConnectionType

        Args:
            DBConnectionType (Enum): Database connection type
            pod (kubernetes.client.models.v1_pod, optional): \
            The target replica pod. Defaults to None.

        Returns:
            dictionary: The connection string parameter key / value pairs.
        """
        if DBConnectionType is DBConnectionType.REPLICA_POD:
            params = self.get_replica_pod_connection_parameters(pod)
        else:
            params = self.get_db_service_connection_parameters(
                DBConnectionType)

        params["database"] = "test_db"
        params["user"] = "test_user"
        params["password"] = PasswordManager.test_db_password
        return params

    def get_replica_pod_connection_parameters(self, pod):
        """ Gets the replica pod connection string parameters

        Args:
            pod (kubernetes.client.models.v1_pod): The target replica pod

        Returns:
            params (dictionary): Contains replica pod connection parameters
        """
        params = self.get_common_connection_parameters()
        params["host"] = pod.status.pod_ip

        return params

    def get_db_service_connection_parameters(self, DBConnectionType):
        """ Add db service connection parameters to the collection

        Returns:
            dictionary: Contains db service connection parameters
        """
        params = self.get_common_connection_parameters()

        self.cluster_name = os.getenv('CLUSTER_NAME')
        self.namespace = os.getenv('NAMESPACE')

        # set host parameter based on DBConnectionType
        if DBConnectionType == DBConnectionType.PRIMARY_SERVICE:
            params["host"] = self.cluster_name + "-ha."\
                + self.namespace + ".svc"
        else:
            params["host"] = self.cluster_name + "-replicas."\
                + self.namespace + ".svc"
        return params

    def get_common_connection_parameters(self):
        """ Create common connection parameter collection

        Returns:
            dictionary: Contains common db connection parameters
        """
        # get values from environment variables
        port = int(os.getenv('SERVICE_PORT'))
        sslmode = os.getenv('SSLMODE')

        # build parameter collection
        params = {}
        params["port"] = port
        params["sslmode"] = sslmode
        return params

    def set_default_config_values(self):
        """ Sets the default config values if not set in configmap
        """

        # defaults the argocd namespace to argocd
        if "ARGOCD_NAMESPACE" not in os.environ:
            os.environ["ARGOCD_NAMESPACE"] = "argocd"

        # defaults the log level to info
        if "ARGOCD_VERIFY_TLS" not in os.environ:
            os.environ["ARGOCD_VERIFY_TLS"] = "true"

        # defaults the log level to info
        if "LOG_LEVEL" not in os.environ:
            os.environ["LOG_LEVEL"] = "info"

        # defaults the log path to /pgdata
        if "LOG_PATH" not in os.environ:
            os.environ["LOG_PATH"] = "/pgdata"

        # defaults the number of attempts to 6
        if "POSTGRES_CONN_ATTEMPTS" not in os.environ:
            os.environ["POSTGRES_CONN_ATTEMPTS"] = "6"

        # defaults the wait interval to 10 seconds
        if "POSTGRES_CONN_INTERVAL" not in os.environ:
            os.environ["POSTGRES_CONN_INTERVAL"] = "10"

        # defaults the service port to 5432
        if "SERVICE_PORT" not in os.environ:
            os.environ["SERVICE_PORT"] = "5432"

        # defaults the sslmode to require
        if "SSLMODE" not in os.environ:
            os.environ["MODE"] = "require"
