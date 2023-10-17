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
# $Id: escpages03.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for TIFF documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser
import pjl

class Parser(pdlparser.PDLParser) :
    """A parser for ESC/PageS03 documents."""
    format = "ESC/PageS03"
    def isValid(self) :        
        """Returns True if data is TIFF, else False."""
        if self.firstblock.startswith("\033\1@EJL") and \
            (self.firstblock.find("=ESC/PAGES03\n") != -1) :
            return True
        else :    
            return False
    
    def getJobSize(self) :
        """Counts pages in an ESC/PageS03 document.
        
           Algorithm by Jerome Alet.
           Reverse engineered the file format.
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        marker = "=ESC/PAGES03\n"
        startpos = minfile.find(marker)
        startsequence = chr(0x1d)
        if startpos == -1 :
            raise pdlparser.PDLParserError, "Invalid ESC/PageS03 file."
        startpos += len(marker)
        if minfile[startpos] != startsequence :
            raise pdlparser.PDLParserError, "Invalid ESC/PageS03 file."
        endsequence = "eps{I"
        lgendsequence = len(endsequence)
        try :
            try :    
                while True :
                    if minfile[startpos] == startsequence :
                        skiplen = 0
                        while True :
                            startpos += 1
                            c = minfile[startpos]
                            if not c.isdigit() :
                                break
                            else :
                                skiplen = (skiplen * 10) + int(c)
                        if minfile[startpos:startpos+lgendsequence] == endsequence :
                            startpos += (skiplen + lgendsequence)
                    else :
                        if minfile[startpos:startpos+6] == "\033\1@EJL" :
                            # Probably near the end of the file.
                            # Test suite was too small to be sure.
                            ejlparser = pjl.EJLParser(minfile[startpos:])
                            pagecount = ejlparser.environment_variables.get("PAGES", "1")
                            if pagecount.startswith('"') and pagecount.endswith('"') :
                                pagecount = pagecount[1:-1]
                            pagecount = int(pagecount)    
                            if pagecount <= 0 :
                                pagecount = 1 # TODO : 0 or 1000000 ??? ;-)
                            break
                        startpos += 1    
            except IndexError :            
                pass
        finally :        
            minfile.close()
        return pagecount
