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
# $Id: ooo.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for OpenDocument documents."""

import sys
import zipfile

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for OpenOffice.org documents."""
    totiffcommands = [ 'xvfb-run -a abiword --import-extension=.odt --print="| gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r\"%(dpi)i\" -sOutputFile=\"%(outfname)s\" -" "%(infname)s"' ]
    required = [ "xvfb-run", "xauth", "abiword", "gs" ]
    format = "ISO/IEC DIS 26300"
    def isValid(self) :        
        """Returns True if data is OpenDocument, else False."""
        if self.firstblock[:2] == "PK" :
            try :
                self.archive = zipfile.ZipFile(self.filename)
                self.contentxml = self.archive.read("content.xml")
                self.metaxml = self.archive.read("meta.xml")
            except :    
                return False
            else :
                return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in an OpenOffice.org document.
        
           Algorithm by Jerome Alet.
        """
        pagecount = 0
        try :
            # First try with Text documents
            index = self.metaxml.index("meta:page-count=")
            pagecount = int(self.metaxml[index:].split('"')[1])
        except :
            # Now try with Impress documents
            pagecount = self.contentxml.count("<draw:page ")
            if not pagecount :
                # Probably a Spreadsheet document
                raise pdlparser.PDLParserError, "OpenOffice.org's spreadsheet documents are not yet supported."
        return pagecount
