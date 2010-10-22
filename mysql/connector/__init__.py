# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009,2010, Oracle and/or its affiliates. All rights reserved.
# Use is subject to license terms. (See COPYING)

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
# 
# There are special exceptions to the terms and conditions of the GNU
# General Public License as it is applied to this software. View the
# full text of the exception in file EXCEPTIONS-CLIENT in the directory
# of this software distribution or see the FOSS License Exception at
# www.mysql.com.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"""
MySQL Connector/Python - MySQL drive written in Python
"""

# Python Db API v2
apilevel = '2.0'
threadsafety = 1
paramstyle = 'pyformat'

# Read the version from an generated file
import _version
__version__ = _version.version

from connection import MySQLConnection
from errors import *
from constants import FieldFlag, FieldType, CharacterSet,\
    RefreshOption, ClientFlag
from dbapi import *

def Connect(*args, **kwargs):
    """Shortcut for creating a connection.MySQLConnection object."""
    return MySQLConnection(*args, **kwargs)
connect = Connect

__all__ = [
    'MySQLConnection', 'Connect',
    
    # Some useful constants
    'FieldType','FieldFlag','ClientFlag','CharacterSet','RefreshOption',

    # Error handling
    'Error','Warning',
    'InterfaceError','DatabaseError',
    'NotSupportedError','DataError','IntegrityError','ProgrammingError',
    'OperationalError','InternalError',
    
    # DBAPI PEP 249 required exports
    'connect','apilevel','threadsafety','paramstyle',
    'Date', 'Time', 'Timestamp', 'Binary',
    'DateFromTicks', 'DateFromTicks', 'TimestampFromTicks',
    'STRING', 'BINARY', 'NUMBER',
    'DATETIME', 'ROWID',
    ]
