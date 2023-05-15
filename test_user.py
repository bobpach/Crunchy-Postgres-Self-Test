"""Simple class to store test user state
"""
from dataclasses import dataclass


@dataclass
class TestUser:
    """Simple class to store test user values
    """

    def __init__(self, user, password):
        self.user = user
        self.password = password
