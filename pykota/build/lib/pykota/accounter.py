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
# $Id: accounter.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines base classes used by all accounting methods."""

import os
#import imp
from importlib.machinery import SourceFileLoader

class PyKotaAccounterError(Exception):
    """An exception for Accounter related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class AccounterBase:
    """A class to account print usage by querying printers."""

    def __init__(self, kotafilter, arguments, ispreaccounter=0):
        """Sets instance vars depending on the current printer."""
        self.filter = kotafilter
        self.arguments = arguments
        self.onerror = self.filter.config.get_printer_on_accounter_error(self.filter.PrinterName)
        self.isSoftware = 1  # by default software accounting
        self.isPreAccounter = ispreaccounter
        self.inkUsage = []

    def get_last_page_counter(self):
        """Returns last internal page counter value (possibly faked)."""
        try:
            return self.LastPageCounter or 0
        except:
            return 0

    def begin_job(self, printer):
        """Saves the computed job size."""
        # computes job's size
        self.JobSize = self.compute_job_size()

        # get last job information for this printer
        if not self.isPreAccounter:
            # TODO : check if this code is still needed
            if not printer.LastJob.Exists:
                # The printer hasn't been used yet, from PyKota's point of view
                self.LastPageCounter = 0
            else:
                # get last job size and page counter from Quota Storage
                # Last lifetime page counter before actual job is 
                # last page counter + last job size
                self.LastPageCounter = int(printer.LastJob.PrinterPageCounter or 0) + int(printer.LastJob.JobSize or 0)

    def fake_begin_job(self):
        """Do nothing."""
        pass

    def end_job(self, printer):
        """Do nothing."""
        pass

    def get_job_size(self, printer):
        """Returns the actual job size."""
        try:
            return self.JobSize
        except AttributeError:
            return 0

    def compute_job_size(self):
        """Must be overriden in children classes."""
        raise RuntimeError("AccounterBase.computeJobSize() must be overriden !")


def open_accounter(kotafilter, ispreaccounter=0):
    """Returns a connection handle to the appropriate accounter."""
    if ispreaccounter:
        (backend, args) = kotafilter.config.get_pre_accounter_backend(kotafilter.PrinterName)
    else:
        (backend, args) = kotafilter.config.get_accounter_backend(kotafilter.PrinterName)
    try:
        # accounterbackend = imp.load_source("accounterbackend",
        #                                   os.path.join(os.path.dirname(__file__),
        #                                                "accounters",
        #                                                "%s.py" % backend.lower()))
        accounterbackend = SourceFileLoader("accounters",
                         f"{os.path.join(os.path.dirname(__file__))}/accounters/{backend.lower()}.py").load_module()
    except ImportError:
        raise PyKotaAccounterError(f"Unsupported accounter backend {backend}")
    else:
        return accounterbackend.Accounter(kotafilter, args, ispreaccounter)
