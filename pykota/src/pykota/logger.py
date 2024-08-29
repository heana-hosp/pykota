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
# $Id: logger.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines base classes used by all logging backends."""
import os
# import imp
from importlib.machinery import SourceFileLoader
import sys


class PyKotaLoggingError(Exception):
    """An exception for logging related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


def open_logger(backend):
    """Returns the appropriate logger subsystem object."""
    try:
        # loggingbackend = imp.load_source("loggingbackend",
        #                                os.path.join(os.path.dirname(__file__),
        #                                             "loggers",
        #                                             f"{backend.lower()}.py"))
        #sys.stderr.write(f"{os.path.join(os.path.dirname(__file__))}/loggers/{backend}\n\n\n\n\n\n")
        loggingbackend = SourceFileLoader("loggers",
                                          f"{os.path.join(os.path.dirname(__file__))}/loggers/{backend.lower()}.py").load_module()

    except ImportError:
        raise PyKotaLoggingError(f"Unsupported logging subsystem {backend}")
    else:
        return loggingbackend.Logger()
