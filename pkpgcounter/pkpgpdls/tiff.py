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
# $Id: tiff.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for TIFF documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for TIFF documents."""
    totiffcommands = [ 'cp "%(infname)s" "%(outfname)s"' ]
    required = [ "cp" ]
    format = "TIFF"
    def isValid(self) :        
        """Returns True if data is TIFF, else False."""
        littleendian = (chr(0x49)*2) + chr(0x2a) + chr(0)
        bigendian = (chr(0x4d)*2) + chr(0) + chr(0x2a)
        if self.firstblock[:4] in (littleendian, bigendian) :
            return True
        else :    
            return False
    
    def getJobSize(self) :
        """Counts pages in a TIFF document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
           
           http://www.ee.cooper.edu/courses/course_pages/past_courses/EE458/TIFF/
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        littleendian = (chr(0x49)*2) + chr(0x2a) + chr(0)
        bigendian = (chr(0x4d)*2) + chr(0) + chr(0x2a)
        if minfile[:4] == littleendian :
            integerbyteorder = "<I"
            shortbyteorder = "<H"
        elif minfile[:4] == bigendian :
            integerbyteorder = ">I"
            shortbyteorder = ">H"
        else :    
            raise pdlparser.PDLParserError, "Unknown file endianness."
        pos = 4    
        try :
            try :    
                nextifdoffset = unpack(integerbyteorder, minfile[pos : pos + 4])[0]
                while nextifdoffset :
                    direntrycount = unpack(shortbyteorder, minfile[nextifdoffset : nextifdoffset + 2])[0]
                    pos = nextifdoffset + 2 + (direntrycount * 12)
                    nextifdoffset = unpack(integerbyteorder, minfile[pos : pos + 4])[0]
                    pagecount += 1
            except IndexError :            
                pass
        finally :        
            minfile.close()
        return pagecount
