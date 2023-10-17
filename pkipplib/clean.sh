#! /bin/sh
#
# pkipplib : IPP support for Python
#
# (c) 2003, 2004, 2005 Jerome Alet <alet@librelogiciel.com>
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
# $Id: clean.sh 15 2006-05-22 19:22:59Z jerome $

# Use this to clean the tree from temporary files

rm -f MANIFEST
rm -fr build dist
find . -name "*.bak" -exec rm -f {} \;
find . -name "*~" -exec rm -f {} \;
find . -name "*.pyc" -exec rm -f {} \;
find . -name "*.pyo" -exec rm -f {} \;
find . -name "*.jem" -exec rm -f {} \;
