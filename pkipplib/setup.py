#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkipplib : IPP and CUPS support for Python
#
# (c) 2003, 2004, 2005, 2006 Jerome Alet <alet@librelogiciel.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# $Id: setup.py 32 2006-06-24 13:36:38Z jerome $
#

import os
import imp
from distutils.core import setup

version = imp.load_source("version", os.path.join("pkipplib", "version.py"))

setup(name = "pkipplib", version = version.__version__,
      license = "GNU GPL",
      description = version.__doc__,
      author = "Jerome Alet",
      author_email = "alet@librelogiciel.com",
      url = "http://www.pykota.com/software/pkipplib",
      packages = [ "pkipplib" ],
      scripts = [os.path.join("bin", "pksubscribe")])

