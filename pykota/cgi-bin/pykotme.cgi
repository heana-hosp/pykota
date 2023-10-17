#! /usr/bin/python3
# -*- coding: ISO-8859-15 -*-

# PyKota Print Quotes generator
#
# PyKota - Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# $Id: pykotme.cgi 3133 2007-01-17 22:19:42Z jerome $
#
#

import sys
import os
import cgi
import urllib
# import cStringIO
from io import StringIO

from pykota import version
from pykota.tool import PyKotaTool, PyKotaToolError
from pykota.cgifuncs import getLanguagePreference, getCharsetPreference
from pkpgpdls import analyzer, pdlparser

header = """Content-type: text/html;charset=%s

<html>
  <head>
    <title>%s</title>
    <link rel="stylesheet" type="text/css" href="/pykota.css" />
  </head>
  <body>
    <!-- %s %s -->
    <p>
      <form action="pykotme.cgi" method="POST" enctype="multipart/form-data">
        <table>
          <tr>
            <td>
              <p>
                <a href="%s"><img src="%s?version=%s" alt="PyKota's Logo" /></a>
                <br />
                <a href="%s">PyKota v%s</a>
              </p>
            </td>
            <td colspan="2">
              <h1>%s</h1>
            </td>
          </tr>
          <tr>
            <td colspan="3" align="center">
              <input type="submit" name="report" value="%s" />
            </td>
          </tr>
        </table>"""

footer = """
        <table>
          <tr>
            <td colspan="3" align="center">
              <input type="submit" name="report" value="%s" />
            </td>
          </tr>
        </table>  
      </form>
    </p>
    <hr width="25%%" />
    <p>
      <font size="-2">
        <a href="http://www.pykota.com/">%s</a>
        &copy; %s %s 
        <br />
        <pre>
%s
        </pre>
      </font>
    </p>
  </body>
</html>"""


class PyKotMeGUI(PyKotaTool):
    """PyKota Quote's Generator GUI"""

    def guiDisplay(self):
        """Displays the administrative interface."""
        global header, footer
        print(header % (self.charset, "PyKota Quotes",
                        self.language, self.charset,
                        self.config.get_logo_link(),
                        self.config.get_logo_url(), version.__version__,
                        self.config.get_logo_link(),
                        version.__version__, "PyKota Quotes",
                        "Quote"))
        print(self.body)
        print(footer % ("Quote", version.__doc__, version.__years__, version.__author__, version.__gplblurb__))

    def error(self, message):
        """Adds an error message to the GUI's body."""
        if message:
            self.body = f'<p><font color="red">{message}</font></p>\n{self.body}'

    def htmlListPrinters(self, selected=[], mask="*"):
        """Displays the printers multiple selection list."""
        printers = self.storage.getMatchingPrinters(mask)
        selectednames = [p.Name for p in selected]
        message = f'<table><tr><td valign="top">{"Printer"} :</td><td valign="top"><select name="printers" multiple="multiple">'
        for printer in printers:
            if printer.Name in selectednames:
                message += f'<option value="{printer.Name}" selected="selected">{printer.Name} ({printer.Description})</option>'
            else:
                message += f'<option value="{printer.Name}">{printer.Name} ({printer.Description})</option>'
        message += '</select></td></tr></table>'
        return message

    def guiAction(self):
        """Main function"""
        printers = inputfile = None
        self.body = f"<p>{'Please click on the above button'}</p>\n"
        if self.form.has_key("report"):
            if self.form.has_key("printers"):
                printersfield = self.form["printers"]
                if type(printersfield) != type([]):
                    printersfield = [printersfield]
                printers = [self.storage.getPrinter(p.value) for p in printersfield]
            else:
                printers = self.storage.getMatchingPrinters("*")
            if self.form.has_key("inputfile"):
                inputfile = self.form["inputfile"].value

        if os.environ.get("REMOTE_USER") is not None:
            self.body += self.htmlListPrinters(printers or [])
            self.body += "<br />"
        self.body += "Filename" + " : "
        self.body += '<input type="file" size="64" name="inputfile" />'
        self.body += "<br />"
        if inputfile:
            try:
                parser = analyzer.PDLAnalyzer(StringIO(inputfile))
                jobsize = parser.get_job_size()
            except pdlparser.PDLParserError as msg:
                self.body += f'<p><font color="red">{msg}</font></p>'
                jobsize = 0  # unknown file format ?
            else:
                self.body += f"<p>{f'Job size : {jobsize:d} pages'}</p>"

            remuser = os.environ.get("REMOTE_USER")
            # special hack to accomodate mod_auth_ldap Apache module
            try:
                remuser = remuser.split("=")[1].split(",")[0]
            except:
                pass
            if not remuser:
                self.body += f"<p>{'The exact cost of a print job can only be determined for a particular user. Please retry while logged-in.'}</p>"
            else:
                try:
                    user = self.storage.getUser(remuser)
                    if user.Exists:
                        if user.LimitBy == "noprint":
                            self.body += f"<p>{'Your account settings forbid you to print at this time.'}</p>"
                        else:
                            for printer in printers:
                                upquota = self.storage.getUserPQuota(user, printer)
                                if upquota.Exists:
                                    if printer.MaxJobSize and (jobsize > printer.MaxJobSize):
                                        msg = f"You are not allowed to print so many pages on printer {printer.Name} at this time."
                                    else:
                                        cost = upquota.computeJobPrice(jobsize)
                                        msg = f"Cost on printer {printer.Name} : {cost:.2f}"
                                        if printer.PassThrough:
                                            msg = "{} ({})".format(msg,
                                                                   "won't be charged, printer is in passthrough mode")
                                        elif user.LimitBy == "nochange":
                                            msg = "{} ({})".format(msg, "won't be charged, your account is immutable")
                                    self.body += f"<p>{msg}</p>"
                except:
                    self.body += '<p><font color="red">{}</font></p>'.format(self.crashed("CGI Error").replace("\n",
                                                                                                               "<br />"))


if __name__ == "__main__":
    admin = PyKotMeGUI(lang=getLanguagePreference(), charset=getCharsetPreference())
    admin.deferredInit()
    admin.form = cgi.FieldStorage()
    admin.guiAction()
    admin.guiDisplay()
    try:
        admin.storage.close()
    except (TypeError, NameError, AttributeError):
        pass

    sys.exit(0)
