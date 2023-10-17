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
# $Id: mscrap.py 374 2007-12-09 14:26:15Z jerome $
#

"""This module implements a page counter for Microsoft Word (r) (tm) (c) (etc...) documents"""

import os
import tempfile

import pdlparser
import version

class Parser(pdlparser.PDLParser) :
    """A parser for that MS crap thing."""
    totiffcommands = [ 'xvfb-run -a abiword --import-extension=.doc --print="| gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r\"%(dpi)i\" -sOutputFile=\"%(outfname)s\" -" "%(infname)s"' ]
    required = [ "xvfb-run", "xauth", "abiword", "gs" ]
    format = "Microsoft shitty"
    def isValid(self) :    
        """Returns True if data is MS crap, else False.
        
           Identifying datas taken from the file command's magic database.
           IMPORTANT : some magic values are not reused here because they
           IMPORTANT : seem to be specific to some particular i18n release.
        """   
        if self.firstblock.startswith("PO^Q`") \
           or self.firstblock.startswith("\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") \
           or self.firstblock.startswith("\xfe7\x00#") \
           or self.firstblock.startswith("\xdb\xa5-\x00\x00\x00") \
           or self.firstblock.startswith("\x31\xbe\x00\x00") \
           or self.firstblock[2112:].startswith("MSWordDoc") :
            # Here we do the missing test because all commands will be needed even in page counting mode
            if self.isMissing(self.required) :
                return False
            else :    
                return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a Microsoft Word (r) (tm) (c) (etc...) document.

           First we convert from .doc to .ps, then we use the PostScript parser.
        """
        doctops = 'xvfb-run -a abiword --import-extension=.doc --print="%(outfname)s" "%(infname)s"'
        workfile = tempfile.NamedTemporaryFile(mode="w+b")
        try :
            outfname = workfile.name
            infname = self.filename
            status = os.system(doctops % locals())
            if status or not os.stat(outfname).st_size :
                raise pdlparser.PDLParserError, "Impossible to convert input document %(infname)s to PostScript" % locals()
            psinputfile = open(outfname, "rb")
            try :
                (first, last) = self.parent.readFirstAndLastBlocks(psinputfile)
                import postscript
                return postscript.Parser(self.parent, 
                                         outfname, 
                                         (first, last)).getJobSize()
            finally :
                psinputfile.close()
        finally :    
            workfile.close()
        raise pdlparser.PDLParserError, "Impossible to count pages in %(infname)s" % locals()
