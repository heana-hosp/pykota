#! /usr/bin/python3
# -*- coding: ISO-8859-15 -*-

# PyKota Print Quota Reports generator
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
# $Id: printquota.cgi 3133 2007-01-17 22:19:42Z jerome $
#
#

import sys
import os
import cgi
import urllib

from datetime import datetime

from pykota import version
from pykota.tool import PyKotaTool, PyKotaToolError
from pykota.reporter import PyKotaReporterError, openReporter
from pykota.cgifuncs import getLanguagePreference, getCharsetPreference

header = """Content-type: text/html;charset=%s

<html>
  <head>
    <title>%s</title>
    <link rel="stylesheet" type="text/css" href="/pykota.css" />
  </head>
  <body>
    <!-- %s %s -->
    <p>
      <form action="printquota.cgi" method="POST">
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


class PyKotaReportGUI(PyKotaTool):
    """PyKota Administrative GUI"""

    def guiDisplay(self):
        """Displays the administrative interface."""
        global header, footer
        print(header % (self.charset, "PyKota Reports",
                        self.language, self.charset,
                        self.config.get_logo_link(),
                        self.config.get_logo_url(), version.__version__,
                        self.config.get_logo_link(),
                        version.__version__, "PyKota Reports",
                        "Report"))
        print(self.body)
        print(footer % ("Report", version.__doc__, version.__years__, version.__author__, version.__gplblurb__))

    def error(self, message):
        """Adds an error message to the GUI's body."""
        if message:
            self.body = f'<p><font color="red">{message}</font></p>\n{self.body}'

    def htmlListPrinters(self, selected=[], mask="*"):
        """Displays the printers multiple selection list."""
        printers = self.storage.getMatchingPrinters(mask)
        selectednames = [p.Name for p in selected]
        message = '<table><tr><td valign="top">{} :</td><td valign="top"><select name="printers" multiple="multiple">'.format("Printer")
        for printer in printers:
            if printer.Name in selectednames:
                message += f'<option value="{printer.Name}" selected="selected">{printer.Name} ({printer.Description})</option>'
            else:
                message += f'<option value="{printer.Name}">{printer.Name} ({printer.Description})</option>'
        message += '</select></td></tr></table>'
        return message

    def htmlUGNamesInput(self, value="*"):
        """Input field for user/group names wildcard."""
        return "User / Group names mask" + (
            f' : <input type="text" name="ugmask" size="20" value="{value or "*"}" /> <em>e.g. <strong>jo*</strong></em>')

    def htmlGroupsCheckbox(self, isgroup=0):
        """Groups checkbox."""
        if isgroup:
            return "Groups report" + ' : <input type="checkbox" checked="checked" name="isgroup" />'
        else:
            return "Groups report" + ' : <input type="checkbox" name="isgroup" />'

    def guiAction(self):
        """Main function"""
        printers = ugmask = isgroup = None
        remuser = os.environ.get("REMOTE_USER", "root")
        # special hack to accomodate mod_auth_ldap Apache module
        try:
            remuser = remuser.split("=")[1].split(",")[0]
        except IndexError:
            pass
        self.body = f"<p>{'Please click on the above button'}</p>\n"
        if self.form.has_key("report"):
            if self.form.has_key("printers"):
                printersfield = self.form["printers"]
                if type(printersfield) != type([]):
                    printersfield = [printersfield]
                printers = [self.storage.getPrinter(p.value) for p in printersfield]
            else:
                printers = self.storage.getMatchingPrinters("*")
            if remuser == "root":
                if self.form.has_key("ugmask"):
                    ugmask = self.form["ugmask"].value
                else:
                    ugmask = "*"
            else:
                if self.form.has_key("isgroup"):
                    user = self.storage.getUser(remuser)
                    if user.Exists:
                        ugmask = " ".join([g.Name for g in self.storage.getUserGroups(user)])
                    else:
                        ugmask = remuser  # result will probably be empty, we don't care
                else:
                    ugmask = remuser
            if self.form.has_key("isgroup"):
                isgroup = 1
            else:
                isgroup = 0
        self.body += self.htmlListPrinters(printers or [])
        self.body += "<br />"
        self.body += self.htmlUGNamesInput(ugmask)
        self.body += "<br />"
        self.body += self.htmlGroupsCheckbox(isgroup)
        try:
            if not self.form.has_key("history"):
                if printers and ugmask:
                    self.reportingtool = openReporter(admin, "html", printers, ugmask.split(), isgroup)
                    self.body += f"{self.reportingtool.generate_report()}"
            else:
                if remuser != "root":
                    username = remuser
                elif self.form.has_key("username"):
                    username = self.form["username"].value
                else:
                    username = None
                if username is not None:
                    user = self.storage.getUser(username)
                else:
                    user = None
                if self.form.has_key("printername"):
                    printer = self.storage.getPrinter(self.form["printername"].value)
                else:
                    printer = None
                if self.form.has_key("datelimit"):
                    datelimit = self.form["datelimit"].value
                else:
                    datelimit = None
                if self.form.has_key("hostname"):
                    hostname = self.form["hostname"].value
                else:
                    hostname = None
                if self.form.has_key("billingcode"):
                    billingcode = self.form["billingcode"].value
                else:
                    billingcode = None
                self.report = [f"<h2>{'History'}</h2>"]
                history = self.storage.retrieveHistory(user=user, printer=printer, hostname=hostname,
                                                       billingcode=billingcode, end=datelimit)
                if not history:
                    self.report.append(f"<h3>{'Empty'}</h3>")
                else:
                    self.report.append('<table class="pykotatable" border="1">')
                    headers = ["Date", "Action", "User", "Printer",
                               "Hostname", "JobId", "Number of pages",
                               "Cost", "Copies", "Number of bytes",
                               "Printer's internal counter", "Title", "Filename",
                               "Options", "MD5Sum", "Billing code",
                               "Precomputed number of pages", "Precomputed cost",
                               "Pages details" + " " + "(not supported yet)"]
                    self.report.append(
                        f'<tr class="pykotacolsheader">{"".join(["<th>%s</th>" % h for h in headers])}</tr>')
                    oddeven = 0
                    for job in history:
                        oddeven += 1
                        if job.JobAction == "ALLOW":
                            if oddeven % 2:
                                oddevenclass = "odd"
                            else:
                                oddevenclass = "even"
                        else:
                            oddevenclass = (job.JobAction or "UNKNOWN").lower()
                        username_url = f'<a href="{os.environ.get("SCRIPT_NAME", "")}?{urllib.urlencode({"history": 1, "username": job.UserName})}">{job.UserName}</a>'
                        printername_url = '<a href="{}?{}">{}</a>'.format(os.environ.get("SCRIPT_NAME", ""),
                                                                          urllib.urlencode({"history": 1,
                                                                                            "printername": job.PrinterName}),
                                                                          job.PrinterName)
                        if job.JobHostName:
                            hostname_url = '<a href="{}?{}">{}</a>'.format(os.environ.get("SCRIPT_NAME", ""),
                                                                           urllib.urlencode(
                                                                               {"history": 1,
                                                                                "hostname": job.JobHostName}),
                                                                           job.JobHostName)
                        else:
                            hostname_url = None
                        if job.JobBillingCode:
                            billingcode_url = '<a href="{}?{}">{}</a>'.format(os.environ.get("SCRIPT_NAME", ""),
                                                                              urllib.urlencode({"history": 1,
                                                                                                "billingcode": job.JobBillingCode}),
                                                                              job.JobBillingCode)
                        else:
                            billingcode_url = None
                        curdate = datetime.fromisoformat(str(job.JobDate)[:19])
                        self.report.append('<tr class="{}">{}</tr>' \
                                           .format(oddevenclass,
                                                   "".join([f"<td>{h or '&nbsp;'}</td>"
                                                            for h in (str(curdate)[:19],
                                                                      job.JobAction,
                                                                      username_url,
                                                                      printername_url,
                                                                      hostname_url,
                                                                      job.JobId,
                                                                      job.JobSize,
                                                                      job.JobPrice,
                                                                      job.JobCopies,
                                                                      job.JobSizeBytes,
                                                                      job.PrinterPageCounter,
                                                                      job.JobTitle,
                                                                      job.JobFileName,
                                                                      job.JobOptions,
                                                                      job.JobMD5Sum,
                                                                      billingcode_url,
                                                                      job.PrecomputedJobSize,
                                                                      job.PrecomputedJobPrice,
                                                                      job.JobPages)])))
                    self.report.append('</table>')
                    dico = {"history": 1,
                            "datelimit": f"{curdate.year:04d}-{curdate.month:02d}-{curdate.day:02d} {curdate.hour:02d}:{curdate.minute:02d}:{curdate.second:02d}",
                            }
                    if user and user.Exists:
                        dico.update({"username": user.Name})
                    if printer and printer.Exists:
                        dico.update({"printername": printer.Name})
                    if hostname:
                        dico.update({"hostname": hostname})
                    prevurl = f"{os.environ.get('SCRIPT_NAME', '')}?{urllib.urlencode(dico)}"
                    self.report.append(f'<a href="{prevurl}">{"Previous page"}</a>')
                self.body = "\n".join(self.report)
        except:
            self.body += '<p><font color="red">{}</font></p>'.format(self.crashed("CGI Error").replace("\n", "<br />"))


if __name__ == "__main__":
    admin = PyKotaReportGUI(lang=getLanguagePreference(), charset=getCharsetPreference())
    admin.deferredInit()
    admin.form = cgi.FieldStorage()
    admin.guiAction()
    admin.guiDisplay()
    try:
        admin.storage.close()
    except (TypeError, NameError, AttributeError):
        pass

    sys.exit(0)
