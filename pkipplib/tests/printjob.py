y#! /usr/bin/env python3
# -*- coding: ISO-8859-15 -*-
#
# pkipplib : IPP and CUPS support for Python
#
# (c) 2003-2013 Jerome Alet <alet@librelogiciel.com>
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
# Sample code to print a PDF document
#
from pkipplib import pkipplib

# Use CUPS server on localhost:631
cups=pkipplib.CUPS()

# Create a new request with correct operation id
req=cups.newRequest(operationid=pkipplib.IPP_PRINT_JOB)

# Fill the required parameters
req.operation["requesting-user-name"] = ("nameWithoutLanguage", "jerome")
req.operation["printer-uri"] = ("uri", cups.identifierToURI("printers", "HP2100"))
req.operation["document-format"] = ("mimeMediaType", "application/pdf")

# Read the PDF datas and make them part of the request
inputfile = open("testpage.pdf", "rb")
req.data = inputfile.read()
inputfile.close()

# Send all this to CUPS
response = cups.doRequest(req)

