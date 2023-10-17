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
# $Id: postscript.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements a page counter for PostScript documents."""

import os
from pkpgpdls import pdlparser


class Parser(pdlparser.PDLParser):
    """A parser for PostScript documents."""
    totiffcommands = [ 'gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" "%(infname)s"' ]
    required = [ "gs" ]
    openmode = "rbU"
    format = "PostScript"

    def is_valid(self):
        """Returns True if data is PostScript, else False."""
        if self.firstblock.startswith(b"%!") or \
           self.firstblock.startswith(b"\004%!") or \
           self.firstblock.startswith(b"\033%-12345X%!PS") or \
           ((self.firstblock[:128].find(b"\033%-12345X") != -1) and \
             ((self.firstblock.find(b"LANGUAGE=POSTSCRIPT") != -1) or \
              (self.firstblock.find(b"LANGUAGE = POSTSCRIPT") != -1) or \
              (self.firstblock.find(b"LANGUAGE = Postscript") != -1))) or \
              (self.firstblock.find(b"%!PS-Adobe") != -1):
            return True
        else:
            return False

    def through_ghost_script(self):
        """Get the count through GhostScript, useful for non-DSC compliant PS files."""
        self.logdebug("Internal parser sucks, using GhostScript instead...")
        if self.is_missing(self.required):
            raise pdlparser.PDLParserError("The gs interpreter is nowhere to be found in your PATH (%s)" % os.environ.get("PATH", ""))
        infname = self.filename
        command = 'gs -sDEVICE=bbox -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET "%(infname)s" 2>&1 | grep -c "%%HiResBoundingBox:" 2>/dev/null'
        pagecount = 0
        fromchild = os.popen(command % locals(), "r")
        try:
            try:
                pagecount = int(fromchild.readline().strip())
            except (IOError, OSError, AttributeError, ValueError) as msg:
                raise pdlparser.PDLParserError("Problem during analysis of Binary PostScript document: {msg}")
        finally:
            if fromchild.close() is not None:
                raise pdlparser.PDLParserError("Problem during analysis of Binary PostScript document")
        self.logdebug("GhostScript said: %s pages" % pagecount)
        return pagecount * self.copies

    def set_copies(self, pagenum, txtvalue):
        """Tries to extract a number of copies from a textual value and set the instance attributes accordingly."""
        try:
            number = int(txtvalue)
        except (ValueError, TypeError):
            pass
        else:
            if number > self.pages[pagenum]["copies"]:
                self.pages[pagenum]["copies"] = number

    def natively(self):
        """Count pages in a DSC compliant PostScript document."""
        pagecount = 0
        self.pages = { 0: { "copies": 1 } }
        oldpagenum = 0
        previousline = ""
        notrust = False
        prescribe = False # Kyocera's Prescribe commands
        acrobatmarker = False
        pagescomment = None
        for line in self.infile:
            line = line.strip()
            parts = line.split()
            nbparts = len(parts)
            if nbparts >= 1:
                part0 = parts[0]
            else:
                part0 = ""
            if part0 == br"%ADOPrintSettings:":
                acrobatmarker = True
            elif part0 == "!R!":
                prescribe = True
            elif part0 == br"%%Pages:":
                try:
                    pagescomment = max(pagescomment or 0, int(parts[1]))
                except ValueError:
                    pass # strange, to say the least
            elif (part0 == br"%%BeginNonPPDFeature:") \
                  and (nbparts > 2) \
                  and (parts[1] == b"NumCopies"):
                self.set_copies(pagecount, parts[2])
            elif (part0 == br"%%Requirements:") \
                  and (nbparts > 1) \
                  and (parts[1] == b"numcopies("):
                try:
                    self.set_copies(pagecount, line.split('(')[1].split(')')[0])
                except IndexError:
                    pass
            elif part0 == b"/#copies":
                if nbparts > 1:
                    self.set_copies(pagecount, parts[1])
            elif part0 == br"%RBINumCopies:":
                if nbparts > 1:
                    self.set_copies(pagecount, parts[1])
            elif (parts[:4] == [b"1", b"dict", b"dup", b"/NumCopies"]) \
                  and (nbparts > 4):
                # handle # of copies set by mozilla/kprinter
                self.set_copies(pagecount, parts[4])
            elif (parts[:6] == [b"{", b"pop", b"1", b"dict", b"dup", b"/NumCopies"]) \
                  and (nbparts > 6):
                # handle # of copies set by firefox/kprinter/cups (alternate syntax)
                self.set_copies(pagecount, parts[6])
            elif (part0 == br"%%Page:") or (part0 == br"(%%[Page:"):
                proceed = True
                try:
                    # treats both "%%Page: x x" and "%%Page: (x-y) z" (probably N-up mode)
                    newpagenum = int(line.split(b']')[0].split()[-1])
                except:
                    notinteger = True # It seems that sometimes it's not an integer but an EPS file name
                else:
                    notinteger = False
                    if newpagenum <= oldpagenum:
                        # Now correctly handles multiple copies when printed from MSOffice.
                        # Thanks to Jiri Popelka for the fix.
                        proceed = False
                    else:
                        oldpagenum = newpagenum
                if proceed and not notinteger:
                    pagecount += 1
                    self.pages[pagecount] = { "copies": self.pages[pagecount-1]["copies"] }
            elif (not prescribe) \
               and (parts[:3] == [r"%%BeginResource:", "procset", "pdf"]) \
               and not acrobatmarker:
                notrust = True # Let this stuff be managed by GhostScript, but we still extract number of copies
            elif line.startswith(b"/languagelevel where{pop languagelevel}{1}ifelse 2 ge{1 dict dup/NumCopies"):
                self.set_copies(pagecount, previousline[2:])
            elif (nbparts > 1) and (parts[1] == b"@copies"):
                self.set_copies(pagecount, part0)
            previousline = line

        # extract max number of copies to please the ghostscript parser, just
        # in case we will use it later
        self.copies = max([ v["copies"] for (k, v) in self.pages.items() ])

        # now apply the number of copies to each page
        if not pagecount and pagescomment:
            pagecount = pagescomment
        for pnum in range(1, pagecount + 1):
            page = self.pages.get(pnum, self.pages.get(1, self.pages.get(0, { "copies": 1 })))
            copies = page["copies"]
            pagecount += (copies - 1)
            self.logdebug("%s * page #%s" % (copies, pnum))

        self.logdebug("Internal parser said: %s pages" % pagecount)
        return pagecount, notrust

    def get_job_size(self):
        """Count pages in PostScript document."""
        self.copies = 1
        (nbpages, notrust) = self.natively()
        newnbpages = nbpages
        if notrust or not nbpages:
            try:
                newnbpages = self.through_ghost_script()
            except pdlparser.PDLParserError as msg:
                self.logdebug(msg)
        return max(nbpages, newnbpages)
