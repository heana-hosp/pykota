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
# $Id: hbp.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for Brother HBP documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for HBP documents."""
    format = "Brother HBP"
    def isValid(self) :        
        """Returns True if data is HBP, else False."""
        if self.firstblock.find("@PJL ENTER LANGUAGE = HBP\n") != -1 :
            return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a HBP document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           http://sf.net/projects/hbp-for-brother/
           
           IMPORTANT : this may not work since @F should be sufficient,
           but the documentation really is unclear and I don't know
           how to skip raster data blocks for now.
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        
        formfeed = "@G" + chr(0) + chr(0) + chr(1) + chr(0xff) + "@F"
        fflen = len(formfeed)
        pos = 0
        try :
            try :
                while True :
                    if (minfile[pos] == "@") \
                       and (minfile[pos:pos+fflen] == formfeed) :
                        pagecount += 1
                        pos += fflen
                    else :        
                        pos += 1
            except IndexError : # EOF ?
                pass
        finally :        
            minfile.close() # reached EOF
        return pagecount
