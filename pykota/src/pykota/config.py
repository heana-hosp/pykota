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
# $Id: config.py 3190 2007-06-20 19:22:27Z jerome $
#
#

"""This module defines classes used to parse PyKota configuration files."""

import os
import tempfile
import configparser


class PyKotaConfigError(Exception):
    """An exception for PyKota config related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class PyKotaConfig:
    """A class to deal with PyKota's configuration."""

    def __init__(self, directory):
        """Reads and checks the configuration file."""
        self.isAdmin = 0
        self.directory = directory
        self.filename = os.path.join(directory, "pykota.conf")
        self.adminfilename = os.path.join(directory, "pykotadmin.conf")
        if not os.access(self.filename, os.R_OK):
            raise PyKotaConfigError(
                f"Configuration file {self.filename} can't be read. Please check that the file exists and that your "
                f"permissions are sufficient.")
        if not os.path.isfile(self.adminfilename):
            raise PyKotaConfigError(f"Configuration file {self.adminfilename} not found.")
        if os.access(self.adminfilename, os.R_OK):
            self.isAdmin = 1
        self.config = configparser.ConfigParser()
        self.config.read([self.filename], encoding='ISO-8859-2')

    def is_true(self, option):
        """Returns True if option is set to true, else False."""
        if (option is not None) and (option.strip().upper() in ['Y', 'YES', '1', 'ON', 'T', 'TRUE']):
            return True
        else:
            return False

    def is_false(self, option):
        """Returns True if option is set to false, else False."""
        if (option is not None) and (option.strip().upper() in ['N', 'NO', '0', 'OFF', 'F', 'FALSE']):
            return True
        else:
            return False

    def get_printer_names(self):
        """Returns the list of configured printers, i.e. all sections names minus 'global'."""
        return [pname for pname in self.config.sections() if pname != "global"]

    def get_global_option(self, option, ignore=0):
        """Returns an option from the global section, or raises a PyKotaConfigError if ignore is not set,
        else returns None. """
        try:
            return self.config.get("global", option, raw=True)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if ignore:
                return None
            else:
                raise PyKotaConfigError(f"Option {option} not found in section global of {self.filename}")

    def get_printer_option(self, printername, option):
        """Returns an option from the printer section, or the global section, or raises a PyKotaConfigError."""
        globaloption = self.get_global_option(option, ignore=1)
        try:
            return self.config.get(printername, option, raw=True)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if globaloption is not None:
                return globaloption
            else:
                raise PyKotaConfigError(f"Option {option} not found in section {printername} of {self.filename}")

    def get_storage_backend(self):
        """Returns the storage backend information as a Python mapping."""
        backendinfo = {}
        backend = self.get_global_option("storagebackend").lower()
        backendinfo["storagebackend"] = backend
        if backend == "sqlitestorage":
            issqlite = 1
            backendinfo["storagename"] = self.get_global_option("storagename")
            for option in ["storageserver", "storageuser", "storageuserpw"]:
                backendinfo[option] = None
        else:
            issqlite = 0
            for option in ["storageserver", "storagename", "storageuser"]:
                backendinfo[option] = self.get_global_option(option)
            backendinfo["storageuserpw"] = self.get_global_option("storageuserpw", ignore=1)  # password is optional

        backendinfo["storageadmin"] = None
        backendinfo["storageadminpw"] = None
        if self.isAdmin:
            adminconf = configparser.ConfigParser()
            adminconf.read([self.adminfilename])
            if adminconf.sections():  # were we able to read the file ?
                try:
                    backendinfo["storageadmin"] = adminconf.get("global", "storageadmin", raw=True)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    if not issqlite:
                        raise PyKotaConfigError(
                            f"Option storageadmin not found in section global of {self.adminfilename}")
                try:
                    backendinfo["storageadminpw"] = adminconf.get("global", "storageadminpw", raw=True)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass  # Password is optional
                # Now try to overwrite the storagebackend, storageserver 
                # and storagename. This allows admins to use the master LDAP
                # server directly and users to use the replicas transparently.
                try:
                    backendinfo["storagebackend"] = adminconf.get("global", "storagebackend", raw=True)
                except configparser.NoOptionError:
                    pass
                try:
                    backendinfo["storageserver"] = adminconf.get("global", "storageserver", raw=True)
                except configparser.NoOptionError:
                    pass
                try:
                    backendinfo["storagename"] = adminconf.get("global", "storagename", raw=True)
                except configparser.NoOptionError:
                    pass
        return backendinfo

    def get_ldap_info(self):
        """Returns some hints for the LDAP backend."""
        ldapinfo = {}
        for option in ["userbase", "userrdn",
                       "balancebase", "balancerdn",
                       "groupbase", "grouprdn", "groupmembers",
                       "printerbase", "printerrdn",
                       "userquotabase", "groupquotabase",
                       "jobbase", "lastjobbase", "billingcodebase",
                       "newuser", "newgroup",
                       "usermail",
                       ]:
            ldapinfo[option] = self.get_global_option(option).strip()
        for field in ["newuser", "newgroup"]:
            if ldapinfo[field].lower().startswith('attach('):
                ldapinfo[field] = ldapinfo[field][7:-1]

        # should we use TLS, by default (if unset) value is NO        
        ldapinfo["ldaptls"] = self.is_true(self.get_global_option("ldaptls", ignore=1))
        ldapinfo["cacert"] = self.get_global_option("cacert", ignore=1)
        if ldapinfo["cacert"]:
            ldapinfo["cacert"] = ldapinfo["cacert"].strip()
        if ldapinfo["ldaptls"]:
            if not os.access(ldapinfo["cacert"] or "", os.R_OK):
                raise PyKotaConfigError(
                    f"Option ldaptls is set, but certificate {str(ldapinfo['cacert'])} is not readable.")
        return ldapinfo

    def get_logging_backend(self):
        """Returns the logging backend information."""
        validloggers = ["stderr", "system"]
        try:
            logger = self.get_global_option("logger").lower()
        except PyKotaConfigError:
            logger = "system"
        if logger not in validloggers:
            raise PyKotaConfigError(f"Option logger only supports values in {str(validloggers)}")
        return logger

    def get_logo_url(self):
        """Returns the URL to use for the logo in the CGI scripts."""
        url = self.get_global_option("logourl", ignore=1) or \
              "http://www.pykota.com/pykota.png"
        return url.strip()

    def get_logo_link(self):
        """Returns the URL to go to when the user clicks on the logo in the CGI scripts."""
        url = self.get_global_option("logolink", ignore=1) or \
              "http://www.pykota.com/"
        return url.strip()

    def get_pre_accounter_backend(self, printername):
        """Returns the preaccounter backend to use for a given printer."""
        validaccounters = ["software", "ink"]
        try:
            fullaccounter = self.get_printer_option(printername, "preaccounter").strip()
        except PyKotaConfigError:
            return ("software", "")
        else:
            flower = fullaccounter.lower()
            for vac in validaccounters:
                if flower.startswith(vac):
                    try:
                        (accounter, args) = [x.strip() for x in fullaccounter.split('(', 1)]
                    except ValueError:
                        raise PyKotaConfigError(f"Invalid preaccounter {fullaccounter} for printer {printername}")
                    if args.endswith(')'):
                        args = args[:-1].strip()
                    if (vac == "ink") and not args:
                        raise PyKotaConfigError(f"Invalid preaccounter {fullaccounter} for printer {printername}")
                    return (vac, args)
            raise PyKotaConfigError(
                f"Option preaccounter in section {printername} only supports values in {str(validaccounters)}")

    def get_accounter_backend(self, printername):
        """Returns the accounter backend to use for a given printer."""
        validaccounters = ["hardware", "software", "ink"]
        try:
            fullaccounter = self.get_printer_option(printername, "accounter").strip()
        except PyKotaConfigError:
            return ("software", "")
        else:
            flower = fullaccounter.lower()
            for vac in validaccounters:
                if flower.startswith(vac):
                    try:
                        (accounter, args) = [x.strip() for x in fullaccounter.split('(', 1)]
                    except ValueError:
                        raise PyKotaConfigError(f"Invalid accounter {fullaccounter} for printer {printername}")
                    if args.endswith(')'):
                        args = args[:-1].strip()
                    if (vac in ("hardware", "ink")) and not args:
                        raise PyKotaConfigError(f"Invalid accounter {fullaccounter} for printer {printername}")
                    return (vac, args)
            raise PyKotaConfigError(
                f"Option accounter in section {printername} only supports values in {str(validaccounters)}")

    def get_pre_hook(self, printername):
        """Returns the prehook command line to launch, or None if unset."""
        try:
            return self.get_printer_option(printername, "prehook").strip()
        except PyKotaConfigError:
            return  # No command to launch in the pre-hook

    def get_post_hook(self, printername):
        """Returns the posthook command line to launch, or None if unset."""
        try:
            return self.get_printer_option(printername, "posthook").strip()
        except PyKotaConfigError:
            return  # No command to launch in the post-hook

    def get_strip_title(self, printername):
        """Returns the striptitle directive's content, or None if unset."""
        try:
            return self.get_printer_option(printername, "striptitle").strip()
        except PyKotaConfigError:
            return  # No prefix to strip off

    def get_ask_confirmation(self, printername):
        """Returns the askconfirmation directive's content, or None if unset."""
        try:
            return self.get_printer_option(printername, "askconfirmation").strip()
        except PyKotaConfigError:
            return  # No overwriting will be done

    def get_overwrite_job_ticket(self, printername):
        """Returns the overwrite_jobticket directive's content, or None if unset."""
        try:
            return self.get_printer_option(printername, "overwrite_jobticket").strip()
        except PyKotaConfigError:
            return  # No overwriting will be done

    def get_unknown_billing_code(self, printername):
        """Returns the unknown_billingcode directive's content, or the default value if unset."""
        validvalues = ["CREATE", "DENY"]
        try:
            fullvalue = self.get_printer_option(printername, "unknown_billingcode")
        except PyKotaConfigError:
            return ("CREATE", None)
        else:
            try:
                value = [x.strip() for x in fullvalue.split('(', 1)]
            except ValueError:
                raise PyKotaConfigError(f"Invalid unknown_billingcode directive {fullvalue} for printer {printername}")
            if len(value) == 1:
                value.append("")
            (value, args) = value
            if args.endswith(')'):
                args = args[:-1]
            value = value.upper()
            if (value == "DENY") and not args:
                return ("DENY", None)
            if value not in validvalues:
                raise PyKotaConfigError(
                    f"Directive unknown_billingcode in section {printername} only supports values in {str(validvalues)}")
            return (value, args)

    def get_printer_enforcement(self, printername):
        """Returns if quota enforcement should be strict or laxist for the current printer."""
        validenforcements = ["STRICT", "LAXIST"]
        try:
            enforcement = self.get_printer_option(printername, "enforcement")
        except PyKotaConfigError:
            return "LAXIST"
        else:
            enforcement = enforcement.upper()
            if enforcement not in validenforcements:
                raise PyKotaConfigError(
                    f"Option enforcement in section {printername} only supports values in {str(validenforcements)}")
            return enforcement

    def get_printer_on_backend_error(self, printername):
        """Returns what must be done whenever the real CUPS backend fails."""
        validactions = ["CHARGE", "NOCHARGE"]
        try:
            action = self.get_printer_option(printername, "onbackenderror")
        except PyKotaConfigError:
            return ["NOCHARGE"]
        else:
            action = action.upper().split(",")
            error = False
            for act in action:
                if act not in validactions:
                    if act.startswith("RETRY:"):
                        try:
                            (num, delay) = [int(p) for p in act[6:].split(":", 2)]
                        except ValueError:
                            error = True
                    else:
                        error = True
            if error:
                raise PyKotaConfigError(
                    f"Option onbackenderror in section {printername} only supports values 'charge', 'nocharge', and 'retry:num:delay'")
            return action

    def get_printer_on_accounter_error(self, printername):
        """Returns what must be done whenever the accounter fails."""
        validactions = ["CONTINUE", "STOP"]
        try:
            action = self.get_printer_option(printername, "onaccountererror")
        except PyKotaConfigError:
            return "STOP"
        else:
            action = action.upper()
            if action not in validactions:
                raise PyKotaConfigError(
                    f"Option onaccountererror in section {printername} only supports values in {str(validactions)}")
            return action

    def get_printer_policy(self, printername):
        """Returns the default policy for the current printer."""
        validpolicies = ["ALLOW", "DENY", "EXTERNAL"]
        try:
            fullpolicy = self.get_printer_option(printername, "policy")
        except PyKotaConfigError:
            return ("DENY", None)
        else:
            try:
                policy = [x.strip() for x in fullpolicy.split('(', 1)]
            except ValueError:
                raise PyKotaConfigError(f"Invalid policy {fullpolicy} for printer {printername}")
            if len(policy) == 1:
                policy.append("")
            (policy, args) = policy
            if args.endswith(')'):
                args = args[:-1]
            policy = policy.upper()
            if (policy == "EXTERNAL") and not args:
                raise PyKotaConfigError(f"Invalid policy {fullpolicy} for printer {printername}")
            if policy not in validpolicies:
                raise PyKotaConfigError(
                    f"Option policy in section {printername} only supports values in {str(validpolicies)}")
            return (policy, args)

    def get_crash_recipient(self):
        """Returns the email address of the software crash messages recipient."""
        try:
            return self.get_global_option("crashrecipient")
        except:
            return

    def get_smtp_server(self):
        """Returns the SMTP server to use to send messages to users."""
        try:
            return self.get_global_option("smtpserver")
        except PyKotaConfigError:
            return "localhost"

    def get_mail_domain(self):
        """Returns the mail domain to use to send messages to users."""
        try:
            return self.get_global_option("maildomain")
        except PyKotaConfigError:
            return

    def get_admin_mail(self, printername):
        """Returns the Email address of the Print Quota Administrator."""
        try:
            return self.get_printer_option(printername, "adminmail")
        except PyKotaConfigError:
            return "root@localhost"

    def get_admin(self, printername):
        """Returns the full name of the Print Quota Administrator."""
        try:
            return self.get_printer_option(printername, "admin")
        except PyKotaConfigError:
            return "root"

    def get_mail_to(self, printername):
        """Returns the recipient of email messages."""
        validmailtos = ["EXTERNAL", "NOBODY", "NONE", "NOONE", "BITBUCKET", "DEVNULL", "BOTH", "USER", "ADMIN"]
        try:
            fullmailto = self.get_printer_option(printername, "mailto")
        except PyKotaConfigError:
            return ("BOTH", None)
        else:
            try:
                mailto = [x.strip() for x in fullmailto.split('(', 1)]
            except ValueError:
                raise PyKotaConfigError(f"Invalid option mailto {fullmailto} for printer {printername}")
            if len(mailto) == 1:
                mailto.append("")
            (mailto, args) = mailto
            if args.endswith(')'):
                args = args[:-1]
            mailto = mailto.upper()
            if (mailto == "EXTERNAL") and not args:
                raise PyKotaConfigError(f"Invalid option mailto {fullmailto} for printer {printername}")
            if mailto not in validmailtos:
                raise PyKotaConfigError(
                    f"Option mailto in section {printername} only supports values in {str(validmailtos)}")
            return (mailto, args)

    def get_max_deny_banners(self, printername):
        """Returns the maximum number of deny banners to be printed for a particular user on a particular printer."""
        try:
            maxdb = self.get_printer_option(printername, "maxdenybanners")
        except PyKotaConfigError:
            return 0  # default value is to forbid printing a deny banner.
        try:
            value = int(maxdb.strip())
            if value < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise PyKotaConfigError(f"Invalid maximal deny banners counter {maxdb}")
        else:
            return value

    def get_print_cancelled_banners(self, printername):
        """Returns True if a banner should be printed when a job is cancelled, else False."""
        try:
            return self.is_true(self.get_printer_option(printername, "printcancelledbanners"))
        except PyKotaConfigError:
            return True

    def get_grace_delay(self, printername):
        """Returns the grace delay in days."""
        try:
            gd = self.get_printer_option(printername, "gracedelay")
        except PyKotaConfigError:
            gd = 7  # default value of 7 days
        try:
            return int(gd)
        except (TypeError, ValueError):
            raise PyKotaConfigError(f"Invalid grace delay {gd}")

    def get_poor_man(self):
        """Returns the poor man's threshold."""
        try:
            pm = self.get_global_option("poorman")
        except PyKotaConfigError:
            pm = 1.0  # default value of 1 unit
        try:
            return float(pm)
        except (TypeError, ValueError):
            raise PyKotaConfigError(f"Invalid poor man's threshold {pm}")

    def get_balance_zero(self):
        """Returns the value of the zero for balance limitation."""
        try:
            bz = self.get_global_option("balancezero")
        except PyKotaConfigError:
            bz = 0.0  # default value, zero is 0.0
        try:
            return float(bz)
        except (TypeError, ValueError):
            raise PyKotaConfigError(f"Invalid balancezero value {bz}")

    def get_poor_warn(self):
        """Returns the poor man's warning message."""
        try:
            return self.get_global_option("poorwarn")
        except PyKotaConfigError:
            return "Your Print Quota account balance is Low.\nSoon you'll not be allowed to print anymore.\nPlease contact the Print Quota Administrator to solve the problem."

    def get_hard_warn(self, printername):
        """Returns the hard limit error message."""
        try:
            return self.get_printer_option(printername, "hardwarn")
        except PyKotaConfigError:
            return f"You are not allowed to print anymore because\nyour Print Quota is exceeded on printer {printername}."

    def get_soft_warn(self, printername):
        """Returns the soft limit error message."""
        try:
            return self.get_printer_option(printername, "softwarn")
        except PyKotaConfigError:
            return f"You will soon be forbidden to print anymore because\nyour Print Quota is almost reached on printer {printername}."

    def get_privacy(self):
        """Returns True if privacy is activated, else False."""
        return self.is_true(self.get_global_option("privacy", ignore=1))

    def get_debug(self):
        """Returns True if debugging is activated, else False."""
        return self.is_true(self.get_global_option("debug", ignore=1))

    def get_caching(self):
        """Returns True if database caching is enabled, else False."""
        return self.is_true(self.get_global_option("storagecaching", ignore=1))

    def get_ldap_cache(self):
        """Returns True if low-level LDAP caching is enabled, else False."""
        return self.is_true(self.get_global_option("ldapcache", ignore=1))

    def get_disable_history(self):
        """Returns True if we want to disable history, else False."""
        return self.is_true(self.get_global_option("disablehistory", ignore=1))

    def get_user_name_to_lower(self):
        """Deprecated."""
        return self.get_global_option("utolower", ignore=1)

    def get_user_name_case(self):
        """Returns value for user name case: upper, lower or native"""
        validvalues = ["upper", "lower", "native"]
        try:
            value = self.get_global_option("usernamecase", ignore=1).strip().lower()
        except AttributeError:
            value = "native"
        if value not in validvalues:
            raise PyKotaConfigError(f"Option usernamecase only supports values in {str(validvalues)}")
        return value

    def get_reject_unknown(self):
        """Returns True if we want to reject the creation of unknown users or groups, else False."""
        return self.is_true(self.get_global_option("reject_unknown", ignore=1))

    def get_printer_keep_files(self, printername):
        """Returns True if files must be kept on disk, else False."""
        try:
            return self.is_true(self.get_printer_option(printername, "keepfiles"))
        except PyKotaConfigError:
            return False

    def get_printer_directory(self, printername):
        """Returns the path to our working directory, else a directory suitable for temporary files."""
        try:
            return self.get_printer_option(printername, "directory").strip()
        except PyKotaConfigError:
            return tempfile.gettempdir()

    def get_deny_duplicates(self, printername):
        """Returns True or a command if we want to deny duplicate jobs, else False."""
        try:
            denyduplicates = self.get_printer_option(printername, "denyduplicates")
        except PyKotaConfigError:
            return False
        else:
            if self.is_true(denyduplicates):
                return True
            elif self.is_false(denyduplicates):
                return False
            else:
                # it's a command to run.
                return denyduplicates

    def get_duplicates_delay(self, printername):
        """Returns the number of seconds after which two identical jobs are not considered a duplicate anymore."""
        try:
            duplicatesdelay = self.get_printer_option(printername, "duplicatesdelay")
        except PyKotaConfigError:
            return 0
        else:
            try:
                return int(duplicatesdelay)
            except (TypeError, ValueError):
                raise PyKotaConfigError(
                    f"Incorrect value {str(duplicatesdelay)} for the duplicatesdelay directive in section {printername}")

    def get_no_printing_max_delay(self, printername):
        """Returns the max number of seconds to wait for the printer to be in 'printing' mode."""
        try:
            maxdelay = self.get_printer_option(printername, "noprintingmaxdelay")
        except PyKotaConfigError:
            return None  # tells to use hardcoded value
        else:
            try:
                maxdelay = int(maxdelay)
                if maxdelay < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise PyKotaConfigError(
                    f"Incorrect value {str(maxdelay)} for the noprintingmaxdelay directive in section {printername}")
            else:
                return maxdelay

    def get_status_stabilization_loops(self, printername):
        """Returns the number of times the printer must return the 'idle' status to consider it stable."""
        try:
            stab = self.get_printer_option(printername, "statusstabilizationloops")
        except PyKotaConfigError:
            return None  # tells to use hardcoded value
        else:
            try:
                stab = int(stab)
                if stab < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise PyKotaConfigError(
                    f"Incorrect value {str(stab)} for the statusstabilizationloops directive in section {printername}")
            else:
                return stab

    def get_status_stabilization_delay(self, printername):
        """Returns the number of seconds to wait between two checks of the printer's status."""
        try:
            stab = self.get_printer_option(printername, "statusstabilizationdelay")
        except PyKotaConfigError:
            return None  # tells to use hardcoded value
        else:
            try:
                stab = float(stab)
                if stab < 0.25:
                    raise ValueError
            except (TypeError, ValueError):
                raise PyKotaConfigError(
                    f"Incorrect value {str(stab)} for the statusstabilizationdelay directive in section {printername}")
            else:
                return stab

    def get_printer_snmp_error_mask(self, printername):
        """Returns the SNMP error mask for a particular printer, or None if not defined."""
        try:
            errmask = self.get_printer_option(printername, "snmperrormask").lower()
        except PyKotaConfigError:
            return None  # tells to use hardcoded value
        else:
            try:
                if errmask.startswith("0x"):
                    value = int(errmask, 16)
                elif errmask.startswith("0"):
                    value = int(errmask, 8)
                else:
                    value = int(errmask)
                if 0 <= value < 65536:
                    return value
                else:
                    raise ValueError
            except ValueError:
                raise PyKotaConfigError(
                    f"Incorrect value {errmask} for the snmperrormask directive in section {printername}")

    def get_winbind_separator(self):
        """Returns the winbind separator's value if it is set, else None."""
        return self.get_global_option("winbind_separator", ignore=1)

    def get_account_banner(self, printername):
        """Returns which banner(s) to account for: NONE, BOTH, STARTING, ENDING."""
        validvalues = ["NONE", "BOTH", "STARTING", "ENDING"]
        try:
            value = self.get_printer_option(printername, "accountbanner")
        except PyKotaConfigError:
            return "BOTH"  # Default value of BOTH
        else:
            value = value.strip().upper()
            if value not in validvalues:
                raise PyKotaConfigError(
                    f"Option accountbanner in section {printername} only supports values in {str(validvalues)}")
            return value

    def get_avoid_duplicate_banners(self, printername):
        """Returns normalized value for avoiding extra banners. """
        try:
            avoidduplicatebanners = self.get_printer_option(printername, "avoidduplicatebanners").upper()
        except PyKotaConfigError:
            return "NO"
        else:
            try:
                value = int(avoidduplicatebanners)
                if value < 0:
                    raise ValueError
            except ValueError:
                if avoidduplicatebanners not in ["YES", "NO"]:
                    raise PyKotaConfigError(
                        "Option avoidduplicatebanners only accepts 'yes', 'no', or a positive integer.")
                else:
                    value = avoidduplicatebanners
            return value

    def get_starting_banner(self, printername):
        """Returns the startingbanner value if set, else None."""
        try:
            return self.get_printer_option(printername, "startingbanner").strip()
        except PyKotaConfigError:
            return None

    def get_ending_banner(self, printername):
        """Returns the endingbanner value if set, else None."""
        try:
            return self.get_printer_option(printername, "endingbanner").strip()
        except PyKotaConfigError:
            return None

    def get_trust_job_size(self, printername):
        """Returns the normalized value of the trustjobsize's directive."""
        try:
            value = self.get_printer_option(printername, "trustjobsize").strip().upper()
        except PyKotaConfigError:
            return (None, "YES")
        else:
            if value == "YES":
                return (None, "YES")
            try:
                (limit, replacement) = [p.strip() for p in value.split(">")[1].split(":")]
                limit = int(limit)
                try:
                    replacement = int(replacement)
                except ValueError:
                    if replacement != "PRECOMPUTED":
                        raise
                if limit < 0:
                    raise ValueError
                if (replacement != "PRECOMPUTED") and (replacement < 0):
                    raise ValueError
            except (IndexError, ValueError, TypeError):
                raise PyKotaConfigError(f"Option trustjobsize for printer {printername} is incorrect")
            return (limit, replacement)

    def get_printer_coefficients(self, printername):
        """Returns a mapping of coefficients for a particular printer."""
        branchbasename = "coefficient_"
        try:
            globalbranches = [(k, self.config.get("global", k)) for k in self.config.options("global") if
                              k.startswith(branchbasename)]
        except configparser.NoSectionError as msg:
            raise PyKotaConfigError(f"Invalid configuration file : {msg}")
        try:
            sectionbranches = [(k, self.config.get(printername, k)) for k in self.config.options(printername) if
                               k.startswith(branchbasename)]
        except configparser.NoSectionError as msg:
            sectionbranches = []
        branches = {}
        for (k, v) in globalbranches:
            k = k.split('_', 1)[1]
            value = v.strip()
            if value:
                try:
                    branches[k] = float(value)
                except ValueError:
                    raise PyKotaConfigError(f"Invalid coefficient {k} ({value}) for printer {printername}")

        for (k, v) in sectionbranches:
            k = k.split('_', 1)[1]
            value = v.strip()
            if value:
                try:
                    branches[k] = float(value)  # overwrite any global option or set a new value
                except ValueError:
                    raise PyKotaConfigError(f"Invalid coefficient {k} ({value}) for printer {printername}")
            else:
                del branches[k]  # empty value disables a global option
        return branches

    def get_printer_skip_initial_wait(self, printername):
        """Returns True if we want to skip the initial waiting loop, else False."""
        try:
            return self.is_true(self.get_printer_option(printername, "skipinitialwait"))
        except PyKotaConfigError:
            return False
