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
# $Id: analyzer.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This is the main module of pkpgcounter.

It defines the PDLAnalyzer class, which provides a generic way to parse
input files, by automatically detecting the best parser to use."""

import os
import sys
import tempfile
from pkpgpdls import bj
from pkpgpdls import cfax
from pkpgpdls import dvi
from pkpgpdls import escp2
from pkpgpdls import escpages03
from pkpgpdls import hbp
from pkpgpdls import inkcoverage
from pkpgpdls import lidil
from pkpgpdls import mscrap
from pkpgpdls import ooo
from pkpgpdls import pcl345
from pkpgpdls import pclxl
from pkpgpdls import pdf
from pkpgpdls import pdlparser
from pkpgpdls import pil
from pkpgpdls import oxps
from pkpgpdls import plain
from pkpgpdls import pnmascii
from pkpgpdls import postscript
from pkpgpdls import qpdl
from pkpgpdls import spl1
from pkpgpdls import tiff
from pkpgpdls import version
from pkpgpdls import zjstream


class AnalyzerOptions:
    """A class for use as the options parameter to PDLAnalyzer's constructor."""
    def __init__(self, debug=None, colorspace=None, resolution=None):
        """Sets initial attributes."""
        self.debug = debug
        self.colorspace = colorspace
        self.resolution = resolution


class PDLAnalyzer:
    """Class for PDL autodetection."""
    def __init__(self, filename, options=AnalyzerOptions()):
        """Initializes the PDL analyzer.

           filename is the name of the file or '-' for stdin.
           filename can also be a file-like object which
           supports read() and seek().
        """
        self.options = options
        self.filename = filename
        self.workfile = None

    def get_job_size(self):
        """Returns the job's size."""
        size = 0
        self.open_file()
        try:
            try:
                pdlhandler = self.detect_pdl_handler()
                size = pdlhandler.get_job_size()
            except pdlparser.PDLParserError as msg:
                raise pdlparser.PDLParserError(f"Unsupported file format for {self.filename} ({msg})")
        finally:
            self.close_file()
        return size

    def get_ink_coverage(self, colorspace=None, resolution=None):
        """Extracts the percents of ink coverage from the input file."""
        result = None
        cspace = colorspace or self.options.colorspace
        res = resolution or self.options.resolution
        if (not cspace) or (not res):
            raise ValueError(f"Invalid colorspace {cspace} or resolution {res}")
        self.open_file()
        try:
            try:
                pdlhandler = self.detect_pdl_handler()
                dummyfile = tempfile.NamedTemporaryFile(mode="w+b",
                                                        prefix="pkpgcounter_",
                                                        suffix=".tiff",
                                                        dir=os.environ.get("PYKOTADIRECTORY") or tempfile.gettempdir())
                filename = dummyfile.name
                try:
                    pdlhandler.convert_to_tiff_multi_page_24nc(filename, self.options.resolution)
                    result = inkcoverage.get_ink_coverage(filename, cspace)
                finally:
                    dummyfile.close()
            except pdlparser.PDLParserError as msg:
                raise pdlparser.PDLParserError(f"Unsupported file format for {self.filename} ({msg})")
        finally:
            self.close_file()
        return result

    def open_file(self):
        """Opens the job's data stream for reading."""
        if hasattr(self.filename, "read") and hasattr(self.filename, "seek"):
            # filename is in fact a file-like object
            infile = self.filename
        elif self.filename == "-":
            # we must read from stdin
            infile = sys.stdin
        else:
            # normal file
            self.workfile = open(self.filename, "rb")
            return

        # Use a temporary file, always seekable contrary to standard input.
        self.workfile = tempfile.NamedTemporaryFile(mode="w+b",
                                                    prefix="pkpgcounter_",
                                                    suffix=".prn",
                                                    dir=os.environ.get("PYKOTADIRECTORY") or
                                                    tempfile.gettempdir())
        self.filename = self.workfile.name
        while True:
            data = infile.read(pdlparser.MEGABYTE)
            if not data:
                break
            self.workfile.write(data)
        self.workfile.flush()
        self.workfile.seek(0)

    def close_file(self):
        """Closes the job's data stream if we have to."""
        self.workfile.close()

    def read_first_last_blocks(self, inputfile):
        """Reads the first and last blocks of data."""
        # Now read first and last block of the input file
        # to be able to detect the real file format and the parser to use.
        firstblock = inputfile.read(pdlparser.FIRSTBLOCKSIZE)
        try:
            inputfile.seek(-pdlparser.LASTBLOCKSIZE, 2)
            lastblock = inputfile.read(pdlparser.LASTBLOCKSIZE)
        except IOError:
            lastblock = ""
        return firstblock, lastblock

    def detect_pdl_handler(self):
        """Tries to autodetect the document format.

           Returns the correct PDL handler class or None if format is unknown
        """
        if not os.stat(self.filename).st_size:
            raise pdlparser.PDLParserError(f"input file {str(self.filename)} is empty !")
        (firstblock, lastblock) = self.read_first_last_blocks(self.workfile)

        # IMPORTANT: the order is important below. FIXME.
        for module in (postscript,
                       pclxl,
                       pdf,
                       qpdl,
                       spl1,
                       dvi,
                       tiff,
                       cfax,
                       zjstream,
                       ooo,
                       hbp,
                       lidil,
                       pcl345,
                       escp2,
                       escpages03,
                       bj,
                       pnmascii,
                       pil,
                       mscrap,
                       oxps,
                       plain):     # IMPORTANT: don't move this one up !
            try:
                return module.Parser(self, self.filename, firstblock, lastblock)
            except pdlparser.PDLParserError:
                pass  # try next parser
        raise pdlparser.PDLParserError("Analysis of first data block failed.")


def main():
    """Entry point for PDL Analyzer."""
    import optparse
    from copy import copy

    def check_cichoice(option, opt, value):
        """To add a CaseIgnore Choice option type."""
        valower = value.lower()
        if valower in [v.lower() for v in option.cichoices]:
            return valower
        else:
            choices = ", ".join([repr(o) for o in option.cichoices])
            raise optparse.OptionValueError(f"option {opt}: invalid choice: {value} "
                                            f"(choose from {choices})")

    class MyOption(optparse.Option):
        """New Option class, with CaseIgnore Choice type."""
        TYPES = optparse.Option.TYPES + ("cichoice",)
        ATTRS = optparse.Option.ATTRS + ["cichoices"]
        TYPE_CHECKER = copy(optparse.Option.TYPE_CHECKER)
        TYPE_CHECKER["cichoice"] = check_cichoice

    parser = optparse.OptionParser(option_class=MyOption,
                                   usage="python analyzer.py [options] file1 [file2 ...]")
    parser.add_option("-v", "--version",
                            action="store_true",
                            dest="version",
                            help="Show pkpgcounter's version number and exit.")
    parser.add_option("-d", "--debug",
                            action="store_true",
                            dest="debug",
                            help="Activate debug mode.")
    parser.add_option("-c", "--colorspace",
                            dest="colorspace",
                            type="cichoice",
                            cichoices=["bw", "rgb", "cmyk", "cmy", "gc"],
                            help="Activate the computation of ink usage, and defines the "
                                 "colorspace to use. Supported values are 'BW', "
                                 "'RGB', 'CMYK', 'CMY', and 'GC'.")
    parser.add_option("-r", "--resolution",
                            type="int",
                            default=72,
                            dest="resolution",
                            help="The resolution in DPI to use when checking ink usage. "
                                 "Lower resolution is faster but less accurate. "
                                 "Default is 72 dpi.")
    (options, arguments) = parser.parse_args()
    if options.version:
        sys.stdout.write(f"{version.__version__}\n")
    elif not (72 <= options.resolution <= 1200):
        sys.stderr.write("ERROR: the argument to the --resolution command line option "
                         "must be between 72 and 1200.\n")
        sys.stderr.flush()
    else:
        if (not arguments) or ((not sys.stdin.isatty()) and ("-" not in arguments)):
            arguments.append("-")
        totalsize = 0
        lines = []
        try:
            for arg in arguments:
                try:
                    parser = PDLAnalyzer(arg, options)
                    if not options.colorspace:
                        totalsize += parser.get_job_size()
                    else:
                        (cspace, pages) = parser.get_ink_coverage()
                        for page in pages:
                            lineparts = []
                            for k in cspace:  # NB: this way we preserve the order of the planes
                                try:
                                    lineparts.append("{}: {}" .format(k, ("%f" % page[k]).rjust(10)))
                                except KeyError:
                                    pass
                            lines.append("      ".join(lineparts))
                except (IOError, pdlparser.PDLParserError) as msg:
                    sys.stderr.write("ERROR: {}\n" .format(msg))
                    sys.stderr.flush()
        except KeyboardInterrupt:
            sys.stderr.write("WARN: Aborted at user's request.\n")
            sys.stderr.flush()
        if not options.colorspace:
            sys.stdout.write("%i\n" % totalsize)
        else:
            sys.stdout.write("%s\n" % ("\n".join(lines)))


if __name__ == "__main__":
    main()
