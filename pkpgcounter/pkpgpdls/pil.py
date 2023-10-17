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
# $Id: pil.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for image formats supported by the Python Imaging Library."""

import pdlparser

try :
    from PIL import Image
except ImportError :    
    sys.stderr.write("ERROR: You MUST install the Python Imaging Library (python-imaging) for pkpgcounter to work.\n")
    raise pdlparser.PDLParserError, "The Python Imaging Library is missing."

import version

class Parser(pdlparser.PDLParser) :
    """A parser for plain text documents."""
    totiffcommands = [ 'convert "%(infname)s" "%(outfname)s"' ]  
    required = [ "convert" ]
    def isValid(self) :    
        """Returns True if data is an image format supported by PIL, else False."""   
        try :
            image = Image.open(self.filename)
        except (IOError, OverflowError) :    
            return False
        else :    
            self.format = "%s (%s)" % (image.format, image.format_description)
            return True
            
    def getJobSize(self) :
        """Counts pages in an image file."""
        index = 0
        image = Image.open(self.filename)
        try :
            while True :
                index += 1              
                image.seek(index)
        except EOFError :        
            pass
        return index    
