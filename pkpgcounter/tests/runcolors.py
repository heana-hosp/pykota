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
# $Id: runcolors.py 282 2007-09-10 20:47:40Z jerome $
#
#

"""This document was created with the help of the ReportLab
ToolKit (tm) available as Free Software from :

        http://www.reportlab.org

It contains 10 pages, including this one.

Each page after this one is entirely filled with 100%
of a particular color, as described below :

Page  1 ====> This notice
Page  2 ====> Red
Page  3 ====> Green
Page  4 ====> Blue
Page  5 ====> Cyan
Page  6 ====> Magenta
Page  7 ====> Yellow
Page  8 ====> Black
Page  9 ====> White
Page 10 ====> The expected results.

This document helps to ensure that the computation of
ink coverage made by pkpgcounter works as expected.

To check by yourself :

  $ for cspace in BW RGB CMY CMYK ; do
        echo "Colorspace : $cspace" ;
        pkpgcounter --colorspace $cspace colors.pdf ;
        echo ;
    done    

Please report any problem to : alet@librelogiciel.com
"""

lastpage = """For each colorspace, the results for the last page will differ a bit from what is below.
The important values are the one for pages 2 to 9 included.

Colorspace : BW
B :   2.355336%
B :  70.196078%
B :  41.568627%
B :  88.627451%
B :  30.196078%
B :  58.823529%
B :  11.764706%
B : 100.000000%
B :   0.000000%
B :   3.500669%

Colorspace : RGB
R :  97.644664%      G :  97.644664%      B :  97.644664%
R : 100.000000%      G :   0.000000%      B :   0.000000%
R :   0.000000%      G : 100.000000%      B :   0.000000%
R :   0.000000%      G :   0.000000%      B : 100.000000%
R :   0.000000%      G : 100.000000%      B : 100.000000%
R : 100.000000%      G :   0.000000%      B : 100.000000%
R : 100.000000%      G : 100.000000%      B :   0.000000%
R :   0.000000%      G :   0.000000%      B :   0.000000%
R : 100.000000%      G : 100.000000%      B : 100.000000%
R :  96.499331%      G :  96.499331%      B :  96.499331%

Colorspace : CMY
C :   2.355336%      M :   2.355336%      Y :   2.355336%
C :   0.000000%      M : 100.000000%      Y : 100.000000%
C : 100.000000%      M :   0.000000%      Y : 100.000000%
C : 100.000000%      M : 100.000000%      Y :   0.000000%
C : 100.000000%      M :   0.000000%      Y :   0.000000%
C :   0.000000%      M : 100.000000%      Y :   0.000000%
C :   0.000000%      M :   0.000000%      Y : 100.000000%
C : 100.000000%      M : 100.000000%      Y : 100.000000%
C :   0.000000%      M :   0.000000%      Y :   0.000000%
C :   3.500669%      M :   3.500669%      Y :   3.500669%

Colorspace : CMYK
C :   0.000000%      M :   0.000000%      Y :   0.000000%      K :   2.355336%
C :   0.000000%      M : 100.000000%      Y : 100.000000%      K :   0.000000%
C : 100.000000%      M :   0.000000%      Y : 100.000000%      K :   0.000000%
C : 100.000000%      M : 100.000000%      Y :   0.000000%      K :   0.000000%
C : 100.000000%      M :   0.000000%      Y :   0.000000%      K :   0.000000%
C :   0.000000%      M : 100.000000%      Y :   0.000000%      K :   0.000000%
C :   0.000000%      M :   0.000000%      Y : 100.000000%      K :   0.000000%
C :   0.000000%      M :   0.000000%      Y :   0.000000%      K : 100.000000%
C :   0.000000%      M :   0.000000%      Y :   0.000000%      K :   0.000000%
C :   0.000000%      M :   0.000000%      Y :   0.000000%      K :   3.500669%
"""

import sys
try :
    from reportlab.lib import colors
    from reportlab.lib import pagesizes
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
except ImportError :    
    sys.stderr.write("Please download and install ReportLab\n\tfrom http://www.reportlab.org\n")
    sys.exit(-1)

if __name__ == "__main__" :
    canv = canvas.Canvas("colors.pdf", pagesize=pagesizes.A4)
    (width, height) = pagesizes.A4
    xbase = 2*cm
    ybase = height - 2*cm
    
    # First we output the explanations on the first page.
    canv.setFont("Courier", 14)
    for line in __doc__.split("\n") :
        canv.drawString(xbase, ybase, line)
        ybase -= 18
    canv.showPage()
    
    # Then we output each page
    for color in (colors.Color(1, 0, 0),        # Red
                  colors.Color(0, 1, 0),        # Green
                  colors.Color(0, 0, 1)) :      # Blue
        canv.setStrokeColorRGB(*color.rgb())          
        canv.setFillColorRGB(*color.rgb())          
        canv.rect(0, 0, width, height, fill=1)
        canv.showPage()
        
    for color in (colors.CMYKColor(1, 0, 0, 0), # Cyan
                  colors.CMYKColor(0, 1, 0, 0), # Magenta
                  colors.CMYKColor(0, 0, 1, 0), # Yellow
                  colors.CMYKColor(0, 0, 0, 1), # Black
                  colors.CMYKColor(0, 0, 0, 0)) : # White
        canv.setStrokeColorCMYK(*color.cmyk())          
        canv.setFillColorCMYK(*color.cmyk())          
        canv.rect(0, 0, width, height, fill=1)
        canv.showPage()
        
    # Finally outputs the expected results.
    canv.setFont("Helvetica-Bold", 16)
    canv.drawCentredString(width/2.0, height-1.5*cm, "Expected Results :")
    ybase = height - 3*cm
    canv.setFont("Courier", 10)
    for line in lastpage.split("\n") :
        canv.drawString(xbase, ybase, line)
        ybase -= 14
    canv.showPage()
        
    canv.save()        
