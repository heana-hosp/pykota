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
# $Id: pnmascii.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements a page counter for PNM (ascii) documents."""

from pkpgpdls import pdlparser


class Parser(pdlparser.PDLParser):
    """A parser for PNM (ascii) documents."""
    openmode = "rU"
    format = "PNM (ascii)"

    def is_valid(self):
        """Returns True if data is ASCII PNM, else False."""
        if self.firstblock.split()[0] in ("P1", "P2", "P3"):
            self.marker = self.firstblock[:2]
            return True
        else:
            return False

    def get_job_size(self):
        """Counts pages in a PNM (ascii) document."""
        pagecount = 0
        linecount = 0
        divby = 1
        marker = self.marker
        for line in self.infile:
            linecount += 1
            if (linecount == 2) and (line.find("device=pksm") != -1):
                # Special case of cmyk map
                divby = 4
            # Unfortunately any whitespace is valid,
            # so we do it the slow way...
            pagecount += line.split().count(marker)

        if not (pagecount % divby):
            return pagecount // divby
        else:
            return pagecount
