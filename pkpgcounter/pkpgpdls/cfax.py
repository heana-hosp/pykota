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
# $Id: cfax.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for Structured Fax documents."""

import struct

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for Structured Fax documents."""
    format = "Structured Fax"
    def isValid(self) :        
        """Returns True if data is Structured Fax, else False."""
        if self.firstblock.startswith("Sfff") :
            return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a Structured Fax document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           http://delphi.pjh2.de/articles/graphic/sff_format.php
        """
        unpack = struct.unpack
        pagecount = 0
        docheader = self.infile.read(20)
        try :
            (sffid,
             version,
             reserved,
             userinfo,
             docpagecount,
             offsetfirstpage,
             offsetlastpage,
             offsetdocumentend) = unpack("<4sBBHHHII", docheader)
            self.infile.seek(offsetfirstpage - len(docheader), 1)     
            while True :
                headerid = self.infile.read(1)
                if not headerid :
                    break
                headerid = ord(headerid)    
                if 1 <= headerid <= 216 : # Normal record header
                    self.infile.seek(headerid, 1)
                elif headerid == 255 :    # Illegal line / Additional user info
                    additionalbyte = self.infile.read(1)
                    if not additionalbyte :
                        break
                    additionalbyte = ord(additionalbyte)    
                    if 1 <= additionalbyte <= 255 :
                        # Skip additional user information (reserved)
                        self.infile.seek(additionalbyte, 1)
                elif not headerid :        
                    # Record with more than 216 MH-coded bytes
                    recordlen = self.infile.read(2)
                    if not recordlen :
                        break
                    recordlen = unpack("<H", recordlen)[0]    
                    self.infile.seek(recordlen, 1)
                elif headerid == 254 : # Page header
                    pageheader = self.infile.read(17)
                    if not pageheader : 
                        break
                    headerlen = ord(pageheader[0])
                    if not headerlen :
                        break # End Of Document
                    (vres,
                     hres,
                     coding,
                     reserved,
                     linelen,
                     pagelen,
                     offsetpreviouspage,
                     offsetnextpage) = unpack("<4BHHII", pageheader[1:])
                    pagecount += 1    
                    if (offsetnextpage == 1) or (vres == 255) :
                        break # End Of Document
                    self.infile.seek(offsetnextpage, 1)    
        except struct.error :     
             raise pdlparser.PDLParserError, "Invalid Structured Fax datas"
        return max(docpagecount, pagecount)     
