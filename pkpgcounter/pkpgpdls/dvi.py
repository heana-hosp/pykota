# -*- coding: utf-8 -*-
#
# pkpgcounter: a generic Page Description Language parser
#
# (c) 2003-2019 Jerome Alet <alet@librelogiciel.com>
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
# $Id: dvi.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements a page counter for DVI documents."""

import os
import mmap
from struct import unpack

from pkpgpdls import pdlparser


class Parser(pdlparser.PDLParser):
    """A parser for DVI documents."""
    totiffcommands = [ 'dvips -q -o - "%(infname)s" | gs -sDEVICE=tiff24nc '
                       '-dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" -']
    required = [ "dvips", "gs" ]
    format = "DVI"
    
    def is_valid(self):
        """Returns True if data is DVI, else False."""
        try:
            if (self.firstblock[0] == b'0xf7') and (self.lastblock[-1] == b'0xdf'):
                return True
            else:
                return False
        except IndexError:
            return False

    def get_job_size(self):
        """Counts pages in a DVI document.

           Algorithm by Jerome Alet.

           The documentation used for this was:

           http://www.math.umd.edu/~asnowden/comp-cont/dvi.html
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        pos = -1
        eofchar = chr(0xdf)
        postchar = chr(0xf8)
        try:
            try:
                while minfile[pos] == eofchar:
                    pos -= 1
                idbyte = minfile[pos]
                if idbyte != minfile[1]:
                    raise IndexError("Invalid DVI file.")
                pos = unpack(">I", minfile[pos - 4:pos])[0]
                if minfile[pos] != postchar:
                    raise IndexError("Invalid DVI file.")
                pagecount = unpack(">H", minfile[pos + 27: pos + 29])[0]
            except IndexError:  # EOF ?
                pass
        finally:
            minfile.close()  # reached EOF
        return pagecount
