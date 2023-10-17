' PyKotIcon - Client side helper for PyKota
'
' (c) 2003, 2004, 2005, 2006 Jerome Alet <alet@librelogiciel.com>
' This program is free software; you can redistribute it and/or modify
' it under the terms of the GNU General Public License as published by
' the Free Software Foundation; either version 2 of the License, or
' (at your option) any later version.
'
' This program is distributed in the hope that it will be useful,
' but WITHOUT ANY WARRANTY; without even the implied warranty of
' MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
' GNU General Public License for more details.
' 
' You should have received a copy of the GNU General Public License
' along with this program; if not, write to the Free Software
' Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
'
' $Id: pykoticon.vbs 79 2006-05-01 17:14:07Z jerome $
'
'
' Edit the last line of this file to add all your print servers
' hostnames or IP addresses instead of "nordine.ateur" and optionally
' define another TCP port to listen to.
'
set Wshshell= WScript.createobject("wscript.shell")
retcode = Wshshell.run ("%comspec% /C pykoticon.exe --port 7654 nordine.ateur", 0, FALSE)
