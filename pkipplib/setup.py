#! /usr/bin/env python3
# -*- coding: utf-8 -*-
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
# $Id$
#

import os
from importlib.machinery import SourceFileLoader

from setuptools import setup

#version = imp.load_source("version", os.path.join("pkipplib", "version.py"))
version = SourceFileLoader("version", os.path.join("pkipplib", "version.py")).load_module()

setup(name="pkipplib", version=version.__version__,
      license="GNU GPL",
      description=version.__doc__,
      author="Jerome Alet",
      author_email="alet@librelogiciel.com",
      url="http://www.pykota.com/software/pkipplib",
      packages=["pkipplib"],
      scripts=[os.path.join("bin", "pksubscribe")])
