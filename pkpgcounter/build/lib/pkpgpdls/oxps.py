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
# $Id: oxps.py 3578 2019-02-14 08:46:15Z jose.camilo $
#

"""This modules implements a page counter for OXPS/XPS documents."""

import zipfile
import re
from pkpgpdls import pdlparser


class Parser(pdlparser.PDLParser):
    """A parser for OXPS/XPS documents.""" # TODO Parser from xps/oxps.
    # totiffcommands = ['xvfb-run -a abiword --import-extension=.odt --print="| gs -sDEVICE=tiff24nc \
    #                   -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r\"%(dpi)i\" '
    #                   '-sOutputFile=\"%(outfname)s\" -" "%(infname)s"']
    totiffcommands = []
    required = ["xvfb-run", "xauth", "abiword", "gs"]
    format = "OXPS/XPS"

    def is_valid(self):
        """Get base metafiles - Returns True if data is OXPS/XPS, else False."""
        if self.firstblock[:2] == b"PK":
            try:
                self.archive = zipfile.ZipFile(self.filename)
                self.contentxml = self.archive.read("[Content_Types].xml")
                self.metaxml = self.archive.read("Metadata/Job_PT.xml")
                self.files = self.archive.filelist
            except KeyError:
                return False
            else:
                return True
        else:
            return False

    def get_job_size(self):
        """Counts pages in an oxps/xps document.
           Algorithm by eslijunior and josecamilo.
        """
        pagecount = 0
        try:
            # Unzip file e extract information
            archive = zipfile.ZipFile(self.filename)
            for files in archive.namelist():
                # check files with extension fpage in zipfile
                if re.search(r'fpage$', files):
                    pagecount += 1
        except FileNotFoundError:
            pagecount = 0
        return pagecount
