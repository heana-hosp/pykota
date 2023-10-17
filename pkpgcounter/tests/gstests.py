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
# $Id: gstests.py 363 2007-12-09 11:05:14Z jerome $
#
#

"""This script generates a testsuite from a PostScript input file and ghostscript."""

import sys
import os
import glob
import md5
import tempfile
import time

MEGABYTE = 1024 * 1024

class TestSuite :
    """A class for the testsuite."""
    def __init__(self, inputfile) :
        """Initializes the testsuite."""
        self.tmp = None
        self.inputfile = inputfile
        self.results = {}
        self.supportedpct = self.failedpct = self.unsupportedpct = None
        self.md5sum = self.computeChecksum()
        self.mastersize = None
        
    def __del__(self) :    
        """Remove temporary file, if any."""
        if self.tmp is not None :
            self.tmp.close()
            
    def computeChecksum(self) :    
        """Computes an MD5 checksum for the input file's content."""
        checksum = md5.new()
        istemp = False
        if self.inputfile == "-" :
            # Input is standard input, so we must use a temporary
            # file to be able to loop over all available devices.
            self.tmp = tempfile.NamedTemporaryFile(mode="w+b")
            self.inputfile = self.tmp.name
            infile = sys.stdin
            istemp = True
        else :    
            infile = open(self.inputfile, "rb")
            
        while True :
            data = infile.read(MEGABYTE)
            if not data :
                break
            if istemp :    
                self.tmp.write(data)
            checksum.update(data)
            
        if istemp :    
            self.tmp.flush()    
        else :
            infile.close()
            
        return checksum.hexdigest()    
        
    def getAvailableDevices(self) :
        """Returns a list of available GhostScript devices.
        
           The list is returned without any x11, bbox, nor ijs related device.
        """
        answerfd = os.popen('/bin/echo "devicenames ==" | gs -dBATCH -dQUIET -dNOPAUSE -dPARANOIDSAFER -sDEVICE=nullpage -', "r")
        answer = answerfd.readline().strip()
        if not answerfd.close() :
            if answer.startswith("[/") and answer.endswith("]") :
                devices = [ dev[1:] for dev in answer[1:-1].split() \
                                        if dev.startswith("/") \
                                           and (not dev.startswith("/x11")) \
                                           and (not dev == "/ijs") \
                                           and (not dev == "/nullpage") \
                                           and (not dev == "/bbox") ]
                devices.sort()                           
                return devices
        return []
            
    def getAvailableIJSPrintClasses(self) :
        """Returns a list of available IJS Print Classes.
        
           Currently the list is a static one and doesn't contain all the available print classes.
        """
        return [ "DJ3600", "DJ3320", "DJ9xx", "DJGenericVIP", "LJColor", 
                 "DJ850", "DJ890", "DJ9xxVIP", "DJ8xx", "DJ540", "DJ660",
                 "DJ6xx", "DJ350", "DJ6xxPhoto", "DJ630", "DJ8x5", "DJ4100",
                 "AP21xx", "AP2560", "AP2xxx", "PSP100", "PSP470", "Undefined",
                 "Postscript", "LJJetReady", "LJMono", "LJFastRaster",
                 "LJZjsMono", ]
            
    def batchGeneration(self, infilename, devices, root, command) :
        """Loops over a set of devices calling a particular command."""
        parts = root.split(".")
        if (len(parts) > 1) and (parts[-1] == "hpijs") :
            devprefix = parts[-1] + "/"
        else :
            devprefix = ""
        for device in devices :
            outfilename = "%(root)s.%(device)s" % locals()
            cmd = command % locals()
            if os.path.exists(outfilename) and os.stat(outfilename).st_size :
                sys.stdout.write("Skipping %(outfilename)s : already exists.\n" % locals())
            else :    
                sys.stdout.write("Generating %(outfilename)s " % locals())
                sys.stdout.flush()
                os.system(cmd)
                sys.stdout.write("\n")
                
            if not os.path.exists(outfilename) :
                sys.stderr.write("ERROR : During the generation of %(outfilename)s\n" % locals())
            elif not os.stat(outfilename).st_size :    
                sys.stderr.write("ERROR : Unsupported driver, impossible to generate %(outfilename)s\n" % locals())
                os.remove(outfilename)
            else :    
                self.results[outfilename] = { "command" : cmd,
                                              "device" : "%s" % (devprefix + device),
                                              "result" : None,
                                              "details" : None,
                                            }
                
    def genTestSuite(self) :
        """Generate the testsuite."""
        root = "testsuite.%s" % self.md5sum
        self.batchGeneration(self.inputfile, self.getAvailableDevices(), 
                                        root, 
                                        'gs -dQUIET -dBATCH -dNOPAUSE -dPARANOIDSAFER -sOutputFile="%(outfilename)s" -sDEVICE="%(device)s" "%(infilename)s"')
                                    
        self.batchGeneration(self.inputfile, self.getAvailableIJSPrintClasses(), 
                                        "%(root)s.hpijs" % locals(), 
                                        'gs -dBATCH -dQUIET -dPARANOIDSAFER -dNOPAUSE -sDEVICE=ijs -sIjsServer=hpijs -dIjsUseOutputFD -sDeviceManufacturer="HEWLETT-PACKARD" -sDeviceModel="%(device)s" -sOutputFile="%(outfilename)s" "%(infilename)s"')
                
    def runPipe(self, cmd) :            
        """Runs a command in a pipe, returns the command's output as a string."""
        answerfd = os.popen(cmd, "r")
        try :
            return answerfd.read().strip()
        finally :        
            answerfd.close()
        
    def computeSize(self, filename) :    
        """Computes the size in pages of a file in the testsuite."""
        answer = self.runPipe('pkpgcounter "%(filename)s" 2>/dev/null' % locals())
        try :
            return int(answer)
        except (ValueError, TypeError) :    
            return 0
        
    def runTests(self) :
        """Launches the page counting tests against the testsuite."""
        masterfilename = self.inputfile
        self.mastersize = mastersize = self.computeSize(masterfilename)
        if not mastersize :
            raise RuntimeError, "Unable to compute the size of the testsuite's master file %(masterfilename)s" % locals()
        else :    
            sys.stdout.write("Master file's contains %(mastersize)i pages.\n" % locals())
        testsuite = glob.glob("testsuite.*")
        testsuite.sort()
        nbtests = len(testsuite)
        for testfname in testsuite :
            parts = testfname.split(".")
            if len(parts) > 3 :
                devname = ".".join(parts[2:])
            else :    
                devname = parts[-1]
            result = self.results.setdefault(testfname, { "command" : "See above", 
                                                          "device" : devname, 
                                                          "result" : None, 
                                                          "details" : None })
            sys.stdout.write("Testing %(testfname)s ... " % locals())
            sys.stdout.flush()
            size = self.computeSize(testfname)
            if size != mastersize :
                if not size :
                    result["result"] = "UNSUPPORTED"
                    result["details"] = "Unsupported file format"
                else :    
                    result["result"] = "FAILED"
                    result["details"] = "Found %(size)i pages instead of %(mastersize)i\n" % locals()
            else :    
                result["result"] = "SUPPORTED"
                result["details"] = None
            sys.stdout.write("%s\n" % result["result"])    
        self.supportedpct = 100.0 * len([True for r in self.results.values() if r["result"] == "SUPPORTED"]) / nbtests
        self.failedpct = 100.0 * len([True for r in self.results.values() if r["result"] == "FAILED"]) / nbtests
        self.unsupportedpct = 100.0 * len([True for r in self.results.values() if r["result"] == "UNSUPPORTED"]) / nbtests
        
    def genHTMLReport(self, filename) :
        """Generates an HTML report."""
        reportdate = "%s (UTC)" % time.asctime(time.gmtime(time.time()))
        title = "pkpgcounter v%s report for testsuite %s generated on %s" \
                        % (self.runPipe("pkpgcounter --version"), \
                           self.md5sum, \
                           reportdate)
        out = open(filename, "w")
        out.write("<html><head><title>%s</title></head><body>\n" % title)
        out.write("<h3>%s</h3>\n" % title)
        out.write("<ul>\n")
        out.write("<li>Testsuite's MD5 checksum : <strong>%s</strong></li>\n" % self.md5sum)
        out.write("<li>Testsuite contains : <strong>%i pages</strong></li>\n" % self.mastersize)
        out.write("<li>Ghostscript used to generate testsuite : <strong>v%s</strong></li>\n" % self.runPipe("gs --version"))
        out.write("<li>Supported : <strong>%.2f%%</strong></li>\n" % self.supportedpct)
        out.write("<li>Failed : <strong>%.2f%%</strong></li>\n" % self.failedpct)
        out.write("<li>Unsupported : <strong>%.2f%%</strong></li>\n" % self.unsupportedpct)
        out.write("</ul>\n")
        out.write("<p><strong>Green</strong> means that pkpgcounter obtained the expected result.</p>\n")
        out.write("<p><strong>Orange</strong> means that pkpgcounter obtained an incorrect result.<em>IMPORTANT : if only 1 page is found, this is often due to image formats which don't support multiple pages anyway.</em></p>\n")
        out.write("<p><strong>Red</strong> means that pkpgcounter doesn't recognize the input file's format.</p>\n")
        out.write('<table border="1"><tr bgcolor="gold"><th width="15%">Device</th><th width="25%">Details</th><th width="60%">Command line</th></tr>\n')
        linecount = 0
        keys = self.results.keys()
        keys.sort()
        for key in keys :
            value = self.results[key]
            linecount += 1    
            if not (linecount % 2) :    
                linecolor = "#DEDEDE"
            else :    
                linecolor = "#FFFFFF"
            out.write('<tr bgcolor="%s">\n' % linecolor)    
            if value["result"] == "SUPPORTED" :
                color = "#00FF00"
            elif value["result"] == "UNSUPPORTED" :    
                color = "#FF0000"
            else :    
                color = "orange"
            out.write('<td bgcolor="%s"><strong>%s</strong></td>\n' % (color, value["device"]))
            out.write('<td>%s</td>\n' % (value["details"] or "&nbsp;"))
            out.write('<td><em>%s</em></td>\n' % value["command"])
            out.write("</tr>\n")
        out.write("</table></body></html>\n")
        out.close()
        
def main() :        
    """Main function."""
    try :
        if len(sys.argv) == 1 :
            sys.argv.append("-")
        if len(sys.argv) != 2 :
            sys.stderr.write("usage : %s [inputfile.ps]\n" % sys.argv[0])
            sys.exit(-1)
        else :    
            testsuite = TestSuite(sys.argv[1])
            testsuite.genTestSuite()
            testsuite.runTests()
            testsuite.genHTMLReport("%s.html" % testsuite.md5sum)
    except KeyboardInterrupt :        
        sys.stderr.write("Interrupted at user's request !\n")
        
if __name__ == "__main__" :
    sys.exit(main())
        
