# PyKota
# -*- coding: ISO-8859-15 -*-
#
# PyKota : Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# $Id: pgstorage.py 3500 2009-05-20 08:27:33Z jerome $
#
#

"""This module defines a class to access to a PostgreSQL database backend."""

import time
from types import NoneType

# from types import StringType

from pykota.storage import PyKotaStorageError, BaseStorage
from pykota.storages.sql import SQLStorage

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    import sys

    # TODO : to translate or not to translate ?
    raise PyKotaStorageError(
        f"This python version ({sys.version.split()[0]}) doesn't seem to have the PygreSQL module installed correctly.")
else:
    try:
        PGError = psycopg2.Error
    except AttributeError:
        PGError = psycopg2.error


class Storage(BaseStorage, SQLStorage):
    def __init__(self, pykotatool, host, dbname, user, passwd):
        """Opens the PostgreSQL database connection."""
        BaseStorage.__init__(self, pykotatool)
        try:
            (host, port) = host.split(":")
            port = int(port)
        except ValueError:
            port = 5432  # Use PostgreSQL's default tcp/ip port (5432).

        self.tool.logdebug(f"Trying to open database (host={host}, port={port}, dbname={dbname}, user={user})...")
        try:
            conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=passwd)
            self.database = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except PGError as msg:
            msg = "{msg} --- the most probable cause of your problem is that PostgreSQL is down, or doesn't accept " \
                  "incoming connections because you didn't configure it as explained in PyKota's " \
                  "documentation.".format(
                **locals())
            raise PGError(msg)
        self.closed = 0
        # try:
        #    self.quote = self.database._quote
        # except AttributeError:  # pg <v4.x
        #    self.quote = pg._quote
        try:
            self.database.execute("SET CLIENT_ENCODING TO 'UTF-8';")
        except PGError as msg:
            self.tool.logdebug(f"Impossible to set database client encoding to UTF-8 : {msg}")
        self.tool.logdebug(f"Database opened (host={host}, port={port}, dbname={dbname}, user={user})")

    def close(self):
        """Closes the database connection."""
        if not self.closed:
            self.database.close()
            self.closed = 1
            self.tool.logdebug("Database closed.")

    def beginTransaction(self):
        """Starts a transaction."""
        self.before = time.time()
        self.database.execute("BEGIN;")
        self.tool.logdebug("Transaction begins...")

    def commitTransaction(self):
        """Commits a transaction."""
        self.database.execute("COMMIT;")
        after = time.time()
        self.tool.logdebug("Transaction committed.")
        # self.tool.logdebug("Transaction duration : %.4f seconds" % (after - self.before))

    def rollbackTransaction(self):
        """Rollbacks a transaction."""
        self.database.execute("ROLLBACK;")
        after = time.time()
        self.tool.logdebug("Transaction aborted.")
        # self.tool.logdebug("Transaction duration : %.4f seconds" % (after - self.before))

    def doRawSearch(self, query):
        """Does a raw search query."""
        query = query.strip()
        if not query.endswith(';'):
            query += ';'
        try:
            before = time.time()
            self.tool.logdebug(f"QUERY : {query}")
            self.database.execute(query)
            result = self.database.fetchall()
        except PGError as msg:
            raise PyKotaStorageError(str(msg))
        else:
            after = time.time()
            # self.tool.logdebug("Query Duration : %.4f seconds" % (after - before))
            return result

    def doSearch(self, query):
        """Does a search query."""
        result = self.doRawSearch(query)
        if (result is not None) and (len(result) > 0):
            return result

    def doModify(self, query):
        """Does a (possibly multiple) modify query."""
        query = query.strip()
        if not query.endswith(';'):
            query += ';'
        try:
            before = time.time()
            self.tool.logdebug(f"QUERY : {query}")
            result = self.database.execute(query)
        except PGError as msg:
            self.tool.logdebug(f"Query failed : {repr(msg)}")
            raise PyKotaStorageError(str(msg))
        else:
            after = time.time()
            # self.tool.logdebug("Query Duration : %.4f seconds" % (after - before))
            return result

    def doQuote(self, field):
        """Quotes a field for use as a string in SQL queries."""
        if type(field) == NoneType:
            typ = None
        elif type(field) == type(0.0):
            typ = "decimal"
        elif type(field) == type(0):
            typ = "int"
        else:
            typ = "text"
        return self.quote(field, typ)

    def prepareRawResult(self, result):
        """Prepares a raw result by including the headers."""
        if result.ntuples() > 0:
            entries = [result.listfields()]
            entries.extend(result.getresult())
            nbfields = len(entries[0])
            for i in range(1, len(entries)):
                fields = list(entries[i])
                for j in range(nbfields):
                    field = fields[j]
                    if type(field) == str:
                        fields[j] = self.databaseToUserCharset(field)
                entries[i] = tuple(fields)
            return entries

    def quote(self, field, typ):
        if typ == None:
            return 'NULL'
        if typ == 'decimal':
            return f"'{field}'"
        elif typ == 'int':
            return field
        else:
            return f"'{field}'"
