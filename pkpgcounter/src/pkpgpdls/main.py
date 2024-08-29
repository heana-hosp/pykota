import sys
from io import open

import PyPDF2 as PyPDF2

import analyzer

__doc__ = """pkpgcounter v%(__version__)s (c) %(__years__)s %(__author__)s

pkpgcounter is a generic Page Description Language parser.

pkpgcounter parses any number of input files and/or its standard input
and outputs the number of pages needed to print these documents.

pkpgcounter can also compute the percent of ink coverage in different
colorspaces for several file formats.

pkpgcounter currently recognizes the following document formats :

    * PostScript (both DSC compliant and binary)
    * PDF
    * PCLXL (aka PCL6)
    * PCL3/4/5
    * DVI
    * OpenDocument (ISO/IEC DIS 26300)
    * Microsoft Word (c) (tm) (r) (etc...)
    * Plain text
    * TIFF
    * Several other image formats
    * ESC/P2
    * Zenographics ZjStream
    * Samsung QPDL (aka SPL2)
    * Samsung SPL1
    * ESC/PageS03
    * Brother HBP
    * Hewlett-Packard LIDIL (hpijs)
    * Structured Fax
    * Canon BJ/BJC
    * ASCII PNM (Netpbm)

The ten latter ones, as well as some TIFF documents, are currently
only supported in page counting mode.

command line usage :

  pkpgcounter [options] [files]

options :

  -v | --version        Prints pkpgcounter's version number then exits.
  -h | --help           Prints this message then exits.

  -d | --debug          Activate debug mode.

  -cCOLORSPACE, --colorspace=COLORSPACE
                        Activate the computation of ink usage, and defines the
                        colorspace to use. Supported values are 'BW' (Black),
                        'RGB', 'CMYK', 'CMY', and 'GC' (Grayscale vs Color).
                        'GC' is useful if you only need to differentiate
                        grayscale pages from coloured pages but don't care
                        about ink usage per se.

  -rRESOLUTION, --resolution=RESOLUTION
                        The resolution in DPI to use when checking ink usage.
                        Lower resolution is faster but less accurate. Default
                        is 72 dpi.

examples :

  $ pkpgcounter file1.ps file2.escp2 file3.pclxl <file4.pcl345

  Will launch pkpgcounter and will output the total number of pages
  needed to print all the documents specified.

  $ pkpgcounter --colorspace bw --resolution 150 file1.ps

  Will output the percent of black ink needed on each page of
  the file1.ps file rendered at 150 dpi.

%(__gplblurb__)s

Please e-mail bugs to: %(__authoremail__)s"""

if __name__ == "__main__":
    if (len(sys.argv) >= 2) and (sys.argv[1] in ("-h", "--help")):
        sys.stdout.write("%s\n" % (__doc__ % globals()))
    else :
        analyzer.main()