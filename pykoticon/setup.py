#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-

"""Packaging and installation script for PyKotIcon."""

# PyKotIcon - Client side helper for PyKota and other applications
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
# $Id: setup.py 110 2006-06-08 16:54:21Z jerome $
#
#

from distutils.core import setup
import sys
import os
import imp
import glob
try :
    import py2exe
except ImportError :
    if sys.platform == "win32" :
        sys.stderr.write("py2exe is not installed ! ABORTING.\n")
        sys.exit(-1)
    else :    
        directory = os.sep.join(["share", "pykoticon"])
        mandir = os.sep.join(["share", "man", "man1"])
        manpages = glob.glob(os.sep.join(["man", "*.1"]))    
        initialdatafiles = [(mandir, manpages)]
        withPy2EXE = False
else :        
    directory = "."
    initialdatafiles = []
    withPy2EXE = True

config = imp.load_source("config", os.path.join("bin", "pykoticon"))
setupDictionary = { "name" : "pykoticon", 
                    "version" : config.__version__,
                    "license" : config.__license__,
                    "description" : config.__doc__,
                    "author" : config.__author__,
                    "author_email" : config.__author_email__,
                    "url" : config.__url__,
                    "data_files" : initialdatafiles \
                      + [(directory, glob.glob(os.path.join("icons", "*.ico")))],
                  }
if withPy2EXE :
    setupDictionary["windows"] = [ os.path.join("bin", "pykoticon") ]
    setupDictionary["data_files"].append((directory, [os.path.join("bin", "pykoticon.vbs")]))
    setupDictionary["data_files"].append((directory, [os.path.join(".", "COPYING")]))
else :
    setupDictionary["scripts"] = [os.path.join("bin", "pykoticon")]
setup(**setupDictionary)
