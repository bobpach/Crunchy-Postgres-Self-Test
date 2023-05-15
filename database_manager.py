"""Contains the Database Manager Class
"""
from psycopg2 import sql
from logging_manager import LoggingManager


class DatabaseManager:
    """Creates and cleans up test objects
    """

    # initialize globals
    lm = LoggingManager()

    def create_database(self, cur):
        """ Creates the test database

        Args:
            cur connection.cursor: The postgres db connection cursor
        """
        # set db name
        dbname = sql.Identifier('test_db')

        # commands to create database and assign privileges
        LoggingManager.logger.info("Creating test database")
        create_cmd = sql.SQL('CREATE DATABASE {}').format(dbname)
        cur.execute(create_cmd)

        LoggingManager.logger.info("Assigning test_db privileges to test_user")
        grant_cmd = sql.SQL('GRANT ALL PRIVILEGES ON DATABASE {} \
          TO test_user').format(dbname)
        cur.execute(grant_cmd)

    # create test schema
    def create_schema(self, cur):
        """ Creates the test schema in the test database

        Args:
            cur connection.cursor: The test db connection cursor
        """
        LoggingManager.logger.info("Creating test_schema in test_db")
        cur.execute('CREATE SCHEMA test_schema')

    # create table in test schema
    def create_table(self, cur):
        """ Creates the test table with data in the test schema

        Args:
            cur connection.cursor: The test db connection cursor
        """
        LoggingManager.logger.info(
            "Creating test_table with data in test_schema")
        cur.execute('CREATE TABLE test_schema.test_table AS SELECT s, \
          md5(random()::text) FROM generate_Series(1,1000) s')

    # clean up objects created with test_user
    def cleanup_test_db_objects(self, cur):
        """ Drops the test table and schema in the test database

        Args:
            cur connection.cursor: The test db connection cursor
        """
        LoggingManager.logger.info("Dropping test_table")
        cur.execute('DROP TABLE test_schema.test_table')
        LoggingManager.logger.info("Dropping test_schema")
        cur.execute('DROP SCHEMA test_schema')

    # clean up objects created with db user
    def cleanup_postgres_db_objects(self, cur):
        """ Drops the test database and user

        Args:
            cur connection.cursor: The postgres db connection cursor
        """
        LoggingManager.logger.info("Dropping test_db")
        cur.execute('DROP DATABASE test_db')
        LoggingManager.logger.info("Dropping test_user")
        cur.execute('DROP ROLE test_user')
