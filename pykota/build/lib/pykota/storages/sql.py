# PyKota
# -*- coding: ISO-8859-15 -*-
#
# PyKota : Print Quotas for CUPS and LPRng
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
# $Id: sql.py 3393 2008-07-10 19:31:52Z jerome $
#
#

"""This module defines methods common to all relational backends."""

from pykota.storage import StorageUser, StorageGroup, StoragePrinter, \
    StorageJob, StorageLastJob, StorageUserPQuota, \
    StorageGroupPQuota, StorageBillingCode


class SQLStorage:
    def storageUserFromRecord(self, username, record):
        """Returns a StorageUser instance from a database record."""
        user = StorageUser(self, username)
        user.ident = record.get("uid", record.get("userid", record.get("id")))
        user.LimitBy = record.get("limitby") or "quota"
        user.AccountBalance = record.get("balance")
        user.LifeTimePaid = record.get("lifetimepaid")
        user.Email = record.get("email")
        user.Description = self.databaseToUserCharset(record.get("description"))
        user.OverCharge = record.get("overcharge", 1.0)
        user.Exists = True
        return user

    def storageGroupFromRecord(self, groupname, record):
        """Returns a StorageGroup instance from a database record."""
        group = StorageGroup(self, groupname)
        group.ident = record.get("id")
        group.LimitBy = record.get("limitby") or "quota"
        group.AccountBalance = record.get("balance")
        group.LifeTimePaid = record.get("lifetimepaid")
        group.Description = self.databaseToUserCharset(record.get("description"))
        group.Exists = True
        return group

    def storagePrinterFromRecord(self, printername, record):
        """Returns a StoragePrinter instance from a database record."""
        printer = StoragePrinter(self, printername)
        printer.ident = record.get("id")
        printer.PricePerJob = record.get("priceperjob") or 0.0
        printer.PricePerPage = record.get("priceperpage") or 0.0
        printer.MaxJobSize = record.get("maxjobsize") or 0
        printer.PassThrough = record.get("passthrough") or 0
        if printer.PassThrough in (1, "1", "t", "true", "TRUE", "True"):
            printer.PassThrough = True
        else:
            printer.PassThrough = False
        printer.Description = self.databaseToUserCharset(
            record.get("description") or "")  # TODO : is 'or ""' still needed ?
        printer.Exists = True
        return printer

    def setJobAttributesFromRecord(self, job, record):
        """Sets the attributes of a job from a database record."""
        job.ident = record.get("id")
        job.JobId = record.get("jobid")
        job.PrinterPageCounter = record.get("pagecounter")
        job.JobSize = record.get("jobsize")
        job.JobPrice = record.get("jobprice")
        job.JobAction = record.get("action")
        job.JobFileName = self.databaseToUserCharset(record.get("filename") or "")
        job.JobTitle = self.databaseToUserCharset(record.get("title") or "")
        job.JobCopies = record.get("copies")
        job.JobOptions = self.databaseToUserCharset(record.get("options") or "")
        job.JobDate = record.get("jobdate")
        job.JobHostName = record.get("hostname")
        job.JobSizeBytes = record.get("jobsizebytes")
        job.JobMD5Sum = record.get("md5sum")
        job.JobPages = record.get("pages")
        job.JobBillingCode = self.databaseToUserCharset(record.get("billingcode") or "")
        job.PrecomputedJobSize = record.get("precomputedjobsize")
        job.PrecomputedJobPrice = record.get("precomputedjobprice")
        job.UserName = self.databaseToUserCharset(record.get("username"))
        job.PrinterName = self.databaseToUserCharset(record.get("printername"))
        if job.JobTitle == job.JobFileName == job.JobOptions == "hidden":
            (job.JobTitle, job.JobFileName, job.JobOptions) = ("Hidden because of privacy concerns",) * 3
        job.Exists = True

    def storageJobFromRecord(self, record):
        """Returns a StorageJob instance from a database record."""
        job = StorageJob(self)
        self.setJobAttributesFromRecord(job, record)
        return job

    def storageLastJobFromRecord(self, printer, record):
        """Returns a StorageLastJob instance from a database record."""
        lastjob = StorageLastJob(self, printer)
        self.setJobAttributesFromRecord(lastjob, record)
        return lastjob

    def storageUserPQuotaFromRecord(self, user, printer, record):
        """Returns a StorageUserPQuota instance from a database record."""
        userpquota = StorageUserPQuota(self, user, printer)
        userpquota.ident = record.get("id")
        userpquota.PageCounter = record.get("pagecounter")
        userpquota.LifePageCounter = record.get("lifepagecounter")
        userpquota.SoftLimit = record.get("softlimit")
        userpquota.HardLimit = record.get("hardlimit")
        userpquota.DateLimit = record.get("datelimit")
        userpquota.WarnCount = record.get("warncount") or 0
        userpquota.Exists = True
        return userpquota

    def storageGroupPQuotaFromRecord(self, group, printer, record):
        """Returns a StorageGroupPQuota instance from a database record."""
        grouppquota = StorageGroupPQuota(self, group, printer)
        grouppquota.ident = record.get("id")
        grouppquota.SoftLimit = record.get("softlimit")
        grouppquota.HardLimit = record.get("hardlimit")
        grouppquota.DateLimit = record.get("datelimit")
        result = self.doSearch(
            f"SELECT SUM(lifepagecounter) AS lifepagecounter, SUM(pagecounter) AS pagecounter FROM userpquota WHERE printerid={self.doQuote(printer.ident)} AND userid IN (SELECT userid FROM groupsmembers WHERE groupid={self.doQuote(group.ident)})")
        if result:
            grouppquota.PageCounter = result[0].get("pagecounter") or 0
            grouppquota.LifePageCounter = result[0].get("lifepagecounter") or 0
        grouppquota.Exists = True
        return grouppquota

    def storageBillingCodeFromRecord(self, billingcode, record):
        """Returns a StorageBillingCode instance from a database record."""
        code = StorageBillingCode(self, billingcode)
        code.ident = record.get("id")
        code.Description = self.databaseToUserCharset(
            record.get("description") or "")  # TODO : is 'or ""' still needed ?
        code.Balance = record.get("balance") or 0.0
        code.PageCounter = record.get("pagecounter") or 0
        code.Exists = True
        return code

    def createFilter(self, only):
        """Returns the appropriate SQL filter."""
        if only:
            expressions = []
            for (k, v) in only.items():
                expressions.append(f"{k}={self.doQuote(self.userCharsetToDatabase(v))}")
            return " AND ".join(expressions)
        return ""

    def createOrderBy(self, default, ordering):
        """Creates a suitable ORDER BY statement based on a list of fieldnames prefixed with '+' (ASC) or '-' (DESC)."""
        statements = []
        if not ordering:
            ordering = default
        for field in ordering:
            if field.startswith("-"):
                statements.append(f"{field[1:]} DESC")
            elif field.startswith("+"):
                statements.append(f"{field[1:]} ASC")
            else:
                statements.append(f"{field} ASC")
        return ", ".join(statements)

    def extractPrinters(self, extractonly={}, ordering=[]):
        """Extracts all printer records."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"WHERE {thefilter}"
        orderby = self.createOrderBy(["+id"], ordering)
        result = self.doRawSearch("SELECT * FROM printers {thefilter} ORDER BY {orderby}".format(**locals()))
        return self.prepareRawResult(result)

    def extractUsers(self, extractonly={}, ordering=[]):
        """Extracts all user records."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"WHERE {thefilter}"
        orderby = self.createOrderBy(["+id"], ordering)
        result = self.doRawSearch("SELECT * FROM users {thefilter} ORDER BY {orderby}".format(**locals()))
        return self.prepareRawResult(result)

    def extractBillingcodes(self, extractonly={}, ordering=[]):
        """Extracts all billing codes records."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"WHERE {thefilter}"
        orderby = self.createOrderBy(["+id"], ordering)
        result = self.doRawSearch("SELECT * FROM billingcodes {thefilter} ORDER BY {orderby}".format(**locals()))
        return self.prepareRawResult(result)

    def extractGroups(self, extractonly={}, ordering=[]):
        """Extracts all group records."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"WHERE {thefilter}"
        orderby = self.createOrderBy(["+groups.id"], ordering)
        result = self.doRawSearch(
            "SELECT groups.*,COALESCE(SUM(balance), 0) AS balance, COALESCE(SUM(lifetimepaid), 0) as lifetimepaid FROM groups LEFT OUTER JOIN users ON users.id IN (SELECT userid FROM groupsmembers WHERE groupid=groups.id) {thefilter} GROUP BY groups.id,groups.groupname,groups.limitby,groups.description ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def extractPayments(self, extractonly={}, ordering=[]):
        """Extracts all payment records."""
        startdate = extractonly.get("start")
        enddate = extractonly.get("end")
        for limit in ("start", "end"):
            try:
                del extractonly[limit]
            except KeyError:
                pass
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"AND {thefilter}"
        (startdate, enddate) = self.cleanDates(startdate, enddate)
        if startdate:
            thefilter = f"{thefilter} AND date>={self.doQuote(startdate)}"
        if enddate:
            thefilter = f"{thefilter} AND date<={self.doQuote(enddate)}"
        orderby = self.createOrderBy(["+payments.id"], ordering)
        result = self.doRawSearch(
            "SELECT username,payments.* FROM users,payments WHERE users.id=payments.userid {thefilter} ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def extractUpquotas(self, extractonly={}, ordering=[]):
        """Extracts all userpquota records."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"AND {thefilter}"
        orderby = self.createOrderBy(["+userpquota.id"], ordering)
        result = self.doRawSearch(
            "SELECT users.username,printers.printername,userpquota.* FROM users,printers,userpquota WHERE users.id=userpquota.userid AND printers.id=userpquota.printerid {thefilter} ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def extractGpquotas(self, extractonly={}, ordering=[]):
        """Extracts all grouppquota records."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"AND {thefilter}"
        orderby = self.createOrderBy(["+grouppquota.id"], ordering)
        result = self.doRawSearch(
            "SELECT groups.groupname,printers.printername,grouppquota.*,coalesce(sum(pagecounter), 0) AS pagecounter,coalesce(sum(lifepagecounter), 0) AS lifepagecounter FROM groups,printers,grouppquota,userpquota WHERE groups.id=grouppquota.groupid AND printers.id=grouppquota.printerid AND userpquota.printerid=grouppquota.printerid AND userpquota.userid IN (SELECT userid FROM groupsmembers WHERE groupsmembers.groupid=grouppquota.groupid) {thefilter} GROUP BY grouppquota.id,grouppquota.groupid,grouppquota.printerid,grouppquota.softlimit,grouppquota.hardlimit,grouppquota.datelimit,grouppquota.maxjobsize,groups.groupname,printers.printername ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def extractUmembers(self, extractonly={}, ordering=[]):
        """Extracts all user groups members."""
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"AND {thefilter}"
        orderby = self.createOrderBy(["+groupsmembers.groupid", "+groupsmembers.userid"], ordering)
        result = self.doRawSearch(
            "SELECT groups.groupname, users.username, groupsmembers.* FROM groups,users,groupsmembers WHERE users.id=groupsmembers.userid AND groups.id=groupsmembers.groupid {thefilter} ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def extractPmembers(self, extractonly={}, ordering=[]):
        """Extracts all printer groups members."""
        for (k, v) in extractonly.items():
            if k == "pgroupname":
                del extractonly[k]
                extractonly["p1.printername"] = v
            elif k == "printername":
                del extractonly[k]
                extractonly["p2.printername"] = v
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"AND {thefilter}"
        orderby = self.createOrderBy(["+printergroupsmembers.groupid", "+printergroupsmembers.printerid"], ordering)
        result = self.doRawSearch(
            "SELECT p1.printername as pgroupname, p2.printername as printername, printergroupsmembers.* FROM printers p1, printers p2, printergroupsmembers WHERE p1.id=printergroupsmembers.groupid AND p2.id=printergroupsmembers.printerid {thefilter} ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def extractHistory(self, extractonly={}, ordering=[]):
        """Extracts all jobhistory records."""
        startdate = extractonly.get("start")
        enddate = extractonly.get("end")
        for limit in ("start", "end"):
            try:
                del extractonly[limit]
            except KeyError:
                pass
        thefilter = self.createFilter(extractonly)
        if thefilter:
            thefilter = f"AND {thefilter}"
        (startdate, enddate) = self.cleanDates(startdate, enddate)
        if startdate:
            thefilter = f"{thefilter} AND jobdate>={self.doQuote(startdate)}"
        if enddate:
            thefilter = f"{thefilter} AND jobdate<={self.doQuote(enddate)}"
        orderby = self.createOrderBy(["+jobhistory.id"], ordering)
        result = self.doRawSearch(
            "SELECT users.username,printers.printername,jobhistory.* FROM users,printers,jobhistory WHERE users.id=jobhistory.userid AND printers.id=jobhistory.printerid {thefilter} ORDER BY {orderby}".format(
                **locals()))
        return self.prepareRawResult(result)

    def filterNames(self, records, attribute, patterns=None):
        """Returns a list of 'attribute' from a list of records.
        
           Logs any missing attribute.
        """
        result = []
        for record in records:
            attrval = record.get(attribute, [None])
            if attrval is None:
                self.tool.printInfo(f"Object {repr(record)} has no {attribute} attribute !", "error")
            else:
                attrval = self.databaseToUserCharset(attrval)
                if patterns:
                    if (not isinstance(patterns, type([]))) and (not isinstance(patterns, type(()))):
                        patterns = [patterns]
                    if self.tool.matchString(attrval, patterns):
                        result.append(attrval)
                else:
                    result.append(attrval)
        return result

    def getAllBillingCodes(self, billingcode=None):
        """Extracts all billing codes or only the billing codes matching the optional parameter."""
        result = self.doSearch("SELECT billingcode FROM billingcodes")
        if result:
            return self.filterNames(result, "billingcode", billingcode)
        else:
            return []

    def getAllPrintersNames(self, printername=None):
        """Extracts all printer names or only the printers' names matching the optional parameter."""
        result = self.doSearch("SELECT printername FROM printers")
        if result:
            return self.filterNames(result, "printername", printername)
        else:
            return []

    def getAllUsersNames(self, username=None):
        """Extracts all user names."""
        result = self.doSearch("SELECT username FROM users")
        if result:
            return self.filterNames(result, "username", username)
        else:
            return []

    def getAllGroupsNames(self, groupname=None):
        """Extracts all group names."""
        result = self.doSearch("SELECT groupname FROM groups")
        if result:
            return self.filterNames(result, "groupname", groupname)
        else:
            return []

    def getUserNbJobsFromHistory(self, user):
        """Returns the number of jobs the user has in history."""
        result = self.doSearch(f"SELECT COUNT(*) AS count FROM jobhistory WHERE userid={self.doQuote(user.ident)}")
        if result:
            return result[0]["count"]
        return 0

    def getUserFromBackend(self, username):
        """Extracts user information given its name."""
        result = self.doSearch(
            f"SELECT * FROM users WHERE username={self.doQuote(username)} LIMIT 1")
        if result:
            return self.storageUserFromRecord(username, result[0])
        else:
            return StorageUser(self, username)

    def getGroupFromBackend(self, groupname):
        """Extracts group information given its name."""
        result = self.doSearch(
            f"SELECT groups.*,COALESCE(SUM(balance), 0.0) AS balance, COALESCE(SUM(lifetimepaid), 0.0) AS lifetimepaid FROM groups LEFT OUTER JOIN users ON users.id IN (SELECT userid FROM groupsmembers WHERE groupid=groups.id) WHERE groupname={self.doQuote(self.userCharsetToDatabase(groupname))} GROUP BY groups.id,groups.groupname,groups.limitby,groups.description LIMIT 1")
        if result:
            return self.storageGroupFromRecord(groupname, result[0])
        else:
            return StorageGroup(self, groupname)

    def getPrinterFromBackend(self, printername):
        """Extracts printer information given its name."""
        result = self.doSearch(
            f"SELECT * FROM printers WHERE printername={self.doQuote(self.userCharsetToDatabase(printername))} LIMIT 1")
        if result:
            return self.storagePrinterFromRecord(printername, result[0])
        else:
            return StoragePrinter(self, printername)

    def getBillingCodeFromBackend(self, label):
        """Extracts a billing code information given its name."""
        result = self.doSearch(
            f"SELECT * FROM billingcodes WHERE billingcode={self.doQuote(self.userCharsetToDatabase(label))} LIMIT 1")
        if result:
            return self.storageBillingCodeFromRecord(label, result[0])
        else:
            return StorageBillingCode(self, label)

    def getUserPQuotaFromBackend(self, user, printer):
        """Extracts a user print quota."""
        if printer.Exists and user.Exists:
            result = self.doSearch(
                f"SELECT * FROM userpquota WHERE userid={self.doQuote(user.ident)} AND printerid={self.doQuote(printer.ident)};")
            if result:
                return self.storageUserPQuotaFromRecord(user, printer, result[0])
        return StorageUserPQuota(self, user, printer)

    def getGroupPQuotaFromBackend(self, group, printer):
        """Extracts a group print quota."""
        if printer.Exists and group.Exists:
            result = self.doSearch(
                f"SELECT * FROM grouppquota WHERE groupid={self.doQuote(group.ident)} AND printerid={self.doQuote(printer.ident)}")
            if result:
                return self.storageGroupPQuotaFromRecord(group, printer, result[0])
        return StorageGroupPQuota(self, group, printer)

    def getPrinterLastJobFromBackend(self, printer):
        """Extracts a printer's last job information."""
        result = self.doSearch(
            "SELECT jobhistory.id, jobid, userid, username, pagecounter, jobsize, jobprice, filename, title, copies, options, hostname, jobdate, md5sum, pages, billingcode, precomputedjobsize, precomputedjobprice FROM jobhistory, users WHERE printerid={} AND userid=users.id ORDER BY jobdate DESC LIMIT 1".format(
                self.doQuote(
                    printer.ident)))
        if result:
            return self.storageLastJobFromRecord(printer, result[0])
        else:
            return StorageLastJob(self, printer)

    def getGroupMembersFromBackend(self, group):
        """Returns the group's members list."""
        groupmembers = []
        result = self.doSearch(
            "SELECT * FROM groupsmembers JOIN users ON groupsmembers.userid=users.id WHERE groupid={}".format(
                self.doQuote(
                    group.ident)))
        if result:
            for record in result:
                user = self.storageUserFromRecord(self.databaseToUserCharset(record.get("username")),
                                                  record)
                groupmembers.append(user)
                self.cacheEntry("USERS", user.Name, user)
        return groupmembers

    def getUserGroupsFromBackend(self, user):
        """Returns the user's groups list."""
        groups = []
        result = self.doSearch(
            "SELECT groupname FROM groupsmembers JOIN groups ON groupsmembers.groupid=groups.id WHERE userid={}".format(
                self.doQuote(
                    user.ident)))
        if result:
            for record in result:
                groups.append(self.getGroup(self.databaseToUserCharset(record.get("groupname"))))
        return groups

    def getParentPrintersFromBackend(self, printer):
        """Get all the printer groups this printer is a member of."""
        pgroups = []
        result = self.doSearch(
            "SELECT groupid,printername FROM printergroupsmembers JOIN printers ON groupid=id WHERE printerid={}".format(
                self.doQuote(
                    printer.ident)))
        if result:
            for record in result:
                if record["groupid"] != printer.ident:  # in case of integrity violation
                    parentprinter = self.getPrinter(self.databaseToUserCharset(record.get("printername")))
                    if parentprinter.Exists:
                        pgroups.append(parentprinter)
        return pgroups

    def getMatchingPrinters(self, printerpattern):
        """Returns the list of all printers for which name matches a certain pattern."""
        printers = []
        # We 'could' do a SELECT printername FROM printers WHERE printername LIKE ...
        # but we don't because other storages semantics may be different, so every
        # storage should use fnmatch to match patterns and be storage agnostic
        result = self.doSearch("SELECT * FROM printers")
        if result:
            patterns = printerpattern.split(",")
            try:
                patdict = {}.fromkeys(patterns)
            except AttributeError:
                # Python v2.2 or earlier
                patdict = {}
                for p in patterns:
                    patdict[p] = None
            for record in result:
                pname = self.databaseToUserCharset(record["printername"])
                if (pname in patdict) or self.tool.matchString(pname, patterns):
                    printer = self.storagePrinterFromRecord(pname, record)
                    printers.append(printer)
                    self.cacheEntry("PRINTERS", printer.Name, printer)
        return printers

    def getMatchingUsers(self, userpattern):
        """Returns the list of all users for which name matches a certain pattern."""
        users = []
        # We 'could' do a SELECT username FROM users WHERE username LIKE ...
        # but we don't because other storages semantics may be different, so every
        # storage should use fnmatch to match patterns and be storage agnostic
        result = self.doSearch("SELECT * FROM users")
        if result:
            patterns = userpattern.split(",")
            try:
                patdict = {}.fromkeys(patterns)
            except AttributeError:
                # Python v2.2 or earlier
                patdict = {}
                for p in patterns:
                    patdict[p] = None
            for record in result:
                uname = self.databaseToUserCharset(record["username"])
                if (uname in patdict) or self.tool.matchString(uname, patterns):
                    user = self.storageUserFromRecord(uname, record)
                    users.append(user)
                    self.cacheEntry("USERS", user.Name, user)
        return users

    def getMatchingGroups(self, grouppattern):
        """Returns the list of all groups for which name matches a certain pattern."""
        groups = []
        # We 'could' do a SELECT groupname FROM groups WHERE groupname LIKE ...
        # but we don't because other storages semantics may be different, so every
        # storage should use fnmatch to match patterns and be storage agnostic
        result = self.doSearch(
            "SELECT groups.*,COALESCE(SUM(balance), 0.0) AS balance, COALESCE(SUM(lifetimepaid), 0.0) AS lifetimepaid FROM groups LEFT OUTER JOIN users ON users.id IN (SELECT userid FROM groupsmembers WHERE groupid=groups.id) GROUP BY groups.id,groups.groupname,groups.limitby,groups.description")
        if result:
            patterns = grouppattern.split(",")
            try:
                patdict = {}.fromkeys(patterns)
            except AttributeError:
                # Python v2.2 or earlier
                patdict = {}
                for p in patterns:
                    patdict[p] = None
            for record in result:
                gname = self.databaseToUserCharset(record["groupname"])
                if patdict.has_key(gname) or self.tool.matchString(gname, patterns):
                    group = self.storageGroupFromRecord(gname, record)
                    groups.append(group)
                    self.cacheEntry("GROUPS", group.Name, group)
        return groups

    def getMatchingBillingCodes(self, billingcodepattern):
        """Returns the list of all billing codes for which the label matches a certain pattern."""
        codes = []
        result = self.doSearch("SELECT * FROM billingcodes")
        if result:
            patterns = billingcodepattern.split(",")
            try:
                patdict = {}.fromkeys(patterns)
            except AttributeError:
                # Python v2.2 or earlier
                patdict = {}
                for p in patterns:
                    patdict[p] = None
            for record in result:
                codename = self.databaseToUserCharset(record["billingcode"])
                if patdict.has_key(codename) or self.tool.matchString(codename, patterns):
                    code = self.storageBillingCodeFromRecord(codename, record)
                    codes.append(code)
                    self.cacheEntry("BILLINGCODES", code.BillingCode, code)
        return codes

    def getPrinterUsersAndQuotas(self, printer, names=["*"]):
        """Returns the list of users who uses a given printer, along with their quotas."""
        usersandquotas = []
        result = self.doSearch(
            "SELECT users.id as uid,username,description,balance,lifetimepaid,limitby,email,overcharge,userpquota.id,lifepagecounter,pagecounter,softlimit,hardlimit,datelimit,warncount FROM users JOIN userpquota ON users.id=userpquota.userid AND printerid={} ORDER BY username ASC".format(
                self.doQuote(
                    printer.ident)))
        if result:
            for record in result:
                uname = self.databaseToUserCharset(record.get("username"))
                if self.tool.matchString(uname, names):
                    user = self.storageUserFromRecord(uname, record)
                    userpquota = self.storageUserPQuotaFromRecord(user, printer, record)
                    usersandquotas.append((user, userpquota))
                    self.cacheEntry("USERS", user.Name, user)
                    self.cacheEntry("USERPQUOTAS", f"{user.Name}@{printer.Name}", userpquota)
        return usersandquotas

    def getPrinterGroupsAndQuotas(self, printer, names=["*"]):
        """Returns the list of groups which uses a given printer, along with their quotas."""
        groupsandquotas = []
        result = self.doSearch(
            "SELECT groupname FROM groups JOIN grouppquota ON groups.id=grouppquota.groupid AND printerid={} ORDER BY groupname ASC".format(
                self.doQuote(
                    printer.ident)))
        if result:
            for record in result:
                gname = self.databaseToUserCharset(record.get("groupname"))
                if self.tool.matchString(gname, names):
                    group = self.getGroup(gname)
                    grouppquota = self.getGroupPQuota(group, printer)
                    groupsandquotas.append((group, grouppquota))
        return groupsandquotas

    def addPrinter(self, printer):
        """Adds a printer to the quota storage, returns the old value if it already exists."""
        oldentry = self.getPrinter(printer.Name)
        if oldentry.Exists:
            return oldentry
        self.doModify(
            f"INSERT INTO printers (printername, passthrough, maxjobsize, description, priceperpage, priceperjob) VALUES ({self.doQuote(self.userCharsetToDatabase(printer.Name))}, {self.doQuote((printer.PassThrough and 't') or 'f')}, {self.doQuote(printer.MaxJobSize or 0)}, {self.doQuote(self.userCharsetToDatabase(printer.Description))}, {self.doQuote(printer.PricePerPage or 0.0)}, {self.doQuote(printer.PricePerJob or 0.0)})")
        printer.isDirty = False
        return None  # the entry created doesn't need further modification

    def addBillingCode(self, bcode):
        """Adds a billing code to the quota storage, returns the old value if it already exists."""
        oldentry = self.getBillingCode(bcode.BillingCode)
        if oldentry.Exists:
            return oldentry
        self.doModify(
            f"INSERT INTO billingcodes (billingcode, balance, pagecounter, description) VALUES ({self.doQuote(self.userCharsetToDatabase(bcode.BillingCode))}, {self.doQuote(bcode.Balance or 0.0)}, {self.doQuote(bcode.PageCounter or 0)}, {self.doQuote(self.userCharsetToDatabase(bcode.Description))})")
        bcode.isDirty = False
        return None  # the entry created doesn't need further modification

    def addUser(self, user):
        """Adds a user to the quota storage, returns the old value if it already exists."""
        oldentry = self.getUser(user.Name)
        if oldentry.Exists:
            return oldentry
        self.doModify(
            f"INSERT INTO users (username, limitby, balance, lifetimepaid, email, overcharge, description) VALUES ({self.doQuote(self.userCharsetToDatabase(user.Name))}, {self.doQuote(user.LimitBy or 'quota')}, {self.doQuote(user.AccountBalance or 0.0)}, {self.doQuote(user.LifeTimePaid or 0.0)}, {self.doQuote(user.Email)}, {self.doQuote(user.OverCharge)}, {self.doQuote(self.userCharsetToDatabase(user.Description))})")
        if user.PaymentsBacklog:
            for (value, comment) in user.PaymentsBacklog:
                self.writeNewPayment(user, value, comment)
            user.PaymentsBacklog = []
        user.isDirty = False
        return None  # the entry created doesn't need further modification

    def addGroup(self, group):
        """Adds a group to the quota storage, returns the old value if it already exists."""
        oldentry = self.getGroup(group.Name)
        if oldentry.Exists:
            return oldentry
        self.doModify(
            f"INSERT INTO groups (groupname, limitby, description) VALUES ({self.doQuote(self.userCharsetToDatabase(group.Name))}, {self.doQuote(group.LimitBy or 'quota')}, {self.doQuote(self.userCharsetToDatabase(group.Description))})")
        group.isDirty = False
        return None  # the entry created doesn't need further modification

    def addUserToGroup(self, user, group):
        """Adds an user to a group."""
        result = self.doSearch(
            f"SELECT COUNT(*) AS mexists FROM groupsmembers WHERE groupid={self.doQuote(group.ident)} AND userid={self.doQuote(user.ident)}")
        try:
            mexists = int(result[0].get("mexists"))
        except (IndexError, TypeError):
            mexists = 0
        if not mexists:
            self.doModify(
                f"INSERT INTO groupsmembers (groupid, userid) VALUES ({self.doQuote(group.ident)}, {self.doQuote(user.ident)})")

    def delUserFromGroup(self, user, group):
        """Removes an user from a group."""
        self.doModify(
            f"DELETE FROM groupsmembers WHERE groupid={self.doQuote(group.ident)} AND userid={self.doQuote(user.ident)}")

    def addUserPQuota(self, upq):
        """Initializes a user print quota on a printer."""
        oldentry = self.getUserPQuota(upq.User, upq.Printer)
        if oldentry.Exists:
            return oldentry
        self.doModify(
            f"INSERT INTO userpquota (userid, printerid, softlimit, hardlimit, warncount, datelimit, pagecounter, lifepagecounter, maxjobsize) VALUES ({self.doQuote(upq.User.ident)}, {self.doQuote(upq.Printer.ident)}, {self.doQuote(upq.SoftLimit)}, {self.doQuote(upq.HardLimit)}, {self.doQuote(upq.WarnCount or 0)}, {self.doQuote(upq.DateLimit)}, {self.doQuote(upq.PageCounter or 0)}, {self.doQuote(upq.LifePageCounter or 0)}, {self.doQuote(upq.MaxJobSize)})")
        upq.isDirty = False
        return None  # the entry created doesn't need further modification

    def addGroupPQuota(self, gpq):
        """Initializes a group print quota on a printer."""
        oldentry = self.getGroupPQuota(gpq.Group, gpq.Printer)
        if oldentry.Exists:
            return oldentry
        self.doModify(
            f"INSERT INTO grouppquota (groupid, printerid, softlimit, hardlimit, datelimit, maxjobsize) VALUES ({self.doQuote(gpq.Group.ident)}, {self.doQuote(gpq.Printer.ident)}, {self.doQuote(gpq.SoftLimit)}, {self.doQuote(gpq.HardLimit)}, {self.doQuote(gpq.DateLimit)}, {self.doQuote(gpq.MaxJobSize)})")
        gpq.isDirty = False
        return None  # the entry created doesn't need further modification

    def savePrinter(self, printer):
        """Saves the printer to the database in a single operation."""
        self.doModify(
            f"UPDATE printers SET passthrough={self.doQuote((printer.PassThrough and 't') or 'f')}, maxjobsize={self.doQuote(printer.MaxJobSize or 0)}, description={self.doQuote(self.userCharsetToDatabase(printer.Description))}, priceperpage={self.doQuote(printer.PricePerPage or 0.0)}, priceperjob={self.doQuote(printer.PricePerJob or 0.0)} WHERE id={self.doQuote(printer.ident)}")

    def saveUser(self, user):
        """Saves the user to the database in a single operation."""
        self.doModify(
            f"UPDATE users SET limitby={self.doQuote(user.LimitBy or 'quota')}, balance={self.doQuote(user.AccountBalance or 0.0)}, lifetimepaid={self.doQuote(user.LifeTimePaid or 0.0)}, email={self.doQuote(user.Email)}, overcharge={self.doQuote(user.OverCharge)}, description={self.doQuote(self.userCharsetToDatabase(user.Description))} WHERE id={self.doQuote(user.ident)}")

    def saveGroup(self, group):
        """Saves the group to the database in a single operation."""
        self.doModify(
            f"UPDATE groups SET limitby={self.doQuote(group.LimitBy or 'quota')}, description={self.doQuote(self.userCharsetToDatabase(group.Description))} WHERE id={self.doQuote(group.ident)}")

    def writeUserPQuotaDateLimit(self, userpquota, datelimit):
        """Sets the date limit permanently for a user print quota."""
        self.doModify(
            f"UPDATE userpquota SET datelimit={self.doQuote(datelimit)} WHERE id={self.doQuote(userpquota.ident)}")

    def writeGroupPQuotaDateLimit(self, grouppquota, datelimit):
        """Sets the date limit permanently for a group print quota."""
        self.doModify(
            f"UPDATE grouppquota SET datelimit={self.doQuote(datelimit)} WHERE id={self.doQuote(grouppquota.ident)}")

    def increaseUserPQuotaPagesCounters(self, userpquota, nbpages):
        """Increase page counters for a user print quota."""
        self.doModify(
            f"UPDATE userpquota SET pagecounter=pagecounter + {self.doQuote(nbpages)},lifepagecounter=lifepagecounter + {self.doQuote(nbpages)} WHERE id={self.doQuote(userpquota.ident)}")

    def saveBillingCode(self, bcode):
        """Saves the billing code to the database."""
        self.doModify(
            f"UPDATE billingcodes SET balance={self.doQuote(bcode.Balance or 0.0)}, pagecounter={self.doQuote(bcode.PageCounter or 0)}, description={self.doQuote(self.userCharsetToDatabase(bcode.Description))} WHERE id={self.doQuote(bcode.ident)}")

    def consumeBillingCode(self, bcode, pagecounter, balance):
        """Consumes from a billing code."""
        self.doModify(
            f"UPDATE billingcodes SET balance=balance + {self.doQuote(balance)}, pagecounter=pagecounter + {self.doQuote(pagecounter)} WHERE id={self.doQuote(bcode.ident)}")

    def refundJob(self, jobident):
        """Marks a job as refunded in the history."""
        self.doModify(f"UPDATE jobhistory SET action='REFUND' WHERE id={self.doQuote(jobident)};")

    def decreaseUserAccountBalance(self, user, amount):
        """Decreases user's account balance from an amount."""
        self.doModify(
            f"UPDATE users SET balance=balance - {self.doQuote(amount)} WHERE id={self.doQuote(user.ident)}")

    def writeNewPayment(self, user, amount, comment=""):
        """Adds a new payment to the payments history."""
        if user.ident is not None:
            self.doModify(
                f"INSERT INTO payments (userid, amount, description) VALUES ({self.doQuote(user.ident)}, {self.doQuote(amount)}, {self.doQuote(self.userCharsetToDatabase(comment))})")
        else:
            self.doModify(
                f"INSERT INTO payments (userid, amount, description) VALUES ((SELECT id FROM users WHERE username={self.doQuote(self.userCharsetToDatabase(user.Name))}), {self.doQuote(amount)}, {self.doQuote(self.userCharsetToDatabase(comment))})")

    def writeLastJobSize(self, lastjob, jobsize, jobprice):
        """Sets the last job's size permanently."""
        self.doModify(
            f"UPDATE jobhistory SET jobsize={self.doQuote(jobsize)}, jobprice={self.doQuote(jobprice)} WHERE id={self.doQuote(lastjob.ident)}")

    def writeJobNew(self, printer, user, jobid, pagecounter, action, jobsize=None, jobprice=None, filename=None,
                    title=None, copies=None, options=None, clienthost=None, jobsizebytes=None, jobmd5sum=None,
                    jobpages=None, jobbilling=None, precomputedsize=None, precomputedprice=None):
        """Adds a job in a printer's history."""
        if self.privacy:
            # For legal reasons, we want to hide the title, filename and options
            title = filename = options = "hidden"
        filename = self.userCharsetToDatabase(filename)
        title = self.userCharsetToDatabase(title)
        options = self.userCharsetToDatabase(options)
        jobbilling = self.userCharsetToDatabase(jobbilling)
        if (not self.disablehistory) or (not printer.LastJob.Exists):
            if jobsize is not None:
                self.doModify(
                    f"INSERT INTO jobhistory (userid, printerid, jobid, pagecounter, action, jobsize, jobprice, filename, title, copies, options, hostname, jobsizebytes, md5sum, pages, billingcode, precomputedjobsize, precomputedjobprice) VALUES ({self.doQuote(user.ident)}, {self.doQuote(printer.ident)}, {self.doQuote(jobid)}, {self.doQuote(pagecounter)}, {self.doQuote(action)}, {self.doQuote(jobsize)}, {self.doQuote(jobprice)}, {self.doQuote(filename)}, {self.doQuote(title)}, {self.doQuote(copies)}, {self.doQuote(options)}, {self.doQuote(clienthost)}, {self.doQuote(jobsizebytes)}, {self.doQuote(jobmd5sum)}, {self.doQuote(jobpages)}, {self.doQuote(jobbilling)}, {self.doQuote(precomputedsize)}, {self.doQuote(precomputedprice)})")
            else:
                self.doModify(
                    f"INSERT INTO jobhistory (userid, printerid, jobid, pagecounter, action, filename, title, copies, options, hostname, jobsizebytes, md5sum, pages, billingcode, precomputedjobsize, precomputedjobprice) VALUES ({self.doQuote(user.ident)}, {self.doQuote(printer.ident)}, {self.doQuote(jobid)}, {self.doQuote(pagecounter)}, {self.doQuote(action)}, {self.doQuote(filename)}, {self.doQuote(title)}, {self.doQuote(copies)}, {self.doQuote(options)}, {self.doQuote(clienthost)}, {self.doQuote(jobsizebytes)}, {self.doQuote(jobmd5sum)}, {self.doQuote(jobpages)}, {self.doQuote(jobbilling)}, {self.doQuote(precomputedsize)}, {self.doQuote(precomputedprice)})")
        else:
            # here we explicitly want to reset jobsize to NULL if needed
            self.doModify(
                f"UPDATE jobhistory SET userid={self.doQuote(user.ident)}, jobid={self.doQuote(jobid)}, pagecounter={self.doQuote(pagecounter)}, action={self.doQuote(action)}, jobsize={self.doQuote(jobsize)}, jobprice={self.doQuote(jobprice)}, filename={self.doQuote(filename)}, title={self.doQuote(title)}, copies={self.doQuote(copies)}, options={self.doQuote(options)}, hostname={self.doQuote(clienthost)}, jobsizebytes={self.doQuote(jobsizebytes)}, md5sum={self.doQuote(jobmd5sum)}, pages={self.doQuote(jobpages)}, billingcode={self.doQuote(jobbilling)}, precomputedjobsize={self.doQuote(precomputedsize)}, precomputedjobprice={self.doQuote(precomputedprice)}, jobdate=now() WHERE id={self.doQuote(printer.LastJob.ident)}")

    def saveUserPQuota(self, userpquota):
        """Saves an user print quota entry."""
        self.doModify(
            f"UPDATE userpquota SET softlimit={self.doQuote(userpquota.SoftLimit)}, hardlimit={self.doQuote(userpquota.HardLimit)}, warncount={self.doQuote(userpquota.WarnCount or 0)}, datelimit={self.doQuote(userpquota.DateLimit)}, pagecounter={self.doQuote(userpquota.PageCounter or 0)}, lifepagecounter={self.doQuote(userpquota.LifePageCounter or 0)}, maxjobsize={self.doQuote(userpquota.MaxJobSize)} WHERE id={self.doQuote(userpquota.ident)}")

    def writeUserPQuotaWarnCount(self, userpquota, warncount):
        """Sets the warn counter value for a user quota."""
        self.doModify(
            f"UPDATE userpquota SET warncount={self.doQuote(warncount)} WHERE id={self.doQuote(userpquota.ident)}")

    def increaseUserPQuotaWarnCount(self, userpquota):
        """Increases the warn counter value for a user quota."""
        self.doModify(f"UPDATE userpquota SET warncount=warncount+1 WHERE id={self.doQuote(userpquota.ident)}")

    def saveGroupPQuota(self, grouppquota):
        """Saves a group print quota entry."""
        self.doModify(
            f"UPDATE grouppquota SET softlimit={self.doQuote(grouppquota.SoftLimit)}, hardlimit={self.doQuote(grouppquota.HardLimit)}, datelimit={self.doQuote(grouppquota.DateLimit)} WHERE id={self.doQuote(grouppquota.ident)}")

    def writePrinterToGroup(self, pgroup, printer):
        """Puts a printer into a printer group."""
        children = []
        result = self.doSearch(
            f"SELECT printerid FROM printergroupsmembers WHERE groupid={self.doQuote(pgroup.ident)}")
        if result:
            for record in result:
                children.append(record.get("printerid"))  # TODO : put this into the database integrity rules
        if printer.ident not in children:
            self.doModify(
                f"INSERT INTO printergroupsmembers (groupid, printerid) VALUES ({self.doQuote(pgroup.ident)}, {self.doQuote(printer.ident)})")

    def removePrinterFromGroup(self, pgroup, printer):
        """Removes a printer from a printer group."""
        self.doModify(
            f"DELETE FROM printergroupsmembers WHERE groupid={self.doQuote(pgroup.ident)} AND printerid={self.doQuote(printer.ident)}")

    def retrieveHistory(self, user=None, printer=None, hostname=None, billingcode=None, jobid=None, limit=100,
                        start=None, end=None):
        """Retrieves all print jobs for user on printer (or all) between start and end date, limited to first 100
        results. """
        query = "SELECT jobhistory.*,username,printername FROM jobhistory,users,printers WHERE users.id=userid AND " \
                "printers.id=printerid "
        where = []
        if user is not None:  # user.ident is None anyway if user doesn't exist
            where.append(f"userid={self.doQuote(user.ident)}")
        if printer is not None:  # printer.ident is None anyway if printer doesn't exist
            where.append(f"printerid={self.doQuote(printer.ident)}")
        if hostname is not None:
            where.append(f"hostname={self.doQuote(hostname)}")
        if billingcode is not None:
            where.append(f"billingcode={self.doQuote(self.userCharsetToDatabase(billingcode))}")
        if jobid is not None:
            where.append("jobid={}".format(self.doQuote(
                jobid)))  # TODO : jobid is text, so self.userCharsetToDatabase(jobid) but do all of them as well.
        if start is not None:
            where.append(f"jobdate>={self.doQuote(start)}")
        if end is not None:
            where.append(f"jobdate<={self.doQuote(end)}")
        if where:
            query += f" AND {' AND '.join(where)}"
        query += " ORDER BY jobhistory.id DESC"
        if limit:
            query += f" LIMIT {self.doQuote(int(limit))}"
        jobs = []
        result = self.doSearch(query)
        if result:
            for fields in result:
                job = self.storageJobFromRecord(fields)
                jobs.append(job)
        return jobs

    def deleteUser(self, user):
        """Completely deletes an user from the database."""
        # TODO : What should we do if we delete the last person who used a given printer ?
        # TODO : we can't reassign the last job to the previous one, because next user would be
        # TODO : incorrectly charged (overcharged).
        for q in [
            f"DELETE FROM payments WHERE userid={self.doQuote(user.ident)}",
            f"DELETE FROM groupsmembers WHERE userid={self.doQuote(user.ident)}",
            f"DELETE FROM jobhistory WHERE userid={self.doQuote(user.ident)}",
            f"DELETE FROM userpquota WHERE userid={self.doQuote(user.ident)}",
            f"DELETE FROM users WHERE id={self.doQuote(user.ident)}",
        ]:
            self.doModify(q)

    def multipleQueriesInTransaction(self, queries):
        """Does many modifications in a single transaction."""
        self.beginTransaction()
        try:
            for q in queries:
                self.doModify(q)
        except:
            self.rollbackTransaction()
            raise
        else:
            self.commitTransaction()

    def deleteManyBillingCodes(self, billingcodes):
        """Deletes many billing codes."""
        codeids = ", ".join([f"{self.doQuote(b.ident)}" for b in billingcodes])
        if codeids:
            self.multipleQueriesInTransaction([
                f"DELETE FROM billingcodes WHERE id IN ({codeids})", ])

    def deleteManyUsers(self, users):
        """Deletes many users."""
        userids = ", ".join([f"{self.doQuote(u.ident)}" for u in users])
        if userids:
            self.multipleQueriesInTransaction([
                f"DELETE FROM payments WHERE userid IN ({userids})",
                f"DELETE FROM groupsmembers WHERE userid IN ({userids})",
                f"DELETE FROM jobhistory WHERE userid IN ({userids})",
                f"DELETE FROM userpquota WHERE userid IN ({userids})",
                f"DELETE FROM users WHERE id IN ({userids})", ])

    def deleteManyGroups(self, groups):
        """Deletes many groups."""
        groupids = ", ".join([f"{self.doQuote(g.ident)}" for g in groups])
        if groupids:
            self.multipleQueriesInTransaction([
                f"DELETE FROM groupsmembers WHERE groupid IN ({groupids})",
                f"DELETE FROM grouppquota WHERE groupid IN ({groupids})",
                f"DELETE FROM groups WHERE id IN ({groupids})", ])

    def deleteManyPrinters(self, printers):
        """Deletes many printers."""
        printerids = ", ".join([f"{self.doQuote(p.ident)}" for p in printers])
        if printerids:
            self.multipleQueriesInTransaction([
                f"DELETE FROM printergroupsmembers WHERE groupid IN ({printerids}) OR printerid IN ({printerids})",
                f"DELETE FROM jobhistory WHERE printerid IN ({printerids})",
                f"DELETE FROM grouppquota WHERE printerid IN ({printerids})",
                f"DELETE FROM userpquota WHERE printerid IN ({printerids})",
                f"DELETE FROM printers WHERE id IN ({printerids})", ])

    def deleteManyUserPQuotas(self, printers, users):
        """Deletes many user print quota entries."""
        printerids = ", ".join([f"{self.doQuote(p.ident)}" for p in printers])
        userids = ", ".join([f"{self.doQuote(u.ident)}" for u in users])
        if userids and printerids:
            self.multipleQueriesInTransaction([
                f"DELETE FROM jobhistory WHERE userid IN ({userids}) AND printerid IN ({printerids})",
                f"DELETE FROM userpquota WHERE userid IN ({userids}) AND printerid IN ({printerids})", ])

    def deleteManyGroupPQuotas(self, printers, groups):
        """Deletes many group print quota entries."""
        printerids = ", ".join([f"{self.doQuote(p.ident)}" for p in printers])
        groupids = ", ".join([f"{self.doQuote(g.ident)}" for g in groups])
        if groupids and printerids:
            self.multipleQueriesInTransaction([
                f"DELETE FROM grouppquota WHERE groupid IN ({groupids}) AND printerid IN ({printerids})", ])

    def deleteUserPQuota(self, upquota):
        """Completely deletes an user print quota entry from the database."""
        for q in [
            f"DELETE FROM jobhistory WHERE userid={self.doQuote(upquota.User.ident)} AND printerid={self.doQuote(upquota.Printer.ident)}",
            f"DELETE FROM userpquota WHERE id={self.doQuote(upquota.ident)}",
        ]:
            self.doModify(q)

    def deleteGroupPQuota(self, gpquota):
        """Completely deletes a group print quota entry from the database."""
        for q in [
            f"DELETE FROM grouppquota WHERE id={self.doQuote(gpquota.ident)}",
        ]:
            self.doModify(q)

    def deleteGroup(self, group):
        """Completely deletes a group from the database."""
        for q in [
            f"DELETE FROM groupsmembers WHERE groupid={self.doQuote(group.ident)}",
            f"DELETE FROM grouppquota WHERE groupid={self.doQuote(group.ident)}",
            f"DELETE FROM groups WHERE id={self.doQuote(group.ident)}",
        ]:
            self.doModify(q)

    def deletePrinter(self, printer):
        """Completely deletes a printer from the database."""
        for q in [
            f"DELETE FROM printergroupsmembers WHERE groupid={self.doQuote(printer.ident)} OR printerid={self.doQuote(printer.ident)}",
            f"DELETE FROM jobhistory WHERE printerid={self.doQuote(printer.ident)}",
            f"DELETE FROM grouppquota WHERE printerid={self.doQuote(printer.ident)}",
            f"DELETE FROM userpquota WHERE printerid={self.doQuote(printer.ident)}",
            f"DELETE FROM printers WHERE id={self.doQuote(printer.ident)}",
        ]:
            self.doModify(q)

    def deleteBillingCode(self, code):
        """Completely deletes a billing code from the database."""
        for q in [
            f"DELETE FROM billingcodes WHERE id={self.doQuote(code.ident)}",
        ]:
            self.doModify(q)
