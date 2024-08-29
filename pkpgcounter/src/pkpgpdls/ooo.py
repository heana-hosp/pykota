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
# $Id: ooo.py
#

"""This modules implements a page counter for OpenDocument documents."""
import zipfile
from pkpgpdls import pdlparser


class Parser(pdlparser.PDLParser):
    """A parser for Opendocument - Writer. ODS extension"""
    totiffcommands = ['xvfb-run -a abiword --import-extension=.odt --print="| gs -sDEVICE=tiff24nc \
                      -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r\"%(dpi)i\" '
                      '-sOutputFile=\"%(outfname)s\" -" "%(infname)s"']
    required = ["xvfb-run", "xauth", "abiword", "gs"]
    format = "Open Document Format"
    
    def is_valid(self):
        """Returns True if data is OpenDocument, else False."""
        if self.firstblock[:2] == b"PK":
            try:
                self.archive = zipfile.ZipFile(self.filename)
                self.contentxml = self.archive.read("content.xml")
                self.metaxml = self.archive.read("meta.xml")
                self.stylexml = self.archive.read("styles.xml")
                self.mimetype = self.archive.read("mimetype")
            except GeneratorExit:
                return False
            else:
                return True
        else:
            return False

    def get_job_size(self):
        """Counts pages in an OpenOffice.org document.

           Algorithm by Jerome Alet, eslijunior, josecamilo.
        """
        # Validate extension based on mimetype metadata
        pagecount = 0
        try:
            # Try Opendocument Text - ODS extension
            if b"application/vnd.oasis.opendocument.text" in self.mimetype:
                try:
                    index = self.metaxml.index(b"meta:page-count")
                    pagecount = int(self.metaxml[index:].split(b'\"')[1])
                except KeyError:
                    raise pdlparser.PDLParserError("Can't get page on metadata on ODT extension.")
            #  Try Opendocument Spreadsheet - ODS extension, for while, won't store page count or preview on metadata.
            if b"application/vnd.oasis.opendocument.spreadsheet" in self.mimetype:
                raise pdlparser.PDLParserError("Can't get page on metadata on ODS extension.")
            # Try Opendocument Presentation
            if b"application/vnd.oasis.opendocument.presentation" in self.mimetype:
                # Count number of draw:page-number on contentxml. Only count slides base - default print.
                try:
                    index = self.contentxml.index(b"draw:page-number")
                    pagecount = self.contentxml[index:].count(b'draw:page-number')
                except KeyError:
                    raise pdlparser.PDLParserError("Can't get page on metadata on ODP extension.")
            # Try Opendocument Graphics
            if b"application/vnd.oasis.opendocument.graphics" in self.mimetype:
                try:
                    index = self.contentxml.index(b"draw:name")
                    pagecount = self.contentxml[index:].count(b'draw:name=')
                except KeyError:
                    raise pdlparser.PDLParserError("Can't get page on metadata on ODG extension.")
            else:
                raise pdlparser.PDLParserError("This Opendocument format are not yet supported.")
        finally:
            return pagecount