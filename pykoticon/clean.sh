#! /bin/sh
#
# PyKotIcon - Client side helper for PyKota and other applications
#
# (c) 2005 Jerome Alet <alet@librelogiciel.com>
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
# $Id: clean.sh 95 2006-06-06 22:10:57Z jerome $

# Use this to clean the tree from temporary files

rm -fr MANIFEST build dist
rm -f bin/pykoticonc
find . -name "*.bak" -exec rm -f {} \;
find . -name "*~" -exec rm -f {} \;
find . -name "*.pyc" -exec rm -f {} \;
find . -name "*.pyo" -exec rm -f {} \;
find . -name "*.jem" -exec rm -f {} \;
find . -name "*.tmp" -exec rm -f {} \;
