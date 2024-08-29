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
# $Id: reporter.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines bases classes used by all reporters."""

import os
import imp
from datetime import datetime


class PyKotaReporterError(Exception):
    """An exception for Reporter related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class BaseReporter:
    """Base class for all reports."""

    def __init__(self, tool, printers, ugnames, isgroup):
        """Initialize local datas."""
        self.tool = tool
        self.printers = printers
        self.ugnames = ugnames
        self.isgroup = isgroup

    def getPrinterTitle(self, printer):
        """Returns the formatted title for a given printer."""
        return f"Report for {(self.isgroup and 'group') or 'user'} quota on printer {printer.Name}" + (
            f" ({printer.Description})")

    def getPrinterGraceDelay(self, printer):
        """Returns the formatted grace delay for a given printer."""
        return (f"Pages grace time: {self.tool.config.get_grace_delay(printer.Name):d} days")

    def getPrinterPrices(self, printer):
        """Returns the formatted prices for a given printer."""
        return f"Price per job: {printer.PricePerJob:.3f}" or 0.0, f"Price per page: {printer.PricePerPage or 0.0:.3f}"

    def getReportHeader(self):
        """Returns the correct header depending on users vs users groups."""
        if self.isgroup:
            return "Group          overcharge   used    soft    hard    balance grace         total       paid warn"
        else:
            return "User           overcharge   used    soft    hard    balance grace         total       paid warn"

    def getPrinterRealPageCounter(self, printer):
        """Returns the formatted real page counter for a given printer."""
        msg = "unknown"
        if printer.LastJob.Exists:
            try:
                msg = f"{printer.LastJob.PrinterPageCounter:9d}"
            except TypeError:
                pass
        return f"Real : {msg}"

    def getTotals(self, total, totalmoney):
        """Returns the formatted totals."""
        return f"Total : {total or 0.0:9d}", f"{('%7.2f' % (totalmoney or 0.0))[:11]:>11}"

    def getQuota(self, entry, quota):
        """Prints the quota information."""
        lifepagecounter = int(quota.LifePageCounter or 0)
        pagecounter = int(quota.PageCounter or 0)
        balance = float(entry.AccountBalance or 0.0)
        lifetimepaid = float(entry.LifeTimePaid or 0.0)
        if not hasattr(entry, "OverCharge"):
            overcharge = "N/A"  # Not available for groups
        else:
            overcharge = float(entry.OverCharge or 0.0)
        if not hasattr(quota, "WarnCount"):
            warncount = "N/A"  # Not available for groups
        else:
            warncount = int(quota.WarnCount or 0)

        if (not entry.LimitBy) or (entry.LimitBy.lower() == "quota"):
            if (quota.HardLimit is not None) and (pagecounter >= quota.HardLimit):
                datelimit = "DENY"
            elif (quota.HardLimit is None) and (quota.SoftLimit is not None) and (pagecounter >= quota.SoftLimit):
                datelimit = "DENY"
            elif quota.DateLimit is not None:
                now = datetime.now()
                # datelimit = DateTime.ISO.ParseDateTime(str(quota.DateLimit)[:19])
                datelimit = datetime.fromisoformat(str(quota.DateLimit)[:19])
                if now >= datelimit:
                    datelimit = "DENY"
            else:
                datelimit = ""
            reached = (((quota.SoftLimit is not None) and (pagecounter >= quota.SoftLimit) and "+") or "-") + "Q"
        else:
            if entry.LimitBy.lower() == "balance":
                balancezero = self.tool.config.get_balance_zero()
                if balance == balancezero:
                    if entry.OverCharge > 0:
                        datelimit = "DENY"
                        reached = "+B"
                    else:
                        # overcharging by a negative or nul factor means user is always allowed to print
                        # TODO : do something when printer prices are negative as well !
                        datelimit = ""
                        reached = "-B"
                elif balance < balancezero:
                    datelimit = "DENY"
                    reached = "+B"
                elif balance <= self.tool.config.get_poor_man():
                    datelimit = "WARNING"
                    reached = "?B"
                else:
                    datelimit = ""
                    reached = "-B"
            elif entry.LimitBy.lower() == "noquota":
                reached = "NQ"
                datelimit = ""
            elif entry.LimitBy.lower() == "nochange":
                reached = "NC"
                datelimit = ""
            else:
                # noprint
                reached = "NP"
                datelimit = "DENY"

        strbalance = f"{balance:5.2f}"[:10]
        strlifetimepaid = f"{lifetimepaid:6.2f}"[:10]
        strovercharge = f"{overcharge:>5}"[:5]
        strwarncount = f"{warncount:>4}"[:4]
        return (lifepagecounter, lifetimepaid, entry.Name, reached,
                pagecounter, str(quota.SoftLimit), str(quota.HardLimit),
                strbalance, str(datelimit)[:10], lifepagecounter,
                strlifetimepaid, strovercharge, strwarncount)


def openReporter(tool, reporttype, printers, ugnames, isgroup):
    """Returns a reporter instance of the proper reporter."""
    try:
        reporterbackend = imp.load_source("reporterbackend",
                                          os.path.join(os.path.dirname(__file__),
                                                       "reporters",
                                                       f"{reporttype.lower()}.py"))
    except ImportError:
        raise PyKotaReporterError(f"Unsupported reporter backend {reporttype}")
    else:
        return reporterbackend.Reporter(tool, printers, ugnames, isgroup)
