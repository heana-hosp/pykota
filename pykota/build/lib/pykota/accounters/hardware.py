# PyKota
# -*- coding: ISO-8859-15 -*-
#
# PyKota - Print Quotas for CUPS and LPRng
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
# $Id: hardware.py 3162 2007-04-14 08:50:47Z jerome $
#
#

import os
import signal
import subprocess

from pykota.accounter import AccounterBase, PyKotaAccounterError
from pykota.accounters import snmp, pjl


class Accounter(AccounterBase):
    def __init__(self, kotabackend, arguments, ispreaccounter=0):
        """Initializes querying accounter."""
        AccounterBase.__init__(self, kotabackend, arguments)
        self.counterafter = 0
        self.counterbefore = 0
        self.isSoftware = 0

    def getPrinterInternalPageCounter(self):
        """Returns the printer's internal page counter."""
        self.filter.logdebug(f"Reading printer {self.filter.PrinterName}'s internal page counter...")
        counter = self.askPrinterPageCounter(self.filter.PrinterHostName)
        self.filter.logdebug(f"Printer {self.filter.PrinterName}'s internal page counter value is : {str(counter)}")
        return counter

    def beginJob(self, printer):
        """Saves printer internal page counter at start of job."""
        # save page counter before job
        self.LastPageCounter = self.getPrinterInternalPageCounter()
        self.fakeBeginJob()

    def fakeBeginJob(self):
        """Fakes a begining of a job."""
        self.counterbefore = self.get_last_page_counter()

    def endJob(self, printer):
        """Saves printer internal page counter at end of job."""
        # save page counter after job
        self.LastPageCounter = self.counterafter = self.getPrinterInternalPageCounter()

    def getJobSize(self, printer):
        """Returns the actual job size."""
        if (not self.counterbefore) or (not self.counterafter):
            # there was a problem retrieving page counter
            self.filter.printInfo(f"A problem occured while reading printer {printer.Name}'s internal page counter.",
                                  "warn")
            if printer.LastJob.Exists:
                # if there's a previous job, use the last value from database
                self.filter.printInfo(f"Retrieving printer {printer.Name}'s page counter from database instead.",
                                      "warn")
                if not self.counterbefore:
                    self.counterbefore = printer.LastJob.PrinterPageCounter or 0
                if not self.counterafter:
                    self.counterafter = printer.LastJob.PrinterPageCounter or 0
                before = min(self.counterbefore, self.counterafter)
                after = max(self.counterbefore, self.counterafter)
                self.counterbefore = before
                self.counterafter = after
                if (not self.counterbefore) or (not self.counterafter) or (self.counterbefore == self.counterafter):
                    self.filter.printInfo(
                        f"Couldn't retrieve printer {printer.Name}'s internal page counter either before or after printing.",
                        "warn")
                    self.filter.printInfo(f"Job's size forced to 1 page for printer {printer.Name}.", "warn")
                    self.counterbefore = 0
                    self.counterafter = 1
            else:
                self.filter.printInfo(f"No previous job in database for printer {printer.Name}.", "warn")
                self.filter.printInfo(f"Job's size forced to 1 page for printer {printer.Name}.", "warn")
                self.counterbefore = 0
                self.counterafter = 1

        jobsize = (self.counterafter - self.counterbefore)
        if jobsize < 0:
            # Try to take care of HP printers 
            # Their internal page counter is saved to NVRAM
            # only every 10 pages. If the printer was switched
            # off then back on during the job, and that the
            # counters difference is negative, we know 
            # the formula (we can't know if more than eleven
            # pages were printed though) :
            if jobsize > -10:
                jobsize += 10
            else:
                # here we may have got a printer being replaced
                # DURING the job. This is HIGHLY improbable (but already happened) !
                self.filter.printInfo(f"Inconsistent values for printer {printer.Name}'s internal page counter.",
                                      "warn")
                self.filter.printInfo(f"Job's size forced to 1 page for printer {printer.Name}.", "warn")
                jobsize = 1
        return jobsize

    def askPrinterPageCounter(self, printer):
        """Returns the page counter from the printer via an external command.
        
           The external command must report the life time page number of the printer on stdout.
        """
        skipinitialwait = self.filter.config.get_printer_skip_initial_wait(printer)
        commandline = self.arguments.strip() % locals()
        cmdlower = commandline.lower()
        if (cmdlower == "snmp") or cmdlower.startswith("snmp:"):
            return snmp.Handler(self, printer, skipinitialwait).retrieveInternalPageCounter()
        elif (cmdlower == "pjl") or cmdlower.startswith("pjl:"):
            return pjl.Handler(self, printer, skipinitialwait).retrieveInternalPageCounter()

        if printer is None:
            raise PyKotaAccounterError(
                f"Unknown printer address in HARDWARE({commandline}) for printer {self.filter.PrinterName}")
        while 1:
            self.filter.printInfo(f"Launching HARDWARE({commandline})...")
            pagecounter = None
            # child = popen2.Popen4(commandline)
            child = subprocess.Popen(commandline, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            try:
                answer, stderr = child.communicate()
            except IOError:
                # we were interrupted by a signal, certainely a SIGTERM
                # caused by the user cancelling the current job
                try:
                    os.kill(child.pid, signal.SIGTERM)
                except:
                    pass  # already killed ?
                self.filter.printInfo(f"SIGTERM was sent to hardware accounter {commandline} (pid: {child.pid})")
            else:
                lines = [l.strip() for l in answer.split(b"\n")]
                for i in range(len(lines)):
                    try:
                        pagecounter = int(lines[i])
                    except (AttributeError, ValueError):
                        self.filter.printInfo(f"Line [{lines[i]}] skipped in accounter's output. Trying again...")
                    else:
                        break

            child.kill()

            try:
                status = child.wait()
            except OSError as msg:
                self.filter.logdebug(f"Error while waiting for hardware accounter pid {child.pid} : {msg}")
            else:
                if os.WIFEXITED(status):
                    status = os.WEXITSTATUS(status)
                self.filter.printInfo(f"Hardware accounter {self.arguments} exit code is {str(status)}")

            if pagecounter is None:
                message = f"Unable to query printer {printer} via HARDWARE({commandline})"
                if self.onerror == "CONTINUE":
                    self.filter.printInfo(message, "error")
                else:
                    raise PyKotaAccounterError(message)
            else:
                return pagecounter
