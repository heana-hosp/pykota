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
# $Id: plain.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements a page counter for plain text documents."""

from pkpgpdls import pdlparser


class Parser(pdlparser.PDLParser):
    """A parser for plain text documents."""
    totiffcommands = ['enscript --quiet --portrait --no-header --columns 1 --output - "%(infname)s" \
    | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" -',
    'a2ps --borders 0 --quiet --portrait --no-header --columns 1 --output - "%(infname)s" | gs -sDEVICE=tiff24nc \
    -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" -',
                     ]
    required = [ "a2ps | enscript", "gs" ]
    openmode = "rU"
    format = "plain text"

    def is_valid(self):
        """Returns True if data is plain text, else False.

           It's hard to detect a plain text file, so we just try to
           extract lines from the first block (sufficiently large).
           If it's impossible to find one we consider it's not plain text.
        """
        lines = self.firstblock.split(b"\r\n")
        if len(lines) == 1:
            lines = lines[0].split(b"\r")
            if len(lines) == 1:
                lines = lines[0].split(b"\n")
        if len(lines) > 1:
            return True
        else:
            return False

    def get_job_size(self):
        """Counts pages in a plain text document."""
        pagesize = 66   # TODO: Does this vary wrt the default page size ?
        # TODO: /etc/papersize and /etc/paper.config
        pagecount = 0
        linecount = 0
        for line in str(self.infile):
            linecount += 1
            if linecount > pagesize:
                pagecount += 1
                linecount = 0
            else:
                cnt = line.count("\f")
                if cnt:
                    pagecount += cnt
                    linecount = 0

        return pagecount + 1    # NB: empty files are catched in is_valid()
