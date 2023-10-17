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
# $Id: qpdl.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for QPDL (aka SPL2) documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser
import pjl

class Parser(pdlparser.PDLParser) :
    """A parser for QPDL (aka SPL2) documents."""
    format = "QPDL (aka SPL2)"
    mediasizes = { 
                    # The first values are identical to that of PCLXL
                    0 : "Letter",
                    1 : "Legal",
                    2 : "A4",
                    3 : "Executive",
                    4 : "Ledger",
                    5 : "A3",
                    6 : "COM10Envelope",
                    7 : "MonarchEnvelope",
                    8 : "C5Envelope",
                    9 : "DLEnvelope",
                    10 : "JB4",
                    11 : "JB5",
                    12 : "B5Envelope",
                    12 : "B5",
                    14 : "JPostcard",
                    15 : "JDoublePostcard",
                    16 : "A5",
                    17 : "A6",
                    18 : "JB6",
                    21 : "Custom",
                    23 : "C6",
                    24 : "Folio",
                 }   
                 
    mediasources = {             
                     # Again, values are identical to that of PCLXL
                     0 : "Default",
                     1 : "Auto",
                     2 : "Manual",
                     3 : "MultiPurpose",
                     4 : "UpperCassette",
                     5 : "LowerCassette",
                     6 : "EnvelopeTray",
                     7 : "ThirdCassette",
                   }
            
    def isValid(self) :    
        """Returns True if data is QPDL aka SPL2, else False."""
        if ((self.firstblock[:128].find("\033%-12345X") != -1) and \
             ((self.firstblock.find("LANGUAGE=QPDL") != -1) or \
              (self.firstblock.find("LANGUAGE = QPDL") != -1))) :
            return True
        else :    
            return False
            
    def beginPage(self, nextpos) :
        """Indicates the beginning of a new page, and extracts media information."""
        self.pagecount += 1
        
        copies = unpack(self.unpackShort, self.minfile[nextpos+1:nextpos+3])[0]
        mediasize = ord(self.minfile[nextpos+3])
        mediasource = ord(self.minfile[nextpos+8])
        duplexmode = unpack(self.unpackShort, self.minfile[nextpos+10:nextpos+12])[0]
        
        self.pages[self.pagecount] = { "copies" : copies, 
                                       "mediasize" : self.mediasizes.get(mediasize, str(mediasize)),
                                       "mediasource" : self.mediasources.get(mediasource, str(mediasource)),
                                       "duplex" : duplexmode,
                                     } 
        return 16       # Length of a page header
        
    def endPage(self, nextpos) :    
        """Indicates the end of a page."""
        epcopies = unpack(self.unpackShort, self.minfile[nextpos:nextpos+2])[0]
        bpcopies = self.pages[self.pagecount]["copies"]
        if epcopies != bpcopies :
            self.logdebug("ERROR: discrepancy between beginPage (%i) and endPage (%i) copies" % (bpcopies, epcopies))
        return 2        # Length of a page footer
        
    def beginBand(self, nextpos) :
        """Indicates the beginning of a new band."""
        bandlength = unpack(self.unpackLong, self.minfile[nextpos+6:nextpos+10])[0]
        return bandlength + 10 # Length of a band header - length of checksum
        
    def littleEndian(self) :
        """Toggles to little endianness."""
        self.unpackType = { 1 : "B", 2 : "<H", 4 : "<I" }
        self.unpackShort = self.unpackType[2]
        self.unpackLong = self.unpackType[4]
        return 0
        
    def bigEndian(self) :
        """Toggles to big endianness."""
        self.unpackType = { 1 : "B", 2 : ">H", 4 : ">I" }
        self.unpackShort = self.unpackType[2]
        self.unpackLong = self.unpackType[4]
        return 0
    
    def escape(self, nextpos) :    
        """Handles the ESC code."""
        pos = endpos = nextpos
        minfile = self.minfile
        if minfile[pos : pos+8] == r"%-12345X" :
            endpos = pos + 9
            endmark = chr(0x0c) + chr(0x00) + chr(0x1b)
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
            stuff.append(minfile[pos : endpos])
            self.logdebug("Escaped datas : [%s]" % repr(minfile[pos : endpos]))
        return endpos - pos
        
    def maybeEOF(self, nextpos) :    
        """Tries to detect the EOF marker."""
        if self.minfile[nextpos:nextpos+9] == self.eofmarker :
            return 9
        else :    
            return 0
        
    def getJobSize(self) :
        """Counts pages in a QPDL (SPL2) document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           Spécification Technique (documentation non officielle)
           Le Language SPL2
           par Aurélien Croc
           http://splix.ap2c.org
        """
        # Initialize table of tags
        self.tags = [ lambda pos : 0 ] * 256    
        self.tags[0x00] = self.beginPage
        self.tags[0x01] = self.endPage
        self.tags[0x09] = self.maybeEOF
        self.tags[0x0c] = self.beginBand
        self.tags[0x1b] = self.escape # The escape code
        
        self.eofmarker = "\033%-12345X"
        
        infileno = self.infile.fileno()
        self.pages = { 0 : { "copies" : 1, 
                             "orientation" : "Default", 
                             "mediatype" : "Plain", 
                             "mediasize" : "Default", 
                             "mediasource" : "Default", 
                             "duplex" : None,
                           } 
                     }      
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        self.pagecount = 0
        self.escapedStuff = {}   # For escaped datas, mostly PJL commands
        self.bigEndian()
        pos = 0
        tags = self.tags
        try :
            try :
                while 1 :
                    tag = ord(minfile[pos])
                    pos += 1
                    pos += tags[tag](pos)
            except IndexError : # EOF ?            
                pass
        finally :
            self.minfile.close()
            
        defaultduplexmode = "Simplex"
        defaultpapersize = ""
        defaultpjlcopies = 1    
        oldpjlcopies = -1
        oldduplexmode = ""
        oldpapersize = ""
        for pnum in range(1, self.pagecount + 1) :
            # NB : is number of copies is 0, the page won't be output
            # but the formula below is still correct : we want 
            # to decrease the total number of pages in this case.
            page = self.pages.get(pnum, self.pages.get(1, { "copies" : 1, "mediasize" : "Default", "duplex" : None }))
            pjlstuff = self.escapedStuff.get(pnum, self.escapedStuff.get(0, []))
            if pjlstuff :
                pjlparser = pjl.PJLParser("".join(pjlstuff))
                nbdefaultcopies = int(pjlparser.default_variables.get("COPIES", -1))
                nbcopies = int(pjlparser.environment_variables.get("COPIES", -1))
                nbdefaultqty = int(pjlparser.default_variables.get("QTY", -1))
                nbqty = int(pjlparser.environment_variables.get("QTY", -1))
                if nbdefaultcopies > -1 :
                    defaultpjlcopies = nbdefaultcopies
                if nbdefaultqty > -1 :
                    defaultpjlcopies = nbdefaultqty
                if nbcopies > -1 :
                    pjlcopies = nbcopies
                elif nbqty > -1 :
                    pjlcopies = nbqty
                else :
                    if oldpjlcopies == -1 :    
                        pjlcopies = defaultpjlcopies
                    else :    
                        pjlcopies = oldpjlcopies    
                if page["duplex"] :        
                    duplexmode = page["duplex"]
                else :    
                    defaultdm = pjlparser.default_variables.get("DUPLEX", "")
                    if defaultdm :
                        if defaultdm.upper() == "ON" :
                            defaultduplexmode = "Duplex"
                        else :    
                            defaultduplexmode = "Simplex"
                    envdm = pjlparser.environment_variables.get("DUPLEX", "")
                    if envdm :
                        if envdm.upper() == "ON" :
                            duplexmode = "Duplex"
                        else :    
                            duplexmode = "Simplex"
                    else :        
                        if not oldduplexmode :
                            duplexmode = defaultduplexmode
                        else :    
                            duplexmode = oldduplexmode
                defaultps = pjlparser.default_variables.get("PAPER", "")
                if defaultps :
                    defaultpapersize = defaultps
                envps = pjlparser.environment_variables.get("PAPER", "")
                if envps :
                    papersize = envps
                else :    
                    if not oldpapersize :
                        papersize = defaultpapersize
                    else :    
                        papersize = oldpapersize
            else :        
                if oldpjlcopies == -1 :
                    pjlcopies = defaultpjlcopies
                else :    
                    pjlcopies = oldpjlcopies
                if not oldduplexmode :
                    duplexmode = defaultduplexmode
                else :    
                    duplexmode = oldduplexmode
                if not oldpapersize :    
                    papersize = defaultpapersize
                else :    
                    papersize = oldpapersize
                duplexmode = oldduplexmode
                papersize = oldpapersize or page["mediasize"]
            if page["mediasize"] != "Default" :
                papersize = page["mediasize"]
            if not duplexmode :    
                duplexmode = oldduplexmode or defaultduplexmode
            oldpjlcopies = pjlcopies    
            oldduplexmode = duplexmode
            oldpapersize = papersize
            copies = max(pjlcopies, page["copies"]) # Was : pjlcopies * page["copies"]
            self.pagecount += (copies - 1)
            self.logdebug("%s*%s*%s*%s" % (copies, 
                                           papersize, 
                                           page["mediasource"], 
                                           duplexmode))
        return self.pagecount
