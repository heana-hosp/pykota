# -*- coding: utf-8 -*-
#
# pkpgcounter: a generic Page Description Language parser
#
# (c) 2003-2019 Jerome Alet <alet@librelogiciel.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id: pdlparser.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This module defines the base class for all Page Description Language parsers."""

import sys
import os

KILOBYTE = 1024
MEGABYTE = 1024 * KILOBYTE
FIRSTBLOCKSIZE = 16 * KILOBYTE
LASTBLOCKSIZE = int(KILOBYTE / 4)


class PDLParserError(Exception):
    """An exception for PDLParser related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class PDLParser:
    """Generic PDL parser."""
    totiffcommands = None  # Default command to convert to TIFF
    required = []  # Default list of required commands
    openmode = "rb"  # Default file opening mode
    format = "Unknown"  # Default file format
    """(firstblock, lastblock)"""

    def __init__(self, parent, filename, *block):
        """Initialize the generic parser."""
        self.parent = parent
        # We need some copies for later inclusion of parsers which
        # would modify the parent's values
        self.filename = filename[:]
        self.firstblock = block[0]
        self.lastblock = block[1]
        self.infile = None
        if not self.is_valid():
            raise PDLParserError("Invalid file format !")
        else:
            self.logdebug("Input file is in the '%s' file format." % self.format)
        self.infile = open(self.filename, self.openmode)
        # self.logdebug("Opened %s in '%s' mode." % (self.filename, self.openmode))

    def __del__(self):
        """Ensures the input file gets closed."""
        if self.infile:
            self.infile.close()

    def find_executable(self, command):
        """Finds an executable in the PATH and returns True if found else False."""
        for cmd in [p.strip() for p in command.split("|")]:  # | can separate alternatives for similar
            # commands (e.g. a2ps|enscript)
            for path in os.environ.get("PATH", "").split(":"):
                fullname = os.path.abspath(os.path.join(os.path.expanduser(path), cmd))
                if os.path.isfile(fullname) and os.access(fullname, os.X_OK):
                    return True
        return False

    def is_missing(self, commands):
        """Returns True if some required commands are missing, else False."""
        howmanythere = 0
        for command in commands:
            if not self.find_executable(command):
                sys.stderr.write(
                    "ERROR: %(command)s is missing or not executable. You MUST install it for "
                    "pkpgcounter to be able to do what you want.\n" % locals())
                sys.stderr.flush()
            else:
                howmanythere += 1
        if howmanythere == len(commands):
            return False
        else:
            return True

    def logdebug(self, message):
        """Logs a debug message if needed."""
        if self.parent.options.debug:
            sys.stderr.write("%s\n" % message)

    def is_valid(self):
        """Returns True if data is in the expected format, else False."""
        raise RuntimeError("Not implemented !")

    def get_job_size(self):
        """Counts pages in a document."""
        raise RuntimeError("Not implemented !")

    def convert_to_tiff_multi_page_24nc(self, outfname, dpi):
        """Converts the input file to TIFF format, X dpi, 24 bits per pixel, uncompressed.
           Writes TIFF datas to the file named by outfname.
        """
        if self.totiffcommands:
            if self.is_missing(self.required):
                raise PDLParserError(
                    "At least one of the following commands is missing and should be installed "
                    "for the computation of ink coverage: {repr(self.required)}")
            infname = self.filename
            for totiffcommand in self.totiffcommands:
                error = False
                commandline = totiffcommand % locals()
                # self.logdebug("Executing '%s'" % commandline)
                status = os.system(commandline)
                if os.WIFEXITED(status):
                    if os.WEXITSTATUS(status):
                        error = True
                else:
                    error = True
                if not os.path.exists(outfname):
                    error = True
                elif not os.stat(outfname).st_size:
                    error = True
                else:
                    break  # Conversion worked fine it seems.
                sys.stderr.write("Command failed: %s\n" % repr(commandline))
            if error:
                raise PDLParserError("Problem during conversion to TIFF.")
        else:
            raise PDLParserError("Impossible to compute ink coverage for this file format.")
