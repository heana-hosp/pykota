# PyKota
# -*- coding: ISO-8859-15 -*-

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
# $Id: tool.py 3392 2008-07-10 19:29:30Z jerome $
#
#

"""This module defines the base classes for PyKota command line tools."""

import sys
import os
import pwd
import fnmatch
import getopt
import smtplib
import gettext
import locale
import socket
import time
from email.mime import text
from email.header import Header
import email.utils


from datetime import datetime

try:
    import chardet
except ImportError:
    def detectCharset(text_charset):
        """Fakes a charset detection if the chardet module is not installed."""
        return "UTF-8"
else:
    def detectCharset(text_charset):
        """Uses the chardet module to workaround CUPS lying to us."""
        return chardet.detect(text_charset)["encoding"] or "UTF-8"

from pykota import config, storage, logger
from pykota.version import __version__, __author__, __years__, __gplblurb__


def N_(message):
    """Fake translation marker for translatable strings extraction."""
    return message


class PyKotaToolError(Exception):
    """An exception for PyKota related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class PyKotaCommandLineError(PyKotaToolError):
    """An exception for Pykota command line tools."""
    pass


def crashed(message="Bug in PyKota"):
    """Minimal crash method."""
    import traceback
    lines = []
    for line in traceback.format_exception(*sys.exc_info()):
        lines.extend([l for l in line.split("\n") if l])
    msg = "ERROR: ".join([f"{l}\n" for l in ([f"ERROR: PyKota v{__version__}", message] + lines)])
    sys.stderr.write(msg)
    sys.stderr.flush()
    return msg


class Percent:
    """A class to display progress."""

    def __init__(self, app, size=None):
        """Initializes the engine."""
        self.factor = None
        self.number = None
        self.app = app
        self.size = None
        if size:
            self.setSize(size)
        self.previous = None
        self.before = time.time()

    def setSize(self, size):
        """Sets the total size."""
        self.number = 0
        self.size = size
        if size:
            self.factor = 100.0 / float(size)

    def display(self, msg):
        """Displays the value."""
        self.app.display(msg)

    def oneMore(self):
        """Increments internal counter."""
        if self.size:
            self.number += 1
            percent = f"{float(self.number) * self.factor:.02f}"
            if percent != self.previous:  # optimize for large number of items
                self.display(f"\r{percent}%")
                self.previous = percent

    def done(self):
        """Displays the 'done' message."""
        after = time.time()
        if self.size:
            speed = self.size / (after - self.before)
            self.display(f"\r100.00%\r        \r{'Done'}. {'Average speed'} : {speed:.2f} {'entries per second'}.\n")
        else:
            self.display("\r100.00%%\r        \r%s.\n" % "Done")


class Tool:
    """Base class for tools with no database access."""

    def __init__(self, lang="", charset=None, doc="PyKota v%(__version__)s (c) %(__years__)s %(__author__)s"):
        """Initializes the command line tool."""
        self.storage = None
        self.debug = True  # in case of early failure
        self.logger = logger.open_logger("stderr")

        # did we drop priviledges ?
        self.privdropped = 0

        # locale stuff
        try:
            locale.setlocale(locale.LC_ALL, (lang, charset))
        except (locale.Error, IOError):
            locale.setlocale(locale.LC_ALL, None)
        (self.language, self.charset) = locale.getlocale()
        self.language = self.language or "C"
        try:
            self.charset = self.charset or locale.getpreferredencoding()
        except locale.Error:
            self.charset = sys.getfilesystemencoding()

        # Dirty hack : if the charset is ASCII, we can safely use UTF-8 instead
        # This has the advantage of allowing transparent support for recent
        # versions of CUPS which (en-)force charset to UTF-8 when printing.
        # This should be needed only when printing, but is probably (?) safe
        # to do when using interactive commands.
        if self.charset.upper() in ('ASCII', 'ANSI_X3.4-1968'):
            self.charset = "UTF-8"

        # translation stuff
        try:
            try:
                trans = gettext.translation("pykota", languages=[f"{self.language}.{self.charset}"],
                                            codeset=self.charset)
            except TypeError:  # Python <2.4
                trans = gettext.translation("pykota", languages=[f"{self.language}.{self.charset}"])
            trans.install()
        except:
            gettext.NullTranslations().install()

        # pykota specific stuff
        self.documentation = doc

    def deferredInit(self):
        """Deferred initialization."""
        confdir = os.environ.get("PYKOTA_HOME")
        environHome = True
        missingUser = False
        if confdir is None:
            environHome = False
            # check for config files in the 'pykota' user's home directory.
            try:
                self.pykotauser = pwd.getpwnam("pykota")
                confdir = self.pykotauser[5]
            except KeyError:
                self.pykotauser = None
                confdir = "/etc/pykota"
                missingUser = True

        self.config = config.PyKotaConfig(confdir)
        self.debug = self.config.get_debug()
        self.smtpserver = self.config.get_smtp_server()
        self.maildomain = self.config.get_mail_domain()
        self.logger = logger.open_logger(self.config.get_logging_backend())
        # now drop priviledge if possible
        self.dropPriv()
        # We NEED this here, even when not in an accounting filter/backend    
        self.softwareJobSize = 0
        self.softwareJobPrice = 0.0

        if environHome:
            self.printInfo(f"PYKOTA_HOME environment variable is set. Configuration files were searched in {confdir}",
                           "info")
        else:
            if missingUser:
                self.printInfo(
                    f"The 'pykota' system account is missing. Configuration files were searched in {confdir} instead.",
                    "warn")

        self.logdebug(f"Language in use : {self.language}")
        self.logdebug(f"Charset in use : {self.charset}")

        arguments = " ".join([f'"{arg}"' for arg in sys.argv])
        self.logdebug(f"Command line arguments : {arguments}")
    def dropPriv(self):
        """Drops priviledges."""
        uid = os.geteuid()
        try:
            self.originalUserName = pwd.getpwuid(uid)[0]
        except (KeyError, IndexError) as msg:
            self.printInfo(f"Strange problem with uid({uid}) : {msg}", "warn")
            self.originalUserName = None
        else:
            if uid:
                self.logdebug(f"Running as user '{self.originalUserName}'.")
            else:
                if self.pykotauser is None:
                    self.logdebug("No user named 'pykota'. Not dropping priviledges.")
                else:
                    try:
                        os.setegid(self.pykotauser[3])
                        os.seteuid(self.pykotauser[2])
                    except OSError as msg:
                        self.printInfo(f"Impossible to drop priviledges : {msg}", "warn")
                    else:
                        self.logdebug("Priviledges dropped. Now running as user 'pykota'.")
                        self.privdropped = 1

    def regainPriv(self):
        """Drops priviledges."""
        if self.privdropped:
            try:
                os.seteuid(0)
                os.setegid(0)
            except OSError as msg:
                self.printInfo(f"Impossible to regain priviledges : {msg}", "warn")
            else:
                self.logdebug("Regained priviledges. Now running as root.")
                self.privdropped = 0

    def UTF8ToUserCharset(self, text):
        """Converts from UTF-8 to user's charset."""
        if text is None:
            return None
        try:
            return text.decode("UTF-8").encode(self.charset, "replace")
        except (UnicodeError, AttributeError):
            try:
                # Maybe already in Unicode ?
                # return text.encode(self.charset, "replace")
                return text.encode(self.charset, "replace").decode("UTF-8")
            except (UnicodeError, AttributeError):
                # Try to autodetect the charset
                # return text.decode(detectCharset(text), "replace").encode(self.charset, "replace")
                return text.decode(detectCharset(text), "replace")

    def userCharsetToUTF8(self, text):
        """Converts from user's charset to UTF-8."""
        if text is None:
            return None
        try:
            # We don't necessarily trust the default charset, because
            # xprint sends us titles in UTF-8 but CUPS gives us an ISO-8859-1 charset !
            # So we first try to see if the text is already in UTF-8 or not, and
            # if it is, we delete characters which can't be converted to the user's charset,
            # then convert back to UTF-8. PostgreSQL 7.3.x used to reject some unicode characters,
            # this is fixed by the ugly line below :
            #
            # return text.decode("UTF-8").encode(self.charset, "replace").decode(self.charset).encode("UTF-8",
            # "replace")
            return text.decode("UTF-8").encode(self.charset, "replace").decode(self.charset)
        except (UnicodeError, AttributeError):
            try:
                # return text.decode(self.charset).encode("UTF-8", "replace")
                return text.decode(self.charset)
            except (UnicodeError, AttributeError):
                try:
                    # Maybe already in Unicode ?
                    # return text.encode("UTF-8", "replace")
                    return text.encode("UTF-8", "replace").decode("UTF-8")
                except (UnicodeError, AttributeError):
                    # Try to autodetect the charset
                    # return text.decode(detectCharset(text), "replace").encode("UTF-8", "replace")
                    return text.decode(detectCharset(text), "replace")
        return newtext

    def display(self, message):
        """Display a message but only if stdout is a tty."""
        if sys.stdout.isatty():
            sys.stdout.write(message)
            sys.stdout.flush()

    def logdebug(self, message):
        """Logs something to debug output if debug is enabled."""
        if self.debug:
            self.logger.log_message(message, "debug")

    def printInfo(self, message, level="info"):
        """Sends a message to standard error."""
        sys.stderr.write(f"{level.upper()}: {message}\n")
        sys.stderr.flush()

    def matchString(self, s, patterns):
        """Returns True if the string s matches one of the patterns, else False."""
        if not patterns:
            return True  # No pattern, always matches.
        else:
            for pattern in patterns:
                if fnmatch.fnmatchcase(s, pattern):
                    return True
            return False

    def sanitizeNames(self, options, names):
        """Ensures that an user can only see the datas he is allowed to see, by modifying the list of names."""
        if not self.config.isAdmin:
            username = pwd.getpwuid(os.geteuid())[0]
            if not options["list"]:
                raise PyKotaCommandLineError(f'{username} : You are not allowed to use this command.')
            else:
                if options["groups"]:
                    user = self.storage.getUser(username)
                    if user.Exists:
                        return [g.Name for g in self.storage.getUserGroups(user)]
                return [username]
        elif not names:
            return ["*"]
        else:
            return names

    def display_version_and_quit(self):
        """Displays version number, then exists successfully."""
        try:
            self.clean()
        except AttributeError:
            pass
        print(__version__)
        sys.exit(0)

    def display_usage_and_quit(self):
        """Displays command line usage, then exists successfully."""
        try:
            self.clean()
        except AttributeError:
            pass
        print(self.documentation % globals())
        print(__gplblurb__)
        print()
        print(f"Please report bugs to :{__author__}")
        sys.exit(0)

    def crashed(self, message="Bug in PyKota"):
        """Outputs a crash message, and optionally sends it to software author."""
        msg = crashed(message)
        fullmessage = "========== Traceback :\n\n{}\n\n========== sys.argv :\n\n{}\n\n========== Environment :\n\n{}\n".format(
            msg, "\n".join([f"    {repr(a)}" for a in sys.argv]),
            "\n".join([f"    {k}={v}" for (k, v) in os.environ.items()]))
        try:
            crashrecipient = self.config.get_crash_recipient()
            if crashrecipient:
                admin = self.config.get_admin_mail("global")  # Nice trick, isn't it ?
                server = smtplib.SMTP(self.smtpserver)
                msg = text.MIMEText(fullmessage, _charset=self.charset)
                msg["Subject"] = Header(f"PyKota v{__version__} crash traceback !", charset=self.charset)
                msg["From"] = admin
                msg["To"] = crashrecipient
                msg["Cc"] = admin
                msg["Date"] = email.utils.formatdate(localtime=True)
                server.sendmail(admin, [admin, crashrecipient], msg.as_string())
                server.quit()
        except:
            pass
        return fullmessage

    def parseCommandline(self, argv, short, long, allownothing=0):
        """Parses the command line, controlling options."""
        # split options in two lists: those which need an argument, those which don't need any
        short = f"{short}A:"
        long.append("arguments=")
        withoutarg = []
        witharg = []
        lgs = len(short)
        i = 0
        while i < lgs:
            ii = i + 1
            if (ii < lgs) and (short[ii] == ':'):
                # needs an argument
                witharg.append(short[i])
                ii = ii + 1  # skip the ':'
            else:
                # doesn't need an argument
                withoutarg.append(short[i])
            i = ii

        for option in long:
            if option[-1] == '=':
                # needs an argument
                witharg.append(option[:-1])
            else:
                # doesn't need an argument
                withoutarg.append(option)

        # then we parse the command line
        done = 0
        while not done:
            # we begin with all possible options unset
            parsed = {}
            for option in withoutarg + witharg:
                parsed[option] = None
            args = []  # to not break if something unexpected happened
            try:
                options, args = getopt.getopt(argv, short, long)
                if options:
                    for (o, v) in options:
                        # we skip the '-' chars
                        lgo = len(o)
                        i = 0
                        while (i < lgo) and (o[i] == '-'):
                            i = i + 1
                        o = o[i:]
                        if o in witharg:
                            # needs an argument : set it
                            parsed[o] = v
                        elif o in withoutarg:
                            # doesn't need an argument : boolean
                            parsed[o] = 1
                        else:
                            # should never occur
                            raise PyKotaCommandLineError("Unexpected problem when parsing command line")
                elif (not args) and (
                        not allownothing) and sys.stdin.isatty():  # no option and no argument, we display help if we are a tty
                    self.display_usage_and_quit()
            except getopt.error as msg:
                raise PyKotaCommandLineError(str(msg))
            else:
                if parsed["arguments"] or parsed["A"]:
                    # arguments are in a file, we ignore all other arguments
                    # and reset the list of arguments to the lines read from
                    # the file.
                    argsfile = open(parsed["arguments"] or parsed["A"], "r")
                    argv = [l.strip() for l in argsfile.readlines()]
                    argsfile.close()
                    for i in range(len(argv)):
                        argi = argv[i]
                        if argi.startswith('"') and argi.endswith('"'):
                            argv[i] = argi[1:-1]
                else:
                    done = 1
        return (parsed, args)


class PyKotaTool(Tool):
    """Base class for all PyKota command line tools."""

    def __init__(self, lang="", charset=None, doc="PyKota v%(__version__)s (c) %(__years__)s %(__author__)s"):
        """Initializes the command line tool and opens the database."""
        Tool.__init__(self, lang, charset, doc)

    def deferredInit(self):
        """Deferred initialization."""
        Tool.deferredInit(self)
        self.storage = storage.openConnection(self)
        if self.config.isAdmin:  # TODO : We don't know this before, fix this !
            self.logdebug("Beware : running as a PyKota administrator !")
        else:
            self.logdebug("Don't Panic : running as a mere mortal !")

    def clean(self):
        """Ensures that the database is closed."""
        try:
            self.storage.close()
        except (TypeError, NameError, AttributeError):
            pass

    def isValidName(self, name):
        """Checks if a user or printer name is valid."""
        invalidchars = "/@?*,;&|"
        for c in list(invalidchars):
            if c in name:
                return 0
        return 1

    def sendMessage(self, adminmail, touser, fullmessage):
        """Sends an email message containing headers to some user."""
        try:
            server = smtplib.SMTP(self.smtpserver)
        except socket.error as msg:
            self.printInfo(f"Impossible to connect to SMTP server : {msg}", "error")
        else:
            try:
                server.sendmail(adminmail, [touser], fullmessage)
            except smtplib.SMTPException as answer:
                for (k, v) in answer.recipients.items():
                    self.printInfo(f"Impossible to send mail to {k}, error {v[0]} : {v[1]}", "error")
            server.quit()

    def sendMessageToUser(self, admin, adminmail, user, subject, message):
        """Sends an email message to a user."""
        message += f"\n\nPlease contact your system administrator :\n\n\t{admin} - <{adminmail}>\n"
        usermail = user.Email or user.Name
        if "@" not in usermail:
            usermail = f"{usermail}@{self.maildomain or self.smtpserver or 'localhost'}"
        msg = text.MIMEText(message, _charset=self.charset)
        msg["Subject"] = Header(subject, charset=self.charset)
        msg["From"] = adminmail
        msg["To"] = usermail
        msg["Date"] = email.utils.formatdate(localtime=True)
        self.sendMessage(adminmail, usermail, msg.as_string())

    def sendMessageToAdmin(self, adminmail, subject, message):
        """Sends an email message to the Print Quota administrator."""
        if "@" not in adminmail:
            adminmail = "%s@%s" % (adminmail, self.maildomain or self.smtpserver or "localhost")
        msg = text.MIMEText(message, _charset=self.charset)
        msg["Subject"] = Header(subject, charset=self.charset)
        msg["From"] = adminmail
        msg["To"] = adminmail
        self.sendMessage(adminmail, adminmail, msg.as_string())

    def _checkUserPQuota(self, userpquota):
        """Checks the user quota on a printer and deny or accept the job."""
        # then we check the user's own quota
        # if we get there we are sure that policy is not EXTERNAL
        user = userpquota.User
        printer = userpquota.Printer
        enforcement = self.config.get_printer_enforcement(printer.Name)
        self.logdebug(f"Checking user {user.Name}'s quota on printer {printer.Name}")
        (policy, dummy) = self.config.get_printer_policy(userpquota.Printer.Name)
        if not userpquota.Exists:
            # Unknown userquota 
            if policy == "ALLOW":
                action = "POLICY_ALLOW"
            else:
                action = "POLICY_DENY"
            self.printInfo(
                f"Unable to match user {user.Name} on printer {printer.Name}, applying default policy ({action})")
        else:
            pagecounter = int(userpquota.PageCounter or 0)
            if enforcement == "STRICT":
                pagecounter += self.softwareJobSize
            if userpquota.SoftLimit is not None:
                softlimit = int(userpquota.SoftLimit)
                if pagecounter < softlimit:
                    action = "ALLOW"
                else:
                    if userpquota.HardLimit is None:
                        # only a soft limit, this is equivalent to having only a hard limit
                        action = "DENY"
                    else:
                        hardlimit = int(userpquota.HardLimit)
                        if softlimit <= pagecounter < hardlimit:
                            now = datetime.now()
                            if userpquota.DateLimit is not None:
                                # datelimit = DateTime.ISO.ParseDateTime(str(userpquota.DateLimit)[:19])
                                datelimit = datetime.fromisoformat(str(userpquota.DateLimit)[:19])
                            else:
                                datelimit = now + self.config.get_grace_delay(printer.Name)
                                userpquota.setDateLimit(datelimit)
                            if now < datelimit:
                                action = "WARN"
                            else:
                                action = "DENY"
                        else:
                            action = "DENY"
            else:
                if userpquota.HardLimit is not None:
                    # no soft limit, only a hard one.
                    hardlimit = int(userpquota.HardLimit)
                    if pagecounter < hardlimit:
                        action = "ALLOW"
                    else:
                        action = "DENY"
                else:
                    # Both are unset, no quota, i.e. accounting only
                    action = "ALLOW"
        return action

    def checkGroupPQuota(self, grouppquota):
        """Checks the group quota on a printer and deny or accept the job."""
        group = grouppquota.Group
        printer = grouppquota.Printer
        enforcement = self.config.get_printer_enforcement(printer.Name)
        self.logdebug(f"Checking group {group.Name}'s quota on printer {printer.Name}")
        if group.LimitBy and (group.LimitBy.lower() == "balance"):
            val = group.AccountBalance or 0.0
            if enforcement == "STRICT":
                val -= self.softwareJobPrice  # use precomputed size.
            balancezero = self.config.get_balance_zero()
            if val <= balancezero:
                action = "DENY"
            elif val <= self.config.get_poor_man():
                action = "WARN"
            else:
                action = "ALLOW"
            if (enforcement == "STRICT") and (val == balancezero):
                action = "WARN"  # we can still print until account is 0
        else:
            val = grouppquota.PageCounter or 0
            if enforcement == "STRICT":
                val += int(
                    self.softwareJobSize)  # TODO : this is not a fix, problem is elsewhere in grouppquota.PageCounter
            if grouppquota.SoftLimit is not None:
                softlimit = int(grouppquota.SoftLimit)
                if val < softlimit:
                    action = "ALLOW"
                else:
                    if grouppquota.HardLimit is None:
                        # only a soft limit, this is equivalent to having only a hard limit
                        action = "DENY"
                    else:
                        hardlimit = int(grouppquota.HardLimit)
                        if softlimit <= val < hardlimit:
                            now = datetime.now()
                            if grouppquota.DateLimit is not None:
                                # datelimit = DateTime.ISO.ParseDateTime(str(grouppquota.DateLimit)[:19])
                                datelimit = datetime.fromisoformat(str(grouppquota.DateLimit)[:19])
                            else:
                                datelimit = now + self.config.get_grace_delay(printer.Name)
                                grouppquota.setDateLimit(datelimit)
                            if now < datelimit:
                                action = "WARN"
                            else:
                                action = "DENY"
                        else:
                            action = "DENY"
            else:
                if grouppquota.HardLimit is not None:
                    # no soft limit, only a hard one.
                    hardlimit = int(grouppquota.HardLimit)
                    if val < hardlimit:
                        action = "ALLOW"
                    else:
                        action = "DENY"
                else:
                    # Both are unset, no quota, i.e. accounting only
                    action = "ALLOW"
        return action

    def checkUserPQuota(self, userpquota):
        """Checks the user quota on a printer and all its parents and deny or accept the job."""
        user = userpquota.User
        printer = userpquota.Printer

        # indicates that a warning needs to be sent
        warned = 0

        # first we check any group the user is a member of
        for group in self.storage.getUserGroups(user):
            # No need to check anything if the group is in noquota mode
            if group.LimitBy != "noquota":
                grouppquota = self.storage.getGroupPQuota(group, printer)
                # for the printer and all its parents
                for gpquota in [grouppquota] + grouppquota.ParentPrintersGroupPQuota:
                    if gpquota.Exists:
                        action = self.checkGroupPQuota(gpquota)
                        if action == "DENY":
                            return action
                        elif action == "WARN":
                            warned = 1

        # Then we check the user's account balance
        # if we get there we are sure that policy is not EXTERNAL
        (policy, dummy) = self.config.get_printer_policy(printer.Name)
        if user.LimitBy and (user.LimitBy.lower() == "balance"):
            self.logdebug(f"Checking account balance for user {user.Name}")
            if user.AccountBalance is None:
                if policy == "ALLOW":
                    action = "POLICY_ALLOW"
                else:
                    action = "POLICY_DENY"
                self.printInfo(
                    f"Unable to find user {user.Name}'s account balance, applying default policy ({action}) for printer {printer.Name}")
                return action
            else:
                if user.OverCharge == 0.0:
                    self.printInfo(f"User {user.Name} will not be charged for printing.")
                    action = "ALLOW"
                else:
                    val = float(user.AccountBalance or 0.0)
                    enforcement = self.config.get_printer_enforcement(printer.Name)
                    if enforcement == "STRICT":
                        val -= self.softwareJobPrice  # use precomputed size.
                    balancezero = self.config.get_balance_zero()
                    if val <= balancezero:
                        action = "DENY"
                    elif val <= self.config.get_poor_man():
                        action = "WARN"
                    else:
                        action = "ALLOW"
                    if (enforcement == "STRICT") and (val == balancezero):
                        action = "WARN"  # we can still print until account is 0
                return action
        else:
            # Then check the user quota on current printer and all its parents.                
            policyallowed = 0
            for upquota in [userpquota] + userpquota.ParentPrintersUserPQuota:
                action = self._checkUserPQuota(upquota)
                if action in ("DENY", "POLICY_DENY"):
                    return action
                elif action == "WARN":
                    warned = 1
                elif action == "POLICY_ALLOW":
                    policyallowed = 1
            if warned:
                return "WARN"
            elif policyallowed:
                return "POLICY_ALLOW"
            else:
                return "ALLOW"

    def externalMailTo(self, cmd, action, user, printer, message):
        """Warns the user with an external command."""
        username = user.Name
        printername = printer.Name
        email = user.Email or user.Name
        if "@" not in email:
            email = f"{email}@{self.maildomain or self.smtpserver}"
        os.system(cmd % locals())

    def formatCommandLine(self, cmd, user, printer):
        """Executes an external command."""
        username = user.Name
        printername = printer.Name
        return cmd % locals()

    def warnGroupPQuota(self, grouppquota):
        """Checks a group quota and send messages if quota is exceeded on current printer."""
        group = grouppquota.Group
        printer = grouppquota.Printer
        admin = self.config.get_admin(printer.Name)
        adminmail = self.config.get_admin_mail(printer.Name)
        (mailto, arguments) = self.config.get_mail_to(printer.Name)
        if group.LimitBy in ("noquota", "nochange"):
            action = "ALLOW"
        else:
            action = self.checkGroupPQuota(grouppquota)
            if action.startswith("POLICY_"):
                action = action[7:]
            if action == "DENY":
                adminmessage = f"Print Quota exceeded for group {group.Name} on printer {printer.Name}"
                self.printInfo(adminmessage)
                if mailto in ["BOTH", "ADMIN"]:
                    self.sendMessageToAdmin(adminmail, "Print Quota", adminmessage)
                if mailto in ["BOTH", "USER", "EXTERNAL"]:
                    for user in self.storage.getGroupMembers(group):
                        if mailto != "EXTERNAL":
                            self.sendMessageToUser(admin, adminmail, user, "Print Quota Exceeded",
                                                   self.config.get_hard_warn(printer.Name))
                        else:
                            self.externalMailTo(arguments, action, user, printer,
                                                self.config.get_hard_warn(printer.Name))
            elif action == "WARN":
                adminmessage = f"Print Quota low for group {group.Name}s on printer {printer.Name}"
                self.printInfo(adminmessage)
                if mailto in ["BOTH", "ADMIN"]:
                    self.sendMessageToAdmin(adminmail, "Print Quota", adminmessage)
                if group.LimitBy and (group.LimitBy.lower() == "balance"):
                    message = self.config.get_poor_warn()
                else:
                    message = self.config.get_soft_warn(printer.Name)
                if mailto in ["BOTH", "USER", "EXTERNAL"]:
                    for user in self.storage.getGroupMembers(group):
                        if mailto != "EXTERNAL":
                            self.sendMessageToUser(admin, adminmail, user, "Print Quota Exceeded", message)
                        else:
                            self.externalMailTo(arguments, action, user, printer, message)
        return action

    def warnUserPQuota(self, userpquota):
        """Checks a user quota and send him a message if quota is exceeded on current printer."""
        user = userpquota.User
        printer = userpquota.Printer
        admin = self.config.get_admin(printer.Name)
        adminmail = self.config.get_admin_mail(printer.Name)
        (mailto, arguments) = self.config.get_mail_to(printer.Name)

        if user.LimitBy in ("noquota", "nochange"):
            action = "ALLOW"
        elif user.LimitBy == "noprint":
            action = "DENY"
            message = f"User {user.Name} is not allowed to print at this time."
            self.printInfo(message)
            if mailto in ["BOTH", "USER", "EXTERNAL"]:
                if mailto != "EXTERNAL":
                    self.sendMessageToUser(admin, adminmail, user, "Printing denied.", message)
                else:
                    self.externalMailTo(arguments, action, user, printer, message)
            if mailto in ["BOTH", "ADMIN"]:
                self.sendMessageToAdmin(adminmail, "Print Quota", message)
        else:
            action = self.checkUserPQuota(userpquota)
            if action.startswith("POLICY_"):
                action = action[7:]

            if action == "DENY":
                adminmessage = f"Print Quota exceeded for user {user.Name} on printer {printer.Name}"
                self.printInfo(adminmessage)
                if mailto in ["BOTH", "USER", "EXTERNAL"]:
                    message = self.config.get_hard_warn(printer.Name)
                    if mailto != "EXTERNAL":
                        self.sendMessageToUser(admin, adminmail, user, "Print Quota Exceeded", message)
                    else:
                        self.externalMailTo(arguments, action, user, printer, message)
                if mailto in ["BOTH", "ADMIN"]:
                    self.sendMessageToAdmin(adminmail, "Print Quota", adminmessage)
            elif action == "WARN":
                adminmessage = f"Print Quota low for user {user.Name} on printer {printer.Name}"
                self.printInfo(adminmessage)
                if mailto in ["BOTH", "USER", "EXTERNAL"]:
                    if user.LimitBy and (user.LimitBy.lower() == "balance"):
                        message = self.config.get_poor_warn()
                    else:
                        message = self.config.get_soft_warn(printer.Name)
                    if mailto != "EXTERNAL":
                        self.sendMessageToUser(admin, adminmail, user, "Print Quota Low", message)
                    else:
                        self.externalMailTo(arguments, action, user, printer, message)
                if mailto in ["BOTH", "ADMIN"]:
                    self.sendMessageToAdmin(adminmail, "Print Quota", adminmessage)
        return action
