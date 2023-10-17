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
# $Id: pdf.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements a page counter for PDF documents.

   Some informations taken from PDF Reference v1.7 by Adobe.
"""

import re


from pkpgpdls import pdlparser

PDFWHITESPACE = chr(0) \
                + chr(9) \
                + chr(10) \
                + chr(12) \
                + chr(13) \
                + chr(32)
PDFDELIMITERS = r"()<>[]{}/%"
PDFMEDIASIZE = "/MediaBox [xmin ymin xmax ymax]"  # an example. MUST be present in Page objects

class PDFObject :
    """A class for PDF objects."""
    def __init__(self, major, minor, description) :
        """Initialize the PDF object."""
        self.major = major
        self.minor = minor
        self.majori = int(major)
        self.minori = int(minor)
        self.description = description
        self.comments = []
        self.content = []
        self.parent = None
        self.kids = []

class Parser(pdlparser.PDLParser):
    """A parser for PDF documents."""
    totiffcommands = ['gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" '
                      '-sOutputFile="%(outfname)s" "%(infname)s"']
    required = ["gs"]
    openmode = "rU"
    format = "PDF"

    def is_valid(self):
        """Returns True if data is PDF, else False."""
        if self.firstblock.startswith(b"%PDF-") or \
                self.firstblock.startswith(b"\033%-12345X%PDF-") or \
                ((self.firstblock[:128].find(b"\033%-12345X") != -1) and (
                        self.firstblock.upper().find(b"LANGUAGE=PDF") != -1)) \
                or (self.firstblock.find(b"%PDF-") != -1):
            return True
        else:
            return False

    def very_fast_andnot_always_correctget_jobsize(self):
        """Counts pages in a PDF document.

            This method works great in the general case,
            and is around 30 times faster than the active
            one.
            Unfortunately it doesn't take into account documents
            with redacted pages (only made with FrameMaker ?)
            where an existing PDF object is replaced with one
            with the same major number a higher minor number.
         """
        newpageregexp = re.compile(rb"/Type\s*/Page[/>\s]")
        return len(newpageregexp.findall(self.infile.read()))

    def get_job_size(self):
        """Counts pages in a PDF document."""
        # First we start with a generic PDF parser.
        lastcomment = None
        objects = {}
        inobject = 0
        objre = re.compile(br"\s?(\d+)\s+(\d+)\s+obj[<\s/]?")
        for line in self.infile:
            line = line.strip()
            if line.startswith(b"% "):
                if inobject:
                    obj.comments.append(line)
                else:
                    lastcomment = line[2:]
            else:
                # New object begins here
                result = objre.search(line)
                if result is not None:
                    (major, minor) = line[result.start():result.end()].split()[:2]
                    obj = PDFObject(major, minor, lastcomment)
                    obj.content.append(line[result.end():])
                    inobject = 1
                elif line.startswith(b"endobj") \
                        or line.startswith(b">> endobj") \
                        or line.startswith(b">>endobj"):
                    # Handle previous object, if any
                    if inobject:
                        # only overwrite older versions of this object
                        # same minor seems to be possible, so the latest one
                        # found in the file will be the one we keep.
                        # if we want the first one, just use > instead of >=
                        oldobject = objects.setdefault(major, obj)
                        if int(minor) >= oldobject.minori:
                            objects[major] = obj
                            # self.logdebug("Object(%i, %i) overwritten with Object(%i, %i)" % (oldobject.majori, oldobject.minori, obj.majori, obj.minori))
                        # self.logdebug("Object(%i, %i)" % (obj.majori, obj.minori))
                        inobject = 0
                else:
                    if inobject:
                        obj.content.append(line)

        # Now we check each PDF object we've just created.
        newpageregexp = re.compile(br"(/Type)\s?(/Page)[/>\s]", re.I)
        pagecount = 0
        for obj in objects.values():
            content = "".join(obj.content)
            count = len(newpageregexp.findall(content))
            if count and (content != rb"<</Type /Page>>"):  # Empty pages which are not rendered ?
                pagecount += count
        return pagecount
