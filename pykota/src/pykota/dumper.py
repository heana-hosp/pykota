# PyKota Print Quota Data Dumper
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
# $Id: dumper.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module handles all the data dumping facilities for PyKota."""

import sys
import os
import pwd
from xml.sax import saxutils
import datetime

try:
    import jaxml
except ImportError:
    sys.stderr.write("The jaxml Python module is not installed. XML output is disabled.\n")
    sys.stderr.write(
        "Download jaxml from http://www.librelogiciel.com/software/ or from your Debian archive of choice\n")
    hasJAXML = 0
else:
    hasJAXML = 1

from pykota import version
from pykota.tool import PyKotaTool, PyKotaToolError, PyKotaCommandLineError, N_


class DumPyKota(PyKotaTool):
    """A class for dumpykota."""
    validdatatypes = {"history": N_("History"),
                      "users": N_("Users"),
                      "groups": N_("Groups"),
                      "printers": N_("Printers"),
                      "upquotas": N_("Users Print Quotas"),
                      "gpquotas": N_("Users Groups Print Quotas"),
                      "payments": N_("History of Payments"),
                      "pmembers": N_("Printers Groups Membership"),
                      "umembers": N_("Users Groups Membership"),
                      "billingcodes": N_("Billing Codes"),
                      "all": N_("All"),
                      }
    validformats = {"csv": N_("Comma Separated Values"),
                    "ssv": N_("Semicolon Separated Values"),
                    "tsv": N_("Tabulation Separated Values"),
                    "xml": N_("eXtensible Markup Language"),
                    "cups": N_("CUPS' page_log"),
                    }
    validfilterkeys = ["username",
                       "groupname",
                       "printername",
                       "pgroupname",
                       "hostname",
                       "billingcode",
                       "jobid",
                       "start",
                       "end",
                       ]

    def main(self, arguments, options, restricted=1):
        """Print Quota Data Dumper."""
        if restricted and not self.config.isAdmin:
            raise PyKotaCommandLineError(f"{pwd.getpwuid(os.geteuid())[0]} : You're not allowed to use this command.")

        datatype = options["data"]
        if datatype not in self.validdatatypes.keys():
            raise PyKotaCommandLineError(f"Invalid modifier [{datatype}] for --data command line option, see help.")

        orderby = options["orderby"]
        if orderby:
            fields = [f.strip() for f in orderby.split(",")]
            orderby = []
            for field in fields:
                if field.isalpha() \
                        or ((field[0] in ("+", "-")) and field[1:].isalpha()):
                    orderby.append(field)
                else:
                    self.printInfo("Skipping invalid ordering statement '{field}'".format(**locals()), "error")
        else:
            orderby = []

        extractonly = {}
        if datatype == "all":
            if (options["format"] != "xml") or options["sum"] or arguments:
                self.printInfo("Dumping all PyKota's datas forces format to XML, and disables --sum and filters.",
                               "warn")
            options["format"] = "xml"
            options["sum"] = None
        else:
            for filterexp in arguments:
                if filterexp.strip():
                    try:
                        (filterkey, filtervalue) = [part.strip() for part in filterexp.split("=")]
                        filterkey = filterkey.lower()
                        if filterkey not in self.validfilterkeys:
                            raise ValueError
                    except ValueError:
                        raise PyKotaCommandLineError(f"Invalid filter value [{filterexp}], see help.")
                    else:
                        extractonly.update({filterkey: filtervalue})

        format = options["format"]
        if (format not in self.validformats.keys()) or (
                (format == "cups") and ((datatype != "history") or options["sum"])):
            raise PyKotaCommandLineError(f"Invalid modifier [{format}] for --format command line option, see help.")

        if (format == "xml") and not hasJAXML:
            raise PyKotaToolError("XML output is disabled because the jaxml module is not available.")

        if datatype not in ("payments", "history"):
            if options["sum"]:
                raise PyKotaCommandLineError(f"Invalid data type [{datatype}] for --sum command line option, see help.")
            if extractonly.has_key("start") or extractonly.has_key("end"):
                self.printInfo("Invalid filter for the {datatype} data type.".format(**locals()), "warn")
                try:
                    del extractonly["start"]
                except KeyError:
                    pass
                try:
                    del extractonly["end"]
                except KeyError:
                    pass

        retcode = 0
        nbentries = 0
        mustclose = 0
        if options["output"].strip() == "-":
            self.outfile = sys.stdout
        else:
            self.outfile = open(options["output"], "w")
            mustclose = 1

        if datatype == "all":
            # NB : order does matter to allow easier or faster restore
            allentries = []
            datatypes = ["printers", "pmembers", "users", "groups",
                         "billingcodes", "umembers", "upquotas",
                         "gpquotas", "payments", "history"]
            neededdatatypes = datatypes[:]
            for datatype in datatypes:
                entries = getattr(self.storage, f"extract{datatype.title()}")(
                    extractonly)  # We don't care about ordering here
                if entries:
                    nbentries += len(entries)
                    allentries.append(entries)
                else:
                    neededdatatypes.remove(datatype)
            retcode = self.dump_xml(allentries, neededdatatypes)
        else:
            entries = getattr(self.storage, f"extract{datatype.title()}")(extractonly, orderby)
            if entries:
                nbentries = len(entries)
                retcode = getattr(self, f"dump{format.title()}")(
                    [self.summarize_datas(entries, datatype, extractonly, options["sum"])], [datatype])

        if mustclose:
            self.outfile.close()
            if not nbentries:
                os.remove(options["output"])

        return retcode

    def cmp(self, val1, val2):
        return (val1 > val2) - (val1 < val2)

    def summarize_datas(self, entries, datatype, extractonly, sum=0):
        """Transforms the datas into a summarized view (with totals).
        
           If sum is false, returns the entries unchanged.
        """
        if not sum:
            return entries
        else:
            headers = entries[0]
            nbheaders = len(headers)
            fieldnumber = {}
            fieldname = {}
            for i in range(nbheaders):
                fieldnumber[headers[i]] = i

            if datatype == "payments":
                totalize = [("amount", float)]
                keys = ["username"]
            else:  # elif datatype == "history"
                totalize = [("jobsize", int),
                            ("jobprice", float),
                            ("jobsizebytes", int),
                            ("precomputedjobsize", int),
                            ("precomputedjobprice", float),
                            ]
                keys = [k for k in ("username", "printername", "hostname", "billingcode") if k in extractonly.keys()]

            newentries = [headers]
            sortedentries = entries[1:]
            if keys:
                # If we have several keys, we can sort only on the first one, because they
                # will vary the same way.
                sortedentries.sort(lambda x, y, fnum=fieldnumber[keys[0]]: self.cmp(x[fnum], y[fnum]))
            totals = {}
            for (k, t) in totalize:
                totals[k] = {"convert": t, "value": 0.0}
            prevkeys = {}
            for k in keys:
                prevkeys[k] = sortedentries[0][fieldnumber[k]]
            for entry in sortedentries:
                curval = '-'.join([str(entry[fieldnumber[k]]) for k in keys])
                prevval = '-'.join([str(prevkeys[k]) for k in keys])
                if curval != prevval:
                    summary = ["*"] * nbheaders
                    for k in keys:
                        summary[fieldnumber[k]] = prevkeys[k]
                    for k in totals.keys():
                        summary[fieldnumber[k]] = totals[k]["convert"](totals[k]["value"])
                    newentries.append(summary)
                    for k in totals.keys():
                        totals[k]["value"] = totals[k]["convert"](entry[fieldnumber[k]])
                else:
                    for k in totals.keys():
                        totals[k]["value"] += totals[k]["convert"](entry[fieldnumber[k]] or 0.0)
                for k in keys:
                    prevkeys[k] = entry[fieldnumber[k]]
            summary = ["*"] * nbheaders
            for k in keys:
                summary[fieldnumber[k]] = prevkeys[k]
            for k in totals.keys():
                summary[fieldnumber[k]] = totals[k]["convert"](totals[k]["value"])
            newentries.append(summary)
            return newentries

    def dump_with_separator(self, separator, allentries):
        """Dumps datas with a separator."""
        for entries in allentries:
            for entry in entries:
                line = []
                for value in entry:
                    if type(value).__name__ in ("str", "NoneType"):
                        line.append('"%s"' % str(value).replace(separator, "\\%s" % separator).replace('"', '\\"'))
                    else:
                        line.append(str(value))
                try:
                    self.outfile.write(f"{separator.join(line)}\n")
                except IOError as msg:
                    sys.stderr.write(f"PyKota data dumper failed : I/O error : {msg}\n")
                    return -1
        return 0

    def dump_csv(self, allentries, dummy):
        """Dumps datas with a comma as the separator."""
        return self.dump_with_separator(",", allentries)

    def dump_ssv(self, allentries, dummy):
        """Dumps datas with a comma as the separator."""
        return self.dump_with_separator(";", allentries)

    def dump_tsv(self, allentries, dummy):
        """Dumps datas with a comma as the separator."""
        return self.dump_with_separator("\t", allentries)

    def dump_cups(self, allentries, dummy):
        """Dumps history datas as CUPS' page_log format."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        entries = allentries[0]
        fieldnames = entries[0]
        fields = {}
        for i in range(len(fieldnames)):
            fields[fieldnames[i]] = i
        sortindex = fields["jobdate"]
        entries = entries[1:]
        entries.sort(lambda m, n, si=sortindex: self.cmp(m[si], n[si]))
        for entry in entries:
            printername = entry[fields["printername"]]
            username = entry[fields["username"]]
            jobid = entry[fields["jobid"]]
            jobdate = datetime.datetime.fromisoformat(str(entry[fields["jobdate"]])[:19])
            gmtoffset = jobdate.gmtoffset()
            # jobdate = "%s %+03i00" % (jobdate.strftime("%d/%b/%Y:%H:%M:%S"), gmtoffset.hour)
            jobdate = f"{jobdate.day:02d}/{months[jobdate.month - 1]}/{jobdate.year:04d}:{jobdate.hour:02d}:{jobdate.minute:02d}:{jobdate.second:02d} {gmtoffset.hour:+03d}{gmtoffset.minute:02d}"
            jobsize = entry[fields["jobsize"]] or 0
            copies = entry[fields["copies"]] or 1
            hostname = entry[fields["hostname"]] or ""
            billingcode = entry[fields["billingcode"]] or "-"
            for pagenum in range(1, jobsize + 1):
                self.outfile.write("%s %s %s [%s] %s %s %s %s\n" % (
                printername, username, jobid, jobdate, pagenum, copies, billingcode, hostname))
        return 0

    def dump_xml(self, allentries, datatypes):
        """Dumps datas as XML."""
        x = jaxml.XML_document(encoding="UTF-8")
        x.pykota(version=version.__version__, author=version.__author__)
        for (entries, datatype) in zip(allentries, datatypes):
            x._push()
            x.dump(storage=self.config.get_storage_backend()["storagebackend"], type=datatype)
            headers = entries[0]
            for entry in entries[1:]:
                x._push()
                x.entry()
                for (header, value) in zip(headers, entry):
                    strvalue = str(value)
                    typval = type(value).__name__
                    if header in ("filename", "title", "options", "billingcode") \
                            and (typval == "str"):
                        try:
                            #aqui era usado o encode
                            strvalue = strvalue.encode("UTF-8")
                        except UnicodeError:
                            pass
                        strvalue = saxutils.escape(strvalue, {"'": "&apos;",
                                                              '"': "&quot;"})
                    x.attribute(strvalue, type=typval, name=header)
                x._pop()
            x._pop()
        x._output(self.outfile)
        return 0
