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
# $Id: pjl.py 291 2007-09-19 12:20:25Z jerome $
#

"""This modules implements a really minimalist PJL/EJL parser."""

# NOTES : QTY= is the number of collated copies for a job.
# NOTES : COPIES= is the number of uncollated copies for each page of a job

import sys

class PJLParserError(Exception):
    """An exception for PJLParser related stuff."""
    def __init__(self, message = ""):
        self.message = message
        Exception.__init__(self, message)
    def __repr__(self):
        return self.message
    __str__ = __repr__
        
class PJLParser :
    """A parser for PJL documents.
    
       Information extracted for bpl11897.pdf which was
       downloaded from Hewlett-Packard's website.
    """
    JL = "PJL"
    def __init__(self, pjljob, debug=0) :
        """Initializes JL Parser."""
        self.debug = debug
        self.jlmarker = "@%s" % self.JL
        self.statements = pjljob.replace("\r\n", "\n").split("\n")
        self.default_variables = {}
        self.environment_variables = {}
        self.parsed = 0
        self.parse()
        
    def __str__(self) :    
        """Outputs our variables as a string of text."""
        if not self.parsed :
            return ""
        mybuffer = []
        if self.default_variables :
            mybuffer.append("Default variables :")
            for (k, v) in self.default_variables.items() :
                mybuffer.append("  %s : %s" % (k, v))
        if self.environment_variables :        
            mybuffer.append("Environment variables :")
            for (k, v) in self.environment_variables.items() :
                mybuffer.append("  %s : %s" % (k, v))
        return "\n".join(mybuffer)        
            
    def logdebug(self, message) :    
        """Logs a debug message if needed."""
        if self.debug :
            sys.stderr.write("%s\n" % message)
            
    def cleanvars(self) :        
        """Cleans the variables dictionnaries."""
        for dicname in ("default", "environment") :
            varsdic = getattr(self, "%s_variables" % dicname)
            for (k, v) in varsdic.items() :
                if len(v) == 1 :
                    varsdic[k] = v[0]
        
    def parse(self) :
        """Parses a JL job."""
        for i in range(len(self.statements)) :
            statement = self.statements[i]
            if statement.startswith(self.jlmarker) :
                parts = statement.split()
                nbparts = len(parts)
                if parts[0] == self.jlmarker :
                    # this is a valid JL statement, but we don't
                    # want to examine all of them...
                    if (nbparts > 2) \
                         and ((parts[1].upper() in ("SET", "DEFAULT")) \
                                  or ((self.jlmarker == "@EJL") and (parts[1].upper() == "JI"))) :
                        # this is what we are interested in !
                        try :    
                            (varname, value) = "".join(parts[2:]).split("=", 1) # TODO : parse multiple assignments on the same SET/JI statement
                        except :    
                            self.logdebug("Invalid JL SET statement [%s]" % repr(statement))
                        else :    
                            # all still looks fine...
                            if parts[1].upper() == "DEFAULT" :
                                varsdic = self.default_variables
                            else :    
                                varsdic = self.environment_variables 
                            variable = varsdic.setdefault(varname.upper(), [])
                            variable.append(value)
                    else :
                        self.logdebug("Ignored JL statement [%s]" % repr(statement))
                        self.logdebug(parts)
                else :
                    self.logdebug("Invalid JL statement [%s]" % repr(statement))
            else :
                self.logdebug("Invalid JL statement [%s]" % repr(statement))
        self.cleanvars()
        self.parsed = 1
        
class EJLParser(PJLParser) :
    """A parser for EJL (Epson Job Language) documents."""
    JL = "EJL"
        
def test() :        
    """Test function."""
    if (len(sys.argv) < 2) or ((not sys.stdin.isatty()) and ("-" not in sys.argv[1:])) :
        sys.argv.append("-")
    for arg in sys.argv[1:] :
        klass = PJLParser
        if arg == "-" :
            infile = sys.stdin
            mustclose = 0
        else :    
            if arg.endswith(".ejl") :
                klass = EJLParser
            infile = open(arg, "rb")
            mustclose = 1
        try :
            parser = klass(infile.read(), debug=1)
        except PJLParserError, msg :    
            sys.stderr.write("ERROR: %s\n" % msg)
            sys.stderr.flush()
        if mustclose :    
            infile.close()
        print str(parser)            
    
if __name__ == "__main__" :    
    test()
