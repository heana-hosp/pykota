# -*- coding: utf-8 -*-
#
# pkpgcounter: a generic Page Description Language parser
#
# (c) 2003-2019 Jerome Alet <alet@librelogiciel.com>
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
# $Id: inkcoverage.py 3578 2019-02-14 08:46:15Z jerome $
#

"""This modules implements the computation of ink coverage in different colorspaces."""

import sys
import functools
from pkpgpdls import pdlparser
try:
    from PIL import Image
except ImportError:
    sys.stderr.write("ERROR: You MUST install the Python Imaging Library "
                     "(either PIL or Pillow) for pkpgcounter to work.\n")
    raise pdlparser.PDLParserError("The Python Imaging Library is missing.")


def get_percent(img, nbpix):
    """Extracts the percents per color component from a picture."""
    result = {}
    bands = img.split()
    for (i, bandname) in enumerate(img.getbands()):
        result[bandname] = 100.0 * (functools.reduce(lambda current, next: current + (next[1] * next[0]),
                                                     enumerate(bands[i].histogram()), 0) / 255.0) / nbpix
    return result


def get_percent_cmyk(img, nbpix):
    """Extracts the percents of Cyan, Magenta, Yellow, and Black from a picture.

       PIL doesn't produce useable CMYK for our algorithm, so we use the algorithm from PrintBill.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    cyan = magenta = yellow = black = 0
    for (r, g, b) in img.getdata():
        pixblack = 255 - max(r, g, b)
        black += pixblack
        cyan += 255 - r - pixblack
        magenta += 255 - g - pixblack
        yellow += 255 - b - pixblack

    frac = 100.0 / nbpix
    return {"C": frac * (cyan / 255.0),
            "M": frac * (magenta / 255.0),
            "Y": frac * (yellow / 255.0),
            "K": frac * (black / 255.0), }


def get_percent_gc(img, nbpix):
    """Determines if a page is in grayscale or colour mode."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    gray = 0
    for (r, g, b) in img.getdata():
        if not (r == g == b):
            # optimize: if a single pixel is not gray the whole page is colored.
            return {"G": 0.0, "C": 100.0}
    return {"G": 100.0, "C": 0.0}


def get_percent_bw(img, nbpix):
    """Extracts the percents of Black from a picture, once converted to gray levels."""
    if img.mode != "L":
        img = img.convert("L")
    return {"B": 100.0 - get_percent(img, nbpix)["L"]}


def get_percent_rgb(img, nbpix):
    """Extracts the percents of Red, Green, Blue from a picture, once converted to RGB."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    return get_percent(img, nbpix)


def get_percent_cmy(img, nbpix):
    """Extracts the percents of Cyan, Magenta, and Yellow from a picture once converted to RGB."""
    result = get_percent_rgb(img, nbpix)
    return {"C": 100.0 - result["R"],
            "M": 100.0 - result["G"],
            "Y": 100.0 - result["B"], }


def get_ink_coverage(fname, colorspace):
    """Returns a list of dictionnaries containing for each page,
       for each color component, the percent of ink coverage on
       that particular page.
    """
    result = []
    colorspace = colorspace.upper()
    computation = globals()["getPercent%s" % colorspace]
    index = 0
    try:
        image = Image.open(fname)
    except (IOError, OverflowError) as msg:
        raise pdlparser.PDLParserError("{msg} ({fname})")
    else:
        try:
            while True:
                nbpixels = image.size[0] * image.size[1]
                result.append(computation(image, nbpixels))
                index += 1
                image.seek(index)
        except EOFError:
            pass
        return colorspace, result


if __name__ == "__main__":
    # NB: length of result gives number of pages !
    sys.stdout.write("%s\n" % get_ink_coverage(sys.argv[1], "CMYK"))
