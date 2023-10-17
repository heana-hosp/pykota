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
# $Id: lidil.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for HP LIDIL format.

   Documentation used : 
   
        hplip-2.7.10/prnt/ldl.py
        hplip-2.7.10/prnt/hpijs/ldlencap.h
"""

import struct

import pdlparser

HEADERSIZE = 10 # LIDIL header is 10 bytes long

# Packet types taken from hplip-2.7.10/prnt/ldl.py
PACKET_TYPE_COMMAND = 0
PACKET_TYPE_DISABLE_PACING = 1
PACKET_TYPE_ENABLE_PACING = 2
PACKET_TYPE_RESUME_NORMAL_OPERATION = 3
PACKET_TYPE_DISABLE_RESPONSES = 4
PACKET_TYPE_ENABLE_RESPONSES = 5
PACKET_TYPE_RESET_LIDIL = 6
PACKET_TYPE_SYNC = 7
PACKET_TYPE_SYNC_COMPLETE = 8

# Command codes we are interested in.
LDL_LOAD_PAGE = 1
LDL_EJECT_PAGE = 2

class Parser(pdlparser.PDLParser) :
    """A parser for HP LIDIL documents."""
    format = "Hewlett-Packard LIDIL"
    def isValid(self) :    
        """Returns True if data is LIDIL, else False."""
        # Beginning Of File marker is a Sync packet, followed with
        # a Sync Complete packet followed with a Reset packet.
        # We just look at the start of the Sync packet for simplicity's sake.
        BOFMarker = "$\x01\x00\x00\x07"
        # End Of File marker is a Sync Complete packet followed
        # with a Reset packet. We ignore the preceding Sync packet
        # for simplicity's sake.
        EOFMarker = "$\x00\x10\x00\x08\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff$$\x00\x10\x00\x06\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff$" 
        if self.firstblock.startswith(BOFMarker) \
           and self.lastblock.endswith(EOFMarker) :
            return True
        else :    
            return False
        
    def getJobSize(self) :
        """Computes the number of pages in a HP LIDIL document."""
        unpack = struct.unpack
        ejectpage = loadpage = 0
        try :
            while True :
                header = self.infile.read(HEADERSIZE)
                if not header :
                    break
                if (len(header) != HEADERSIZE) or (header[0] != "$") :
                    # Invalid header or no Frame Sync byte.
                    raise pdlparser.PDLParserError, "This file doesn't seem to be valid Hewlett-Packard LIDIL datas."
                (framesync,     
                 cmdlength,
                 dummy,
                 packettype,
                 commandnumber,
                 referencenumber,
                 datalength) = unpack(">BHBBBHH", header)
                if packettype == PACKET_TYPE_COMMAND :
                    if commandnumber == LDL_LOAD_PAGE :
                        loadpage += 1
                    elif commandnumber == LDL_EJECT_PAGE :
                        ejectpage += 1
                self.infile.seek(cmdlength + datalength - len(header), 1) # relative seek
        except struct.error :    
            raise pdlparser.PDLParserError, "This file doesn't seem to be valid Hewlett-Packard LIDIL datas."
            
        # Number of page eject commands should be sufficient,
        # but we never know : someone could try to cheat the printer
        # by loading a page but not ejecting it, and ejecting it manually
        # later on. Not sure if the printers would support this, but
        # taking the max value works around the problem in any case.
        self.logdebug("Load : %i    Eject : %i" % (loadpage, ejectpage))
        return max(loadpage, ejectpage)
