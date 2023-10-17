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
# $Id: pcl345.py 374 2007-12-09 14:26:15Z jerome $
#

"""This modules implements a page counter for PCL3/4/5 documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser
import pjl

NUL = chr(0x00)
LINEFEED = chr(0x0a)
FORMFEED = chr(0x0c)
ESCAPE = chr(0x1b)
ASCIILIMIT = chr(0x80)

class Parser(pdlparser.PDLParser) :
    """A parser for PCL3, PCL4, PCL5 documents."""
    totiffcommands = [ 'pcl6 -sDEVICE=pdfwrite -r"%(dpi)i" -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -sOutputFile=- "%(infname)s" | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(outfname)s" -', 
                       'pcl6 -sDEVICE=pswrite -r"%(dpi)i" -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -sOutputFile=- "%(infname)s" | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(outfname)s" -',
                     ]
    required = [ "pcl6", "gs" ]
    format = "PCL3/4/5"
    mediasizes = {  # ESC&l####A
                    0 : "Default",
                    1 : "Executive",
                    2 : "Letter",
                    3 : "Legal",
                    6 : "Ledger", 
                    25 : "A5",
                    26 : "A4",
                    27 : "A3",
                    45 : "JB5",
                    46 : "JB4",
                    71 : "HagakiPostcard",
                    72 : "OufukuHagakiPostcard",
                    80 : "MonarchEnvelope",
                    81 : "COM10Envelope",
                    90 : "DLEnvelope",
                    91 : "C5Envelope",
                    100 : "B5Envelope",
                    101 : "Custom",
                 }   
                 
    mediasources = { # ESC&l####H
                     0 : "Default",
                     1 : "Main",
                     2 : "Manual",
                     3 : "ManualEnvelope",
                     4 : "Alternate",
                     5 : "OptionalLarge",
                     6 : "EnvelopeFeeder",
                     7 : "Auto",
                     8 : "Tray1",
                   }
                   
    orientations = { # ESC&l####O
                     0 : "Portrait",
                     1 : "Landscape",
                     2 : "ReversePortrait",
                     3 : "ReverseLandscape",
                   }
                   
    mediatypes = { # ESC&l####M
                     0 : "Plain",
                     1 : "Bond",
                     2 : "Special",
                     3 : "Glossy",
                     4 : "Transparent",
                   }
        
    def isValid(self) :    
        """Returns True if data is PCL3/4/5, else False."""
        try :
            pos = 0
            while self.firstblock[pos] == chr(0) :
                pos += 1
        except IndexError :        
            return False
        else :    
            firstblock = self.firstblock[pos:]
            if firstblock.startswith("\033E\033") or \
               firstblock.startswith("\033%1BBPIN;") or \
               ((pos == 11000) and firstblock.startswith("\033")) or \
               (firstblock.startswith("\033*rbC") and (not self.lastblock[-3:] == "\f\033@")) or \
               firstblock.startswith("\033*rB\033") or \
               firstblock.startswith("\033%8\033") or \
               (firstblock.find("\033%-12345X") != -1) or \
               (firstblock.find("@PJL ENTER LANGUAGE=PCL\012\015\033") != -1) or \
               (firstblock.startswith(chr(0xcd)+chr(0xca)) and (firstblock.find("\033E\033") != -1)) :
                return True
            else :    
                return False
        
    def setPageDict(self, attribute, value) :
        """Initializes a page dictionnary."""
        dic = self.pages.setdefault(self.pagecount, { "linescount" : 1,
                                                      "copies" : 1, 
                                                      "mediasource" : "Main", 
                                                      "mediasize" : "Default", 
                                                      "mediatype" : "Plain", 
                                                      "orientation" : "Portrait", 
                                                      "escaped" : "", 
                                                      "duplex": 0 })
        dic[attribute] = value
        
    def readByte(self) :    
        """Reads a byte from the input stream."""
        tag = ord(self.minfile[self.pos])
        self.pos += 1
        return tag
        
    def endPage(self) :    
        """Handle the FF marker."""
        #self.logdebug("FORMFEED %i at %08x" % (self.pagecount, self.pos-1))
        if not self.hpgl2 :
            # Increments page count only if we are not inside an HPGL2 block
            self.pagecount += 1
        
    def escPercent(self) :    
        """Handles the ESC% sequence."""
        if self.minfile[self.pos : self.pos+7] == r"-12345X" :
            #self.logdebug("Generic ESCAPE sequence at %08x" % self.pos)
            self.pos += 7
            buffer = []
            quotes = 0
            char = chr(self.readByte())
            while ((char < ASCIILIMIT) or (quotes % 2)) and (char not in (FORMFEED, ESCAPE, NUL)) :  
                buffer.append(char)
                if char == '"' :
                    quotes += 1
                char = chr(self.readByte())
            self.setPageDict("escaped", "".join(buffer))
            #self.logdebug("ESCAPED : %s" % "".join(buffer))
            self.pos -= 1   # Adjust position
        else :    
            while 1 :
                (value, end) = self.getInteger()
                if end == 'B' :
                    self.enterHPGL2()
                    while self.minfile[self.pos] != ESCAPE :
                        self.pos += 1
                    self.pos -= 1    
                    return 
                elif end == 'A' :    
                    self.exitHPGL2()
                    return
                elif end is None :    
                    return
        
    def enterHPGL2(self) :    
        """Enters HPGL2 mode."""
        #self.logdebug("ENTERHPGL2 %08x" % self.pos)
        self.hpgl2 = True
        
    def exitHPGL2(self) :    
        """Exits HPGL2 mode."""
        #self.logdebug("EXITHPGL2 %08x" % self.pos)
        self.hpgl2 = False
        
    def handleTag(self, tagtable) :    
        """Handles tags."""
        tagtable[self.readByte()]()
        
    def escape(self) :    
        """Handles the ESC character."""
        #self.logdebug("ESCAPE")
        self.handleTag(self.esctags)
        
    def escAmp(self) :    
        """Handles the ESC& sequence."""
        #self.logdebug("AMP")
        self.handleTag(self.escamptags)
        
    def escStar(self) :    
        """Handles the ESC* sequence."""
        #self.logdebug("STAR")
        self.handleTag(self.escstartags)
        
    def escLeftPar(self) :    
        """Handles the ESC( sequence."""
        #self.logdebug("LEFTPAR")
        self.handleTag(self.escleftpartags)
        
    def escRightPar(self) :    
        """Handles the ESC( sequence."""
        #self.logdebug("RIGHTPAR")
        self.handleTag(self.escrightpartags)
        
    def escE(self) :    
        """Handles the ESCE sequence."""
        #self.logdebug("RESET")
        self.resets += 1
        
    def escAmpl(self) :    
        """Handles the ESC&l sequence."""
        while 1 :
            (value, end) = self.getInteger()
            if value is None :
                return
            if end in ('h', 'H') :
                mediasource = self.mediasources.get(value, str(value))
                self.mediasourcesvalues.append(mediasource)
                self.setPageDict("mediasource", mediasource)
                #self.logdebug("MEDIASOURCE %s" % mediasource)
            elif end in ('a', 'A') :
                mediasize = self.mediasizes.get(value, str(value))
                self.mediasizesvalues.append(mediasize)
                self.setPageDict("mediasize", mediasize)
                #self.logdebug("MEDIASIZE %s" % mediasize)
            elif end in ('o', 'O') :
                orientation = self.orientations.get(value, str(value))
                self.orientationsvalues.append(orientation)
                self.setPageDict("orientation", orientation)
                #self.logdebug("ORIENTATION %s" % orientation)
            elif end in ('m', 'M') :
                mediatype = self.mediatypes.get(value, str(value))
                self.mediatypesvalues.append(mediatype)
                self.setPageDict("mediatype", mediatype)
                #self.logdebug("MEDIATYPE %s" % mediatype)
            elif end == 'X' :
                self.copies.append(value)
                self.setPageDict("copies", value)
                #self.logdebug("COPIES %i" % value)
            elif end == 'F' :    
                self.linesperpagevalues.append(value)
                self.linesperpage = value
                #self.logdebug("LINES PER PAGE : %i" % self.linesperpage)
            #else :
            #    self.logdebug("Unexpected end <%s> and value <%s>" % (end, value))
                
    def escAmpa(self) :    
        """Handles the ESC&a sequence."""
        while 1 :
            (value, end) = self.getInteger()
            if value is None :
                return
            if end == 'G' :    
                #self.logdebug("BACKSIDES %i" % value)
                self.backsides.append(value)
                self.setPageDict("duplex", value)
                
    def escAmpp(self) :    
        """Handles the ESC&p sequence."""
        while 1 :
            (value, end) = self.getInteger()
            if value is None :
                return
            if end == 'X' :    
                self.pos += value
                #self.logdebug("SKIPTO %08x" % self.pos)
                
    def escStarb(self) :    
        """Handles the ESC*b sequence."""
        while 1 :
            (value, end) = self.getInteger()
            if (end is None) and (value is None) :
                return
            if end in ('V', 'W', 'v', 'w') :    
                self.pos += (value or 0)
                #self.logdebug("SKIPTO %08x" % self.pos)
                
    def escStarr(self) :    
        """Handles the ESC*r sequence."""
        while 1 :
            (value, end) = self.getInteger()
            if value is None :
                if end is None :
                    return
                elif end in ('B', 'C') :        
                    #self.logdebug("EndGFX")
                    if self.startgfx :
                        self.endgfx.append(1)
                    else :    
                        #self.logdebug("EndGFX found before StartGFX, ignored.")
                        pass
            if end == 'A' and (0 <= value <= 3) :
                #self.logdebug("StartGFX %i" % value)
                self.startgfx.append(value)
                
    def escStaroptAmpu(self) :    
        """Handles the ESC*o ESC*p ESC*t and ESC&u sequences."""
        while 1 :
            (value, end) = self.getInteger()
            if value is None :
                return
        
    def escSkipSomethingW(self) :    
        """Handles the ESC???###W sequences."""
        while 1 :
            (value, end) = self.getInteger()
            if value is None :
                return
            if end == 'W' :    
                self.pos += value
                #self.logdebug("SKIPTO %08x" % self.pos)
                
    def newLine(self) :            
        """Handles new lines markers."""
        if not self.hpgl2 :
            dic = self.pages.get(self.pagecount, None)
            if dic is None :
                self.setPageDict("linescount", 1)                              
                dic = self.pages.get(self.pagecount)
            nblines = dic["linescount"]    
            self.setPageDict("linescount", nblines + 1)                              
            if (self.linesperpage is not None) \
               and (dic["linescount"] > self.linesperpage) :
                self.pagecount += 1
        
    def getInteger(self) :    
        """Returns an integer value and the end character."""
        sign = 1
        value = None
        while 1 :
            char = chr(self.readByte())
            if char in (NUL, ESCAPE, FORMFEED, ASCIILIMIT) :
                self.pos -= 1 # Adjust position
                return (None, None)
            if char == '-' :
                sign = -1
            elif not char.isdigit() :
                if value is not None :
                    return (sign*value, char)
                else :
                    return (value, char)
            else :    
                value = ((value or 0) * 10) + int(char)    
        
    def skipByte(self) :    
        """Skips a byte."""
        #self.logdebug("SKIPBYTE %08x ===> %02x" % (self.pos, ord(self.minfile[self.pos])))
        self.pos += 1
        
    def handleImageRunner(self) :    
        """Handles Canon ImageRunner tags."""
        tag = self.readByte()
        if tag == ord(self.imagerunnermarker1[-1]) :
            oldpos = self.pos-2
            codop = self.minfile[self.pos:self.pos+2]
            length = unpack(">H", self.minfile[self.pos+6:self.pos+8])[0]
            self.pos += 18
            if codop != self.imagerunnermarker2 :
                self.pos += length
            self.logdebug("IMAGERUNNERTAG SKIP %i AT %08x" % (self.pos-oldpos, self.pos))
        else :
            self.pos -= 1 # Adjust position
                
    def getJobSize(self) :     
        """Count pages in a PCL5 document.
         
           Should also work for PCL3 and PCL4 documents.
           
           Algorithm from pclcount
           (c) 2003, by Eduardo Gielamo Oliveira & Rodolfo Broco Manin 
           published under the terms of the GNU General Public Licence v2.
          
           Backported from C to Python by Jerome Alet, then enhanced
           with more PCL tags detected. I think all the necessary PCL tags
           are recognized to correctly handle PCL5 files wrt their number
           of pages. The documentation used for this was :
         
           HP PCL/PJL Reference Set
           PCL5 Printer Language Technical Quick Reference Guide
           http://h20000.www2.hp.com/bc/docs/support/SupportManual/bpl13205/bpl13205.pdf 
        """
        infileno = self.infile.fileno()
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        self.pages = {}
        self.pagecount = 0
        self.resets = 0
        self.backsides = []
        self.copies = []
        self.mediasourcesvalues = []
        self.mediasizesvalues = []
        self.orientationsvalues = []
        self.mediatypesvalues = []
        self.linesperpagevalues = []
        self.linesperpage = None
        self.startgfx = []
        self.endgfx = []
        self.hpgl2 = False
        self.imagerunnermarker1 = chr(0xcd) + chr(0xca) # Markers for Canon ImageRunner printers
        self.imagerunnermarker2 = chr(0x10) + chr(0x02)
        self.isimagerunner = (minfile[:2] == self.imagerunnermarker1)
        
        tags = [ lambda : None] * 256
        tags[ord(LINEFEED)] = self.newLine
        tags[ord(FORMFEED)] = self.endPage
        tags[ord(ESCAPE)] = self.escape
        tags[ord(ASCIILIMIT)] = self.skipByte
        tags[ord(self.imagerunnermarker1[0])] = self.handleImageRunner
        
        self.esctags = [ lambda : None ] * 256
        self.esctags[ord('%')] = self.escPercent
        self.esctags[ord('*')] = self.escStar
        self.esctags[ord('&')] = self.escAmp
        self.esctags[ord('(')] = self.escLeftPar
        self.esctags[ord(')')] = self.escRightPar
        self.esctags[ord('E')] = self.escE
        
        self.escamptags = [lambda : None ] * 256
        self.escamptags[ord('a')] = self.escAmpa
        self.escamptags[ord('l')] = self.escAmpl
        self.escamptags[ord('p')] = self.escAmpp
        self.escamptags[ord('b')] = self.escSkipSomethingW
        self.escamptags[ord('n')] = self.escSkipSomethingW
        self.escamptags[ord('u')] = self.escStaroptAmpu
        
        self.escstartags = [ lambda : None ] * 256
        self.escstartags[ord('b')] = self.escStarb
        self.escstartags[ord('r')] = self.escStarr
        self.escstartags[ord('o')] = self.escStaroptAmpu
        self.escstartags[ord('p')] = self.escStaroptAmpu
        self.escstartags[ord('t')] = self.escStaroptAmpu
        self.escstartags[ord('c')] = self.escSkipSomethingW
        self.escstartags[ord('g')] = self.escSkipSomethingW
        self.escstartags[ord('i')] = self.escSkipSomethingW
        self.escstartags[ord('l')] = self.escSkipSomethingW
        self.escstartags[ord('m')] = self.escSkipSomethingW
        self.escstartags[ord('v')] = self.escSkipSomethingW
        
        self.escleftpartags = [ lambda : None ] * 256
        self.escleftpartags[ord('s')] = self.escSkipSomethingW
        self.escleftpartags[ord('f')] = self.escSkipSomethingW
        
        self.escrightpartags = [ lambda : None ] * 256
        self.escrightpartags[ord('s')] = self.escSkipSomethingW
        
        self.pos = 0
        try :
            try :
                while 1 :
                    tags[self.readByte()]()
            except IndexError : # EOF ?            
                pass
        finally :
            self.minfile.close()
        
        self.logdebug("Pagecount : \t\t\t%i" % self.pagecount)
        self.logdebug("Resets : \t\t\t%i" % self.resets)
        self.logdebug("Copies : \t\t\t%s" % self.copies)
        self.logdebug("NbCopiesMarks : \t\t%i" % len(self.copies))
        self.logdebug("MediaTypes : \t\t\t%s" % self.mediatypesvalues)
        self.logdebug("NbMediaTypes : \t\t\t%i" % len(self.mediatypesvalues))
        self.logdebug("MediaSizes : \t\t\t%s" % self.mediasizesvalues)
        self.logdebug("NbMediaSizes : \t\t\t%i" % len(self.mediasizesvalues))
        self.logdebug("MediaSources : \t\t\t%s" % self.mediasourcesvalues)
        nbmediasourcesdefault = len([m for m in self.mediasourcesvalues if m == 'Default'])
        nbmediasourcesnotdefault = len(self.mediasourcesvalues) - nbmediasourcesdefault
        self.logdebug("MediaSourcesDefault : \t\t%i" % nbmediasourcesdefault)
        self.logdebug("MediaSourcesNOTDefault : \t%i" % nbmediasourcesnotdefault)
        self.logdebug("Orientations : \t\t\t%s" % self.orientationsvalues)
        nborientations = len(self.orientationsvalues)
        self.logdebug("NbOrientations : \t\t\t%i" % nborientations)
        self.logdebug("StartGfx : \t\t\t%s" % len(self.startgfx))
        self.logdebug("EndGfx : \t\t\t%s" % len(self.endgfx))
        self.logdebug("BackSides : \t\t\t%s" % self.backsides)
        self.logdebug("NbBackSides : \t\t\t%i" % len(self.backsides))
        self.logdebug("IsImageRunner : \t\t\t%s" % self.isimagerunner)
        
        if self.isimagerunner :
            self.logdebug("Adjusting PageCount : +1")
            self.pagecount += 1      # ImageRunner adjustment
        elif self.linesperpage is not None :    
            self.logdebug("Adjusting PageCount : +1")
            self.pagecount += 1      # Adjusts for incomplete last page
        elif len(self.startgfx) == len(self.endgfx) == 0 :
            if self.resets % 2 :
                if nborientations == self.pagecount + 1 :
                    self.logdebug("Adjusting PageCount : +1")
                    self.pagecount += 1
                elif (self.pagecount > 1) \
                     and (nborientations == self.pagecount - 1) :
                    self.logdebug("Adjusting PageCount : -1")
                    self.pagecount -= 1
        elif (self.pagecount > 1) \
             and (self.resets == 2) \
             and (not nbmediasourcesdefault) \
             and (nbmediasourcesnotdefault == 1) :
            self.logdebug("Adjusting PageCount : -1")
            self.pagecount -= 1
                    
        self.pagecount = self.pagecount or nbmediasourcesdefault
        
        if not self.pagecount :
            if self.resets == len(self.startgfx) :
                self.pagecount = self.resets 
        
        defaultpjlcopies = 1    
        defaultduplexmode = "Simplex"
        defaultpapersize = ""
        oldpjlcopies = -1
        oldduplexmode = ""
        oldpapersize = ""
        for pnum in range(self.pagecount) :
            # if no number of copies defined, take the preceding one else the one set before any page else 1.
            page = self.pages.get(pnum, self.pages.get(pnum - 1, self.pages.get(0, { "copies" : 1, "mediasource" : "Main", "mediasize" : "Default", "mediatype" : "Plain", "orientation" : "Portrait", "escaped" : "", "duplex": 0})))
            pjlstuff = page["escaped"]
            if pjlstuff :
                pjlparser = pjl.PJLParser(pjlstuff)
                nbdefaultcopies = int(pjlparser.default_variables.get("COPIES", -1))
                nbcopies = int(pjlparser.environment_variables.get("COPIES", -1))
                nbdefaultqty = int(pjlparser.default_variables.get("QTY", -1))
                nbqty = int(pjlparser.environment_variables.get("QTY", -1))
                if nbdefaultcopies > -1 :
                    defaultpjlcopies = nbdefaultcopies
                if nbdefaultqty > -1 :
                    defaultpjlcopies = nbdefaultqty
                if nbcopies > -1 :
                    pjlcopies = nbcopies
                elif nbqty > -1 :
                    pjlcopies = nbqty
                else :
                    if oldpjlcopies == -1 :    
                        pjlcopies = defaultpjlcopies
                    else :    
                        pjlcopies = oldpjlcopies    
                if page["duplex"] :        
                    duplexmode = "Duplex"
                else :    
                    defaultdm = pjlparser.default_variables.get("DUPLEX", "")
                    if defaultdm :
                        if defaultdm.upper() == "ON" :
                            defaultduplexmode = "Duplex"
                        else :    
                            defaultduplexmode = "Simplex"
                    envdm = pjlparser.environment_variables.get("DUPLEX", "")
                    if envdm :
                        if envdm.upper() == "ON" :
                            duplexmode = "Duplex"
                        else :    
                            duplexmode = "Simplex"
                    else :        
                        duplexmode = oldduplexmode or defaultduplexmode
                defaultps = pjlparser.default_variables.get("PAPER", "")
                if defaultps :
                    defaultpapersize = defaultps
                envps = pjlparser.environment_variables.get("PAPER", "")
                if envps :
                    papersize = envps
                else :    
                    if not oldpapersize :
                        papersize = defaultpapersize
                    else :    
                        papersize = oldpapersize
            else :        
                if oldpjlcopies == -1 :
                    pjlcopies = defaultpjlcopies
                else :    
                    pjlcopies = oldpjlcopies
                
                duplexmode = (page["duplex"] and "Duplex") or oldduplexmode or defaultduplexmode
                if not oldpapersize :    
                    papersize = defaultpapersize
                else :    
                    papersize = oldpapersize
                papersize = oldpapersize or page["mediasize"]
            if page["mediasize"] != "Default" :
                papersize = page["mediasize"]
            if not duplexmode :    
                duplexmode = oldduplexmode or defaultduplexmode
            oldpjlcopies = pjlcopies    
            oldduplexmode = duplexmode
            oldpapersize = papersize
            copies = max(pjlcopies, page["copies"]) # Was : pjlcopies * page["copies"]
            self.pagecount += (copies - 1)
            self.logdebug("%s*%s*%s*%s*%s*%s*BW" % (copies, \
                                              page["mediatype"], \
                                              papersize, \
                                              page["orientation"], \
                                              page["mediasource"], \
                                              duplexmode))
        
        return self.pagecount
