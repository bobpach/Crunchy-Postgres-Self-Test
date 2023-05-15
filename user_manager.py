"""Contains the UserManager class

Returns:
    TestUser: TestUser object to manage password state
"""
from logging_manager import LoggingManager
from password_manager import PasswordManager
from psycopg2 import sql
from test_user import TestUser


class UserManager:
    """Class to create and manage database users.

    Returns:
        TestUser: TestUser object to manage password state
    """

    lm = LoggingManager()

    def create_test_user(self, cur):
        """Creates a test user object with a randomly generated password

        Args:
            cur (psycopg2.connection.cursor): database connection cursor

        Returns:
          TestUser: TestUser object to manage password state
        """
        try:
            # create stateful object for the test user
            pwd = PasswordManager.test_db_password
            test_user = TestUser("test_user", pwd)

            # create test user and grant privileges
            create_cmd = sql.SQL("CREATE USER test_user WITH PASSWORD {}")
            create_cmd = create_cmd.format(sql.Literal(test_user.password))
            cur.execute(create_cmd)
            grant_cmd = sql.SQL('ALTER ROLE test_user WITH SUPERUSER CREATEDB')
            cur.execute(grant_cmd)

            return test_user
        except (Exception) as error:
            LoggingManager.logger.error(error)

    def switch_to_test_user(self, cur):
        """Changes the active ROLE to test_user

        Args:
          cur (psycopg2.connection.cursor): database connection cursor
        """
        cur.execute('SET ROLE test_user')

    def switch_to_postgres_user(self, cur):
        """Changes the active ROLE to postgres

        Args:
            cur (psycopg2.connection.cursor): database connection cursor
        """
        cur.execute('SET ROLE postgres')
