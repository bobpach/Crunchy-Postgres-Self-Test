""" Contains Database Connection Type Enum
"""
from enum import Enum


class DBConnectionType(Enum):
    """Database Connection Type Enum
    """
    PRIMARY_SERVICE = 1
    REPLICA_SERVICE = 2
    REPLICA_POD = 3
