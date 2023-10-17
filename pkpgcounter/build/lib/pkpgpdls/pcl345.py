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
# $Id: pcl345.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements a page counter for PCL3/4/5 documents."""

import os
import mmap
from struct import unpack

from pkpgpdls import pdlparser
from pkpgpdls import pjl

NUL = chr(0x00)
LINEFEED = chr(0x0a)
FORMFEED = chr(0x0c)
ESCAPE = chr(0x1b)
ASCIILIMIT = chr(0x80)


class Parser(pdlparser.PDLParser):
    """A parser for PCL3, PCL4, PCL5 documents."""
    totiffcommands = ['pcl6 -sDEVICE=pdfwrite -r"%(dpi)i" -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET '
                      '-sOutputFile=- "%(infname)s" | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE '
                      '-dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(outfname)s" -',
                      'pcl6 -sDEVICE=pswrite -r"%(dpi)i" -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET '
                      '-sOutputFile=- "%(infname)s" | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE '
                      '-dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(outfname)s" -', ]
    required = ["pcl6", "gs"]
    format = "PCL3/4/5"
    mediasizes = {  # ESC&l####A
                    0: "Default",
                    1: "Executive",
                    2: "Letter",
                    3: "Legal",
                    6: "Ledger",
                    25: "A5",
                    26: "A4",
                    27: "A3",
                    45: "JB5",
                    46: "JB4",
                    71: "HagakiPostcard",
                    72: "OufukuHagakiPostcard",
                    80: "MonarchEnvelope",
                    81: "COM10Envelope",
                    90: "DLEnvelope",
                    91: "C5Envelope",
                    100: "B5Envelope",
                    101: "Custom",
                 }

    mediasources = {  # ESC&l####H
                     0: "Default",
                     1: "Main",
                     2: "Manual",
                     3: "ManualEnvelope",
                     4: "Alternate",
                     5: "OptionalLarge",
                     6: "EnvelopeFeeder",
                     7: "Auto",
                     8: "Tray1",
                   }

    orientations = {  # ESC&l####O
                     0: "Portrait",
                     1: "Landscape",
                     2: "ReversePortrait",
                     3: "ReverseLandscape",
                   }

    mediatypes = {  # ESC&l####M
                     0: "Plain",
                     1: "Bond",
                     2: "Special",
                     3: "Glossy",
                     4: "Transparent",
                   }

    def is_valid(self):
        """Returns True if data is PCL3/4/5, else False."""
        try:
            pos = 0
            while self.firstblock[pos] == chr(0):
                pos += 1
        except IndexError:
            return False
        else:
            firstblock = self.firstblock[pos:]
            if firstblock.startswith(b"\033E\033") or \
               firstblock.startswith(b"\033(") or \
               firstblock.startswith(b"\033%1BBPIN;") or \
               ((pos == 11000) and firstblock.startswith(b"\033")) or \
               (firstblock.startswith(b"\033*rbC") and (not self.lastblock[-3:] == b"\f\033@")) or \
               firstblock.startswith(b"\033*rB\033") or \
               firstblock.startswith(b"\033%8\033") or \
               (firstblock.find(b"\033%-12345X") != -1) or \
               (firstblock.find(b"@PJL ENTER LANGUAGE=PCL\012\015\033") != -1) or \
               (firstblock.startswith(bytes(0xcd)+bytes(0xca)) and (firstblock.find(b"\033E\033") != -1)):
                return True
            else:
                return False

    def set_page_dict(self, attribute, value):
        """Initializes a page dictionnary."""
        dic = self.pages.setdefault(self.pagecount, {"linescount": 1,
                                                     "copies": 1,
                                                     "mediasource": "Main",
                                                     "mediasize": "Default",
                                                     "mediatype": "Plain",
                                                     "orientation": "Portrait",
                                                     "escaped": "",
                                                     "duplex": 0})
        dic[attribute] = value

    def read_byte(self):
        """Reads a byte from the input stream."""
        tag = ord(self.minfile[self.pos])
        self.pos += 1
        return tag

    def end_page(self):
        """Handle the FF marker."""
        # self.logdebug("FORMFEED %i at %08x" % (self.pagecount, self.pos-1))
        if not self.hpgl2:
            # Increments page count only if we are not inside an HPGL2 block
            self.pagecount += 1

    def esc_percent(self):
        """Handles the ESC% sequence."""
        if self.minfile[self.pos: self.pos+7] == r"-12345X":
            # self.logdebug("Generic ESCAPE sequence at %08x" % self.pos)
            self.pos += 7
            buffer = []
            quotes = 0
            char = chr(self.read_byte())
            while ((char < ASCIILIMIT) or (quotes % 2)) and (char not in (FORMFEED, ESCAPE, NUL)):
                buffer.append(char)
                if char == '"':
                    quotes += 1
                char = chr(self.read_byte())
            self.set_page_dict("escaped", "".join(buffer))
            # self.logdebug("ESCAPED: %s" % "".join(buffer))
            self.pos -= 1   # Adjust position
        else:
            while 1:
                (value, end) = self.get_integer()
                if end == 'B':
                    self.enter_hpgl2()
                    while self.minfile[self.pos] != ESCAPE:
                        self.pos += 1
                    self.pos -= 1
                    return
                elif end == 'A':
                    self.exit_hpgl2()
                    return
                elif end is None:
                    return

    def enter_hpgl2(self):
        """Enters HPGL2 mode."""
        # self.logdebug("ENTERHPGL2 %08x" % self.pos)
        self.hpgl2 = True

    def exit_hpgl2(self):
        """Exits HPGL2 mode."""
        # self.logdebug("EXITHPGL2 %08x" % self.pos)
        self.hpgl2 = False

    def handle_tag(self, tagtable):
        """Handles tags."""
        tagtable[self.read_byte()]()

    def escape(self):
        """Handles the ESC character."""
        # self.logdebug("ESCAPE")
        self.handle_tag(self.esctags)

    def esc_amp(self):
        """Handles the ESC& sequence."""
        # self.logdebug("AMP")
        self.handle_tag(self.escamptags)

    def esc_dollar(self):
        """Handles the ESC$ sequence."""
        # self.logdebug("DOLLAR")
        self.handle_tag(self.escdollartags)

    def esc_star(self):
        """Handles the ESC* sequence."""
        # self.logdebug("STAR")
        self.handle_tag(self.escstartags)

    def esc_left_par(self):
        """Handles the ESC( sequence."""
        # self.logdebug("LEFTPAR")
        self.handle_tag(self.escleftpartags)

    def esc_right_par(self):
        """Handles the ESC( sequence."""
        # self.logdebug("RIGHTPAR")
        self.handle_tag(self.escrightpartags)

    def esc_e(self):
        """Handles the ESCE sequence."""
        # self.logdebug("RESET")
        self.resets += 1

    def esc_ampl(self):
        """Handles the ESC&l sequence."""
        while 1:
            (value, end) = self.get_integer()
            if value is None:
                return
            if end in ('h', 'H'):
                mediasource = self.mediasources.get(value, str(value))
                self.mediasourcesvalues.append(mediasource)
                self.set_page_dict("mediasource", mediasource)
                # self.logdebug("MEDIASOURCE %s" % mediasource)
            elif end in ('a', 'A'):
                mediasize = self.mediasizes.get(value, str(value))
                self.mediasizesvalues.append(mediasize)
                self.set_page_dict("mediasize", mediasize)
                # self.logdebug("MEDIASIZE %s" % mediasize)
            elif end in ('o', 'O'):
                orientation = self.orientations.get(value, str(value))
                self.orientationsvalues.append(orientation)
                self.set_page_dict("orientation", orientation)
                # self.logdebug("ORIENTATION %s" % orientation)
            elif end in ('m', 'M'):
                mediatype = self.mediatypes.get(value, str(value))
                self.mediatypesvalues.append(mediatype)
                self.set_page_dict("mediatype", mediatype)
                # self.logdebug("MEDIATYPE %s" % mediatype)
            elif end == 'X':
                self.copies.append(value)
                self.set_page_dict("copies", value)
                # self.logdebug("COPIES %i" % value)
            elif end == 'F':
                self.linesperpagevalues.append(value)
                self.linesperpage = value
                # self.logdebug("LINES PER PAGE: %i" % self.linesperpage)
            # else:
            #    self.logdebug("Unexpected end <%s> and value <%s>" % (end, value))

    def esc_ampa(self):
        """Handles the ESC&a sequence."""
        while 1:
            (value, end) = self.get_integer()
            if value is None:
                return
            if end == 'G':
                # self.logdebug("BACKSIDES %i" % value)
                self.backsides.append(value)
                self.set_page_dict("duplex", value)

    def esc_ampp(self):
        """Handles the ESC&p sequence."""
        while 1:
            (value, end) = self.get_integer()
            if value is None:
                return
            if end == 'X':
                self.pos += value
                # self.logdebug("SKIPTO %08x" % self.pos)

    def esc_starb(self):
        """Handles the ESC*b sequence."""
        while 1:
            (value, end) = self.get_integer()
            if (end is None) and (value is None):
                return
            if end in ('V', 'W', 'v', 'w'):
                self.pos += (value or 0)
                # self.logdebug("SKIPTO %08x" % self.pos)

    def esc_starr(self):
        """Handles the ESC*r sequence."""
        while 1:
            (value, end) = self.get_integer()
            if value is None:
                if end is None:
                    return
                elif end in ('B', 'C'):
                    # self.logdebug("EndGFX")
                    if self.startgfx:
                        self.endgfx.append(1)
                    else:
                        # self.logdebug("EndGFX found before StartGFX, ignored.")
                        pass
            if end == 'A' and (0 <= value <= 3):
                # self.logdebug("StartGFX %i" % value)
                self.startgfx.append(value)

    def esc_staropt_ampu(self):
        """Handles the ESC*o ESC*p ESC*t and ESC&u sequences."""
        while 1:
            (value, end) = self.get_integer()
            if value is None:
                return

    def esc_skip_something_w(self):
        """Handles the ESC???###W sequences."""
        while 1:
            (value, end) = self.get_integer()
            if value is None:
                return
            if end == 'W':
                self.pos += value
                # self.logdebug("SKIPTO %08x" % self.pos)

    def new_line(self):
        """Handles new lines markers."""
        if not self.hpgl2:
            dic = self.pages.get(self.pagecount, None)
            if dic is None:
                self.set_page_dict("linescount", 1)
                dic = self.pages.get(self.pagecount)
            nblines = dic["linescount"]
            self.set_page_dict("linescount", nblines + 1)
            if (self.linesperpage is not None) \
               and (dic["linescount"] > self.linesperpage):
                self.pagecount += 1

    def get_integer(self):
        """Returns an integer value and the end character."""
        sign = 1
        value = None
        while 1:
            char = chr(self.read_byte())
            if char in (NUL, ESCAPE, FORMFEED, ASCIILIMIT):
                self.pos -= 1  # Adjust position
                return None, None
            if char == '-':
                sign = -1
            elif not char.isdigit():
                if value is not None:
                    return sign*value, char
                else:
                    return value, char
            else:
                value = ((value or 0) * 10) + int(char)

    def skip_byte(self):
        """Skips a byte."""
        # self.logdebug("SKIPBYTE %08x ===> %02x" % (self.pos, ord(self.minfile[self.pos])))
        self.pos += 1

    def handle_image_runner(self):
        """Handles Canon ImageRunner tags."""
        tag = self.read_byte()
        if tag == ord(self.imagerunnermarker1[-1]):
            oldpos = self.pos-2
            codop = self.minfile[self.pos:self.pos+2]
            length = unpack(">H", self.minfile[self.pos+6:self.pos+8])[0]
            self.pos += 18
            if codop != self.imagerunnermarker2:
                self.pos += length
            self.logdebug("ImageRunner tag: Skip %i bytes from 0x%08x to 0x%08x" % (self.pos-oldpos, oldpos, self.pos))
        else:
            self.pos -= 1  # Adjust position

    def get_job_size(self):
        """Count pages in a PCL5 document.

           Should also work for PCL3 and PCL4 documents.

           Algorithm from pclcount
           (c) 2003, by Eduardo Gielamo Oliveira & Rodolfo Broco Manin
           published under the terms of the GNU General Public Licence v2.

           Backported from C to Python by Jerome Alet, then enhanced
           with more PCL tags detected. I think all the necessary PCL tags
           are recognized to correctly handle PCL5 files wrt their number
           of pages. The documentation used for this was:

           HP PCL/PJL Reference Set
           PCL5 Printer Language Technical Quick Reference Guide
           http://h20000.www2.hp.com/bc/docs/support/SupportManual/bpl13205/bpl13205.pdf
        """
        infileno = self.infile.fileno()
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        self.pages = {}
        self.pagecount = 0
        self.resets = 0
        self.backsides = []
        self.copies = []
        self.mediasourcesvalues = []
        self.mediasizesvalues = []
        self.orientationsvalues = []
        self.mediatypesvalues = []
        self.linesperpagevalues = []
        self.linesperpage = None
        self.startgfx = []
        self.endgfx = []
        self.hpgl2 = False
        self.imagerunnermarker1 = chr(0xcd) + chr(0xca) # Markers for Canon ImageRunner printers
        self.imagerunnermarker2 = chr(0x10) + chr(0x02)
        self.isimagerunner = (minfile[:2] == self.imagerunnermarker1)

        tags = [lambda: None] * 256
        tags[ord(LINEFEED)] = self.new_line
        tags[ord(FORMFEED)] = self.end_page
        tags[ord(ESCAPE)] = self.escape
        tags[ord(ASCIILIMIT)] = self.skip_byte
        tags[ord(self.imagerunnermarker1[0])] = self.handle_image_runner

        self.esctags = [lambda: None] * 256
        self.esctags[ord('%')] = self.esc_percent
        self.esctags[ord('*')] = self.esc_star
        self.esctags[ord('$')] = self.esc_dollar
        self.esctags[ord('&')] = self.esc_amp
        self.esctags[ord('(')] = self.esc_left_par
        self.esctags[ord(')')] = self.esc_right_par
        self.esctags[ord('E')] = self.esc_e

        self.escamptags = [lambda: None] * 256
        self.escamptags[ord('a')] = self.esc_ampa
        self.escamptags[ord('l')] = self.esc_ampl
        self.escamptags[ord('p')] = self.esc_ampp
        self.escamptags[ord('b')] = self.esc_skip_something_w
        self.escamptags[ord('n')] = self.esc_skip_something_w
        self.escamptags[ord('u')] = self.esc_staropt_ampu

        self.escstartags = [lambda: None] * 256
        self.escstartags[ord('b')] = self.esc_starb
        self.escstartags[ord('r')] = self.esc_starr
        self.escstartags[ord('o')] = self.esc_staropt_ampu
        self.escstartags[ord('p')] = self.esc_staropt_ampu
        self.escstartags[ord('t')] = self.esc_staropt_ampu
        self.escstartags[ord('c')] = self.esc_skip_something_w
        self.escstartags[ord('g')] = self.esc_skip_something_w
        self.escstartags[ord('i')] = self.esc_skip_something_w
        self.escstartags[ord('l')] = self.esc_skip_something_w
        self.escstartags[ord('m')] = self.esc_skip_something_w
        self.escstartags[ord('v')] = self.esc_skip_something_w

        self.escdollartags = [lambda: None] * 256
        self.escdollartags[ord('b')] = self.esc_skip_something_w

        self.escleftpartags = [lambda: None] * 256
        self.escleftpartags[ord('s')] = self.esc_skip_something_w
        self.escleftpartags[ord('f')] = self.esc_skip_something_w

        self.escrightpartags = [lambda: None] * 256
        self.escrightpartags[ord('s')] = self.esc_skip_something_w

        self.pos = 0
        try:
            try:
                while 1:
                    tags[self.read_byte()]()
            except IndexError:  # EOF ?
                pass
        finally:
            self.minfile.close()

        self.logdebug("Pagecount: \t\t\t%i" % self.pagecount)
        self.logdebug("Resets: \t\t\t%i" % self.resets)
        self.logdebug("Copies: \t\t\t%s" % self.copies)
        self.logdebug("NbCopiesMarks: \t\t%i" % len(self.copies))
        self.logdebug("MediaTypes: \t\t\t%s" % self.mediatypesvalues)
        self.logdebug("NbMediaTypes: \t\t\t%i" % len(self.mediatypesvalues))
        self.logdebug("MediaSizes: \t\t\t%s" % self.mediasizesvalues)
        nbmediasizes = len(self.mediasizesvalues)
        self.logdebug("NbMediaSizes: \t\t\t%i" % nbmediasizes)
        self.logdebug("MediaSources: \t\t\t%s" % self.mediasourcesvalues)
        nbmediasourcesdefault = len([m for m in self.mediasourcesvalues if m in ('Default', 'Auto')])
        nbmediasourcesnotdefault = len(self.mediasourcesvalues) - nbmediasourcesdefault
        self.logdebug("MediaSourcesDefault: \t\t%i" % nbmediasourcesdefault)
        self.logdebug("MediaSourcesNOTDefault: \t%i" % nbmediasourcesnotdefault)
        self.logdebug("Orientations: \t\t\t%s" % self.orientationsvalues)
        nborientations = len(self.orientationsvalues)
        self.logdebug("NbOrientations: \t\t\t%i" % nborientations)
        self.logdebug("StartGfx: \t\t\t%s" % len(self.startgfx))
        self.logdebug("EndGfx: \t\t\t%s" % len(self.endgfx))
        nbbacksides = len(self.backsides)
        self.logdebug("BackSides: \t\t\t%s" % self.backsides)
        self.logdebug("NbBackSides: \t\t\t%i" % nbbacksides)
        self.logdebug("IsImageRunner: \t\t\t%s" % self.isimagerunner)

#        if self.isimagerunner:
#            self.logdebug("Adjusting PageCount: +1")
#            self.pagecount += 1      # ImageRunner adjustment
        if self.isimagerunner:
            self.logdebug("Adjusting PageCount: -1")
            self.pagecount -= 1      # ImageRunner adjustment
        elif self.linesperpage is not None:
            self.logdebug("Adjusting PageCount: +1")
            self.pagecount += 1      # Adjusts for incomplete last page
        elif len(self.startgfx) == len(self.endgfx) == 0:
            if self.resets % 2:
                if (not self.pagecount) and (nborientations < nbbacksides):
                    self.logdebug("Adjusting PageCount because of backsides: %i" % nbbacksides)
                    self.pagecount = nbbacksides
                elif nborientations == self.pagecount + 1:
                    self.logdebug("Adjusting PageCount: +1")
                    self.pagecount += 1
                elif (self.pagecount > 1) and (nborientations == self.pagecount - 1):
                    self.logdebug("Adjusting PageCount: -1")
                    self.pagecount -= 1
        elif (self.pagecount > 1) and\
             (self.resets == 2) and\
             (not nbmediasourcesdefault) and\
             (nbmediasourcesnotdefault == 1):
            self.logdebug("Adjusting PageCount: -1")
            self.pagecount -= 1

        self.pagecount = self.pagecount or nbmediasourcesdefault or nbmediasizes or nborientations or self.resets

        if not self.pagecount:
            if self.resets == len(self.startgfx):
                self.pagecount = self.resets

        defaultpjlcopies = 1
        defaultduplexmode = "Simplex"
        defaultpapersize = ""
        oldpjlcopies = -1
        oldduplexmode = ""
        oldpapersize = ""
        for pnum in range(self.pagecount):
            # if no number of copies defined, take the preceding one else the one set before any page else 1.
            page = self.pages.get(pnum, self.pages.get(pnum - 1, self.pages.get(0, {"copies": 1, "mediasource":
                                                                                    "Main", "mediasize": "Default",
                                                                                    "mediatype": "Plain", "orientation":
                                                                                    "Portrait", "escaped": "",
                                                                                    "duplex": 0})))
            pjlstuff = page["escaped"]
            if pjlstuff:
                pjlparser = pjl.PJLParser(pjlstuff)
                nbdefaultcopies = int(pjlparser.default_variables.get("COPIES", -1))
                nbcopies = int(pjlparser.environment_variables.get("COPIES", -1))
                nbdefaultqty = int(pjlparser.default_variables.get("QTY", -1))
                nbqty = int(pjlparser.environment_variables.get("QTY", -1))
                if nbdefaultcopies > -1:
                    defaultpjlcopies = nbdefaultcopies
                if nbdefaultqty > -1:
                    defaultpjlcopies = nbdefaultqty
                if nbcopies > -1:
                    pjlcopies = nbcopies
                elif nbqty > -1:
                    pjlcopies = nbqty
                else:
                    if oldpjlcopies == -1:
                        pjlcopies = defaultpjlcopies
                    else:
                        pjlcopies = oldpjlcopies
                if page["duplex"]:
                    duplexmode = "Duplex"
                else:
                    defaultdm = pjlparser.default_variables.get("DUPLEX", "")
                    if defaultdm:
                        if defaultdm.upper() == "ON":
                            defaultduplexmode = "Duplex"
                        else:
                            defaultduplexmode = "Simplex"
                    envdm = pjlparser.environment_variables.get("DUPLEX", "")
                    if envdm:
                        if envdm.upper() == "ON":
                            duplexmode = "Duplex"
                        else:
                            duplexmode = "Simplex"
                    else:
                        duplexmode = oldduplexmode or defaultduplexmode
                defaultps = pjlparser.default_variables.get("PAPER", "")
                if defaultps:
                    defaultpapersize = defaultps
                envps = pjlparser.environment_variables.get("PAPER", "")
                if envps:
                    papersize = envps
                else:
                    if not oldpapersize:
                        papersize = defaultpapersize
                    else:
                        papersize = oldpapersize
            else:
                if oldpjlcopies == -1:
                    pjlcopies = defaultpjlcopies
                else:
                    pjlcopies = oldpjlcopies

                duplexmode = (page["duplex"] and "Duplex") or oldduplexmode or defaultduplexmode
                if not oldpapersize:
                    papersize = defaultpapersize
                else:
                    papersize = oldpapersize
                papersize = oldpapersize or page["mediasize"]
            if page["mediasize"] != "Default":
                papersize = page["mediasize"]
            if not duplexmode:
                duplexmode = oldduplexmode or defaultduplexmode
            oldpjlcopies = pjlcopies
            oldduplexmode = duplexmode
            oldpapersize = papersize
            copies = max(pjlcopies, page["copies"])  # Was: pjlcopies * page["copies"]
            self.pagecount += (copies - 1)
            self.logdebug("%s*%s*%s*%s*%s*%s*BW" % (copies,
                                                    page["mediatype"],
                                                    papersize,
                                                    page["orientation"],
                                                    page["mediasource"],
                                                    duplexmode))

        return self.pagecount
