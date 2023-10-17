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
# $Id: bj.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for Canon BJ documents."""

import os
import mmap

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for Canon BJ documents."""
    format = "Canon BJ/BJC"
    def isValid(self) :        
        """Returns True if data is BJ/BJC, else False."""
        if self.firstblock.startswith("\033[K\002\000") :
            return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a Canon BJ document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           ghostscript-8.60/src/gdevbj*.c
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        pos = 0
        try :
            try :
                while True :
                    if minfile[pos] == "\033" :
                        # Look if we've found an initialization sequence
                        # through the Set Initial Condition command
                        pageheader = minfile[pos:pos+7]
                        if pageheader in ("\033[K\002\000\000\017", 
                                          "\033[K\002\000\000\044",
                                          "\033[K\002\000\004\044") :
                            pagecount += 1
                            pos += 6
                    pos += 1
            except IndexError : # EOF ?
                pass
        finally :        
            minfile.close() # reached EOF
        return pagecount
