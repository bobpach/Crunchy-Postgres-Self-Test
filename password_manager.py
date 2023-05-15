""" Creates and provides access to a randomly generated password
"""
import os
import random
import string


class PasswordManager:
    """ Creates and provides access to a randomly generated password
    """

    # initialize with static attributes
    def __init__(self):
        if not hasattr(PasswordManager, 'postgres_password'):
            PasswordManager.postgres_password = self.get_postgres_password()
        if not hasattr(PasswordManager, 'test_db_password'):
            PasswordManager.test_db_password = self.generate_random_password()

    def generate_random_password(self):
        """ Generate random password of length 24 with letters,
        digits, and symbols
        """
        if not hasattr(self, '_test_db_password'):
            characters = string.ascii_letters + string.digits \
                + string.punctuation
            pwd = ''.join(random.choice(characters)
                          for i in range(24))
            return pwd

    def get_postgres_password(self):
        """ Gets the postgres user password from the environment variable

        Returns:
            string: postgres user password
        """
        return os.getenv('DB_USER_PASSWORD')
