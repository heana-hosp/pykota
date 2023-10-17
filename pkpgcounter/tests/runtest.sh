#! /bin/sh
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

echo "Analyzing colors..."
if ! [ -f "colors.pdf" ]  ; then
   python ./runcolors.py ; 
fi ;
echo 

for cspace in BW RGB CMY CMYK GC ; do
    echo "Colorspace : $cspace" ;
    pkpgcounter --colorspace $cspace colors.pdf ;
    echo ;
done    

echo "Generating testsuite..."
gunzip <master.ps.gz | python ./gstests.py -

