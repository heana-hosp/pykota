#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
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
# $Id: setup.py 282 2007-09-10 20:47:40Z jerome $
#
#

import sys
import glob
import os
import shutil
try :
    from distutils.core import setup
except ImportError, msg :    
    sys.stderr.write("%s\n" % msg)
    sys.stderr.write("You need the DistUtils Python module.\nunder Debian, you may have to install the python-dev package.\nOf course, YMMV.\n")
    sys.exit(-1)
    
try :    
    from PIL import Image
except ImportError :    
    sys.stderr.write("You need the Python Imaging Library (aka PIL).\nYou can grab it from http://www.pythonware.com\n")
    sys.exit(-1)
    
try :    
    import psyco
except ImportError :    
    sys.stderr.write("WARN: If you are running on a 32 Bits x86 platform, you should install the Python Psyco module if possible, this would greatly speedup parsing. NB : Psyco doesn't work on other platforms, so don't worry if you're in this case.\n")
    
sys.path.insert(0, "pkpgpdls")
from pkpgpdls.version import __version__, __doc__

data_files = []
mofiles = glob.glob(os.sep.join(["po", "*", "*.mo"]))
for mofile in mofiles :
    lang = mofile.split(os.sep)[1]
    directory = os.sep.join(["share", "locale", lang, "LC_MESSAGES"])
    data_files.append((directory, [ mofile ]))
    
docdir = "share/doc/pkpgcounter"    
docfiles = ["README", "COPYING", "BUGS", "CREDITS", "NEWS"]
data_files.append((docdir, docfiles))

directory = os.sep.join(["share", "man", "man1"])
manpages = glob.glob(os.sep.join(["man", "*.1"]))    
data_files.append((directory, manpages))

setup(name = "pkpgcounter", version = __version__,
      license = "GNU GPL",
      description = __doc__,
      author = "Jerome Alet",
      author_email = "alet@librelogiciel.com",
      url = "http://www.pykota.com/software/pkpgcounter/",
      packages = [ "pkpgpdls" ],
      scripts = [ "bin/pkpgcounter" ],
      data_files = data_files)
      
