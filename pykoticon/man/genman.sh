#! /bin/sh
#
# PyKotIcon - Client side helper for PyKota and other applications
#
# (c) 2003, 2004, 2005, 2006 Jerome Alet <alet@librelogiciel.com>
# You're welcome to redistribute this software under the
# terms of the GNU General Public Licence version 2.0
# or, at your option, any higher version.
#
# You can read the complete GNU GPL in the file COPYING
# which should come along with this software, or visit
# the Free Software Foundation's WEB site http://www.fsf.org
#
# $Id: genman.sh 94 2006-06-06 22:10:22Z jerome $
#
for prog in pykoticon ; do 
    echo $prog ;
    help2man --no-info --section=1 --manual "User Commands" --source="C@LL - Conseil Internet & Logiciels Libres" --output=$prog.1 $prog ; 
    echo ;
done
