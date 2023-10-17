#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
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
# $Id: spl1.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for SPL1 documents."""

import os
import mmap
import struct

import pdlparser
import version

ESCAPECHARS = (chr(0x1b), chr(0x24))

class Parser(pdlparser.PDLParser) :
    """A parser for SPL1 documents."""
    format = "SPL1 (aka GDI)"
    def isValid(self) :    
        """Returns True if data is SPL1, else False."""
        if ((self.firstblock[:128].find("\033%-12345X") != -1) and \
            (self.firstblock.find("$PJL ") != -1) and \
             ((self.firstblock.find("LANGUAGE=SMART") != -1) or \
              (self.firstblock.find("LANGUAGE = SMART") != -1))) :
            return True
        else :    
            return False
            
    def littleEndian(self) :
        """Toggles to little endianness."""
        self.unpackType = { 1 : "B", 2 : "<H", 4 : "<I" }
        self.unpackShort = self.unpackType[2]
        self.unpackLong = self.unpackType[4]
        # self.logdebug("Little Endian")
        return 0
        
    def bigEndian(self) :
        """Toggles to big endianness."""
        self.unpackType = { 1 : "B", 2 : ">H", 4 : ">I" }
        self.unpackShort = self.unpackType[2]
        self.unpackLong = self.unpackType[4]
        # self.logdebug("Big Endian")
        return 0
    
    def escape(self, nextpos) :    
        """Handles the ESC code."""
        self.isbitmap = False
        pos = endpos = nextpos
        minfile = self.minfile
        if minfile[pos : pos+8] == r"%-12345X" :
            endpos = pos + 9
        elif minfile[pos-1] in ESCAPECHARS :    
            endpos = pos
        else :    
            return 0
        endmark = (chr(0x1b), chr(0x00))
        asciilimit = chr(0x80)
        quotes = 0
        while (minfile[endpos] not in endmark) and \
               ((minfile[endpos] < asciilimit) or (quotes % 2)) :
            if minfile[endpos] == '"' :
                quotes += 1
            endpos += 1
            
        # Store this in a per page mapping.    
        # NB : First time will be at page 0 (i.e. **before** page 1) !
        stuff = self.escapedStuff.setdefault(self.pagecount, [])
        datas = minfile[pos-1 : endpos]
        stuff.append(datas)
        if datas.endswith("$PJL BITMAP START\r\n") :
            self.isbitmap = True
            # self.logdebug("New bitmap")
        self.logdebug("Escaped datas : [%s]" % repr(datas))
        return endpos - pos + 1
        
    def getJobSize(self) :
        """Counts pages in an SPL1 document.
        
           Algorithm by Jerome Alet.
        """
        infileno = self.infile.fileno()
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        self.pagecount = 0
        self.escapedStuff = {}   # For escaped datas, mostly PJL commands
        self.bigEndian()
        self.isbitmap = False
        pos = 0
        unpack = struct.unpack
        try :
            try :
                while 1 :
                    tag = minfile[pos]
                    if tag in ESCAPECHARS :
                        pos += self.escape(pos+1)
                    else :    
                        if not self.isbitmap :
                            raise pdlparser.PDLParserError, "Unfortunately SPL1 is incompletely recognized. Parsing aborted. Please report the problem to %s" % version.__authoremail__
                        (offset,
                         seqnum) = unpack(">IH", minfile[pos:pos+6])
                        # self.logdebug("Offset : %i      Sequence Number : %i" % (offset, seqnum))
                        if not seqnum : 
                            # Sequence number resets to 0 for each new page.
                            self.pagecount += 1
                        pos += 4 + offset
            except struct.error, msg :     
                raise pdlparser.PDLParserError, "Unfortunately SPL1 is incompletely recognized (%s). Parsing aborted. Please report the problem to %s" % (msg, version.__authoremail__)
            except IndexError : # EOF ?            
                pass
        finally :
            minfile.close()
        return self.pagecount
