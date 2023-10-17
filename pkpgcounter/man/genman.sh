#! /bin/sh
#
# pkpgcounter : a generic Page Description Language parser.
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
# $Id: genman.sh 350 2007-11-28 23:14:47Z jerome $
#
for prog in pkpgcounter ; do 
    echo "$prog" ;
    help2man --no-info \
             --section=1 \
	     --name="count number of pages required to print various types of documents" \
	     --manual="User Commands" \
	     --source="C@LL - Conseil Internet & Logiciels Libres" \
	     --output="temp$prog.1" \
	     $prog ; 
    /bin/sed -e "s/--/\\\-\\\-/g" <"temp$prog.1" >"$prog.1" ;
    /bin/rm -f "temp$prog.1"
    echo ;
done
