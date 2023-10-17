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
# $Id: inkcoverage.py 346 2007-11-28 17:28:30Z jerome $
#

"""This modules implements the computation of ink coverage in different colorspaces."""

import sys

import pdlparser

try :
    from PIL import Image
except ImportError :    
    sys.stderr.write("ERROR: You MUST install the Python Imaging Library (python-imaging) for pkpgcounter to work.\n")
    raise pdlparser.PDLParserError, "The Python Imaging Library is missing."

def getPercent(img, nbpix) :
    """Extracts the percents per color component from a picture.
      
       Faster without Psyco on my own machine.
    """
    result = {}     
    bands = img.split()
    for (i, bandname) in enumerate(img.getbands()) :
        result[bandname] = 100.0 * (reduce(lambda current, next: current + (next[1] * next[0]), enumerate(bands[i].histogram()), 0) / 255.0) / nbpix
    return result    
    
def getPercentCMYK(img, nbpix) :
    """Extracts the percents of Cyan, Magenta, Yellow, and Black from a picture.
     
       PIL doesn't produce useable CMYK for our algorithm, so we use the algorithm from PrintBill.
       Psyco speeds this function up by around 2.5 times on my computer.
    """
    if img.mode != "RGB" :
        img = img.convert("RGB")
    cyan = magenta = yellow = black = 0    
    for (r, g, b) in img.getdata() :
        if r == g == b :
            black += 255 - r
        else :    
            cyan += 255 - r
            magenta += 255 - g
            yellow += 255 - b
    return { "C" : 100.0 * (cyan / 255.0) / nbpix,
             "M" : 100.0 * (magenta / 255.0) / nbpix,
             "Y" : 100.0 * (yellow / 255.0) / nbpix,
             "K" : 100.0 * (black / 255.0) / nbpix,
           }
        
def getPercentGC(img, nbpix) :        
    """Determines if a page is in grayscale or colour mode."""
    if img.mode != "RGB" :
        img = img.convert("RGB")
    gray = 0
    for (r, g, b) in img.getdata() :
        if not (r == g == b) :
            # optimize : if a single pixel is no gray the whole page is colored.
            return { "G" : 0.0, "C" : 100.0 }
    return { "G" : 100.0, "C" : 0.0 }
    
def getPercentBW(img, nbpix) :
    """Extracts the percents of Black from a picture, once converted to gray levels."""
    if img.mode != "L" :
        img = img.convert("L")
    return { "B" : 100.0 - getPercent(img, nbpix)["L"] }
    
def getPercentRGB(img, nbpix) :
    """Extracts the percents of Red, Green, Blue from a picture, once converted to RGB."""
    if img.mode != "RGB" :
        img = img.convert("RGB")
    return getPercent(img, nbpix)    
    
def getPercentCMY(img, nbpix) :
    """Extracts the percents of Cyan, Magenta, and Yellow from a picture once converted to RGB."""
    result = getPercentRGB(img, nbpix)
    return { "C" : 100.0 - result["R"],
             "M" : 100.0 - result["G"],
             "Y" : 100.0 - result["B"],
           }
    
def getInkCoverage(fname, colorspace) :
    """Returns a list of dictionnaries containing for each page, 
       for each color component, the percent of ink coverage on 
       that particular page.
    """
    result = []
    colorspace = colorspace.upper()
    computation = globals()["getPercent%s" % colorspace]
    if colorspace in ("CMYK", "GC") : # faster with psyco on my machine
        try :
            import psyco
        except ImportError :    
            pass
        else :    
            psyco.bind(getPercentCMYK)
    
    index = 0
    try :
        image = Image.open(fname)
    except (IOError, OverflowError), msg :   
        raise pdlparser.PDLParserError, "%s (%s)" % (msg, fname)
    else :    
        try :
            while True :
                nbpixels = image.size[0] * image.size[1]
                result.append(computation(image, nbpixels))
                index += 1              
                image.seek(index)
        except EOFError :        
            pass
        return (colorspace, result)

if __name__ == "__main__" :
    # NB : length of result gives number of pages !
    print getInkCoverage(sys.argv[1], "CMYK")
