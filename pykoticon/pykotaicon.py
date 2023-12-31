#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-

"""PyKotIcon is a generic, networked, cross-platform dialog box manager."""

# PyKotIcon - Client side helper for PyKota and other applications
#
# (c) 2003, 2004, 2005, 2006 Jerome Alet <alet@librelogiciel.com>
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
#

__version__ = "1.02"
__author__ = "Jerome Alet"
__author_email__ = "alet@librelogiciel.com"
__license__ = "GNU GPL"
__url__ = "http://www.pykota.com/software/pykoticon"
__revision__ = "$Id: pykoticon 117 2020-05-08 21:26:06Z eslijr $"

import sys
import os
import time
import urllib.request, urllib.parse, urllib.error
import locale
import gettext
import socket
import threading
import xmlrpc.client
import xmlrpc.server
import getpass
import wx, wx.adv, wx.aui, wx.core

try :
    import optparse
except ImportError :    
    sys.stderr.write("You need Python v2.3 or higher for PyKotIcon to work.\nAborted.\n")
    sys.exit(-1)

if sys.platform == "win32" :
    isWindows = True
    try :
        import win32api
    except ImportError :    
        raise ImportError("Mark Hammond's Win32 Extensions are missing. Please install them.")
    else :    
        iconsdir = os.path.split(sys.argv[0])[0]
else :        
    isWindows = False
    iconsdir = "/usr/share/pykoticon"   # TODO : change this
    import pwd
    
try :    
    import wx
    hasWxPython = True
except ImportError :    
    hasWxPython = False
    raise ImportError("wxPython is missing. Please install it.")
    
aboutbox = """PyKotIcon v%(__version__)s (c) 2003-2006 %(__author__)s - %(__author_email__)s

PyKotIcon is generic, networked, cross-platform dialog box manager.

It is often used as a client side companion for PyKota, but it
can be used from other applications if you want.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA."""

        
class MyXMLRPCServer(xmlrpc.server.SimpleXMLRPCServer) :
    """My own server class."""
    allow_reuse_address = True
    def __init__(self, frame, options, arguments) :
        xmlrpc.server.SimpleXMLRPCServer.__init__(self, \
                                                       ('0.0.0.0', options.port), \
                                                       xmlrpc.server.SimpleXMLRPCRequestHandler, \
                                                       options.debug)
        self.frame = frame
        self.debug = options.debug
        self.cacheduration = options.cache
        self.cache = {}
        self.printServers = [ socket.gethostbyname(arg) for arg in arguments ]
        if "127.0.0.1" not in self.printServers :
            self.printServers.append("127.0.0.1") # to allow clean shutdown
        loop = threading.Thread(target=self.mainloop)
        loop.start()
        
    def logDebug(self, message) :    
        """Logs a debug message if debug mode is active."""
        if self.debug :
            sys.stderr.write("%s\n" % message)
            
    def getAnswerFromCache(self, key) :
        """Tries to extract a value from the cache and returns it if still valid."""
        cacheentry = self.cache.get(key)
        if cacheentry is not None :
            (birth, value) = cacheentry 
            if (time.time() - birth) < self.cacheduration :
                self.logDebug("Cache hit for %s" % str(key))
                return value # NB : we don't extend the life of this entry
            else :    
                self.logDebug("Cache expired for %s" % str(key))
        else :        
            self.logDebug("Cache miss for %s" % str(key))
        return None
        
    def storeAnswerInCache(self, key, value) :    
        """Stores an entry in the cache."""
        self.cache[key] = (time.time(), value)
        self.logDebug("Cache store for %s" % str(key))
        
    def export_askDatas(self, labels, varnames, varvalues) :
        """Asks some textual datas defined by a list of labels, a list of variables' names and a list of variables values in a mapping."""
        values = {}
        for (key, value) in list(varvalues.items()) :
            values[key] = self.frame.UTF8ToUserCharset(value.data)
        cachekey = tuple(values.items())  
        retcode = self.getAnswerFromCache(cachekey)
        if (retcode is None) or (not retcode["isValid"]) :
            wx.CallAfter(self.frame.askDatas, [ self.frame.UTF8ToUserCharset(label.data) for label in labels ], \
                                              varnames, \
                                              values)
            # ugly, isn't it ?
            while self.frame.dialogAnswer is None :
                time.sleep(0.1)
            retcode = self.frame.dialogAnswer    
            for (key, value) in list(retcode.items()) :
                if key != "isValid" :
                    retcode[key] = xmlrpc.client.Binary(self.frame.userCharsetToUTF8(value))
            self.frame.dialogAnswer = None # prepare for next call, just in case
            self.storeAnswerInCache(cachekey, retcode)
        return retcode
        
    def export_quitApplication(self) :    
        """Makes the application quit."""
        self.frame.quitEvent.set()
        wx.CallAfter(self.frame.OnClose, None)
        return True
        
    def export_showDialog(self, message, yesno) :
        """Opens a notification or confirmation dialog."""
        wx.CallAfter(self.frame.showDialog, self.frame.UTF8ToUserCharset(message.data), yesno)
        # ugly, isn't it ?
        while self.frame.dialogAnswer is None :
            time.sleep(0.1)
        retcode = self.frame.dialogAnswer    
        self.frame.dialogAnswer = None # prepare for next call, just in case
        return retcode
        
    def export_nop(self) :    
        """Does nothing, but allows a clean shutdown from the frame itself."""
        return True
        
    def _dispatch(self, method, params) :    
        """Ensure that only export_* methods are available."""
        return getattr(self, "export_%s" % method)(*params)
        
    def handle_error(self, request, client_address) :    
        """Doesn't display an ugly traceback in case an error occurs."""
        self.logDebug("An exception occured while handling an incoming request from %s:%s" % (client_address[0], client_address[1]))
        
    def verify_request(self, request, client_address) :
        """Ensures that requests which don't come from the print server are rejected."""
        (client, port) = client_address
        if client in self.printServers :
            self.logDebug("%s accepted." % client)
            return True
        else :
            # Unauthorized access !
            self.logDebug("%s rejected." % client)
            return False
        
    def mainloop(self) :
        """XML-RPC Server's main loop."""
        self.register_function(self.export_askDatas)
        self.register_function(self.export_showDialog)
        self.register_function(self.export_quitApplication)
        self.register_function(self.export_nop)
        while not self.frame.quitEvent.isSet() :
            self.handle_request()
        self.server_close()    
        sys.exit(0)
    
    
class GenericInputDialog(wx.Dialog) :
    """Generic input dialog box."""
    def __init__(self, parent, id, labels, varnames, varvalues):
        wx.Dialog.__init__(self, parent, id, \
               _("PyKotIcon data input"), \
               style = wx.CAPTION \
                     | wx.THICK_FRAME \
                     | wx.STAY_ON_TOP \
                     | wx.DIALOG_MODAL)

        self.variables = []
        vsizer = wx.BoxSizer(wx.VERTICAL)
        for i in range(len(varnames)) :
            varname = varnames[i]
            try :
                label = labels[i]
            except IndexError :    
                label = ""
            labelid = wx.NewId()    
            varid = wx.NewId()
            labelst = wx.StaticText(self, labelid, label)
            if varname.lower().find("password") != -1 :
                variable = wx.TextCtrl(self, varid, varvalues.get(varname, ""), style=wx.TE_PASSWORD)
            else :
                variable = wx.TextCtrl(self, varid, varvalues.get(varname, ""))
            self.variables.append(variable)    
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            hsizer.Add(labelst, 0, wx.ALIGN_CENTER | wx.ALIGN_RIGHT | wx.ALL, 5)
            hsizer.Add(variable, 0, wx.ALIGN_CENTER | wx.ALIGN_LEFT | wx.ALL, 5)
            vsizer.Add(hsizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
            
        okbutton = wx.Button(self, wx.ID_OK, "OK")    
        vsizer.Add(okbutton, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetAutoLayout(True)
        self.SetSizerAndFit(vsizer)
        self.Layout()
        
        
class PyKotIcon(wx.Frame):
    """Main class."""
    def __init__(self, parent, id):
        self.dialogAnswer = None
        wx.Frame.__init__(self, parent, id, \
               _("PyKotIcon info for %s") % self.getCurrentUserName(), \
               size = (0, 0), \
               style = wx.FRAME_NO_TASKBAR | wx.NO_FULL_REPAINT_ON_RESIZE)
                     
    def getCurrentUserName(self) :
        """Retrieves the current user's name."""
        if isWindows :
#            return win32api.GetUserName()
            return getpass.getuser()

        else :    
            try :
                return pwd.getpwuid(os.geteuid())[0]
            except :
                return "** Unknown **"
            
    def OnIconify(self, event) :
        """Iconify/De-iconify the application."""
        if not self.IsIconized() :
            self.Iconize(True)
        self.Hide()

    def OnTaskBarActivate(self, event) :
        """Show the application if it is minimized."""
        if self.IsIconized() :
            self.Iconize(False)
        if not self.IsShown() :
            self.Show(True)
        self.Raise()

    def OnClose(self, event) :
        """Cleanly quit the application."""
        if (event is None) \
           or self.options.allowquit :
            self.closeServer()
            self.menu.Destroy()
            self.tbicon.Destroy()
            self.Destroy()
            return True
        else :    
            # self.quitIsForbidden()
            return False

    def OnTaskBarMenu(self, event) :
        """Open the taskbar menu."""
        self.tbicon.PopupMenu(self.menu)

    def OnTaskBarClose(self, event) :
        """React to close from the taskbar."""
        self.Close()
            
    def quitIsForbidden(self) :        
        """Displays a message indicating that quitting the application is not allowed."""
        message = _("Sorry, this was forbidden by your system administrator.")
        caption = _("Information")
        style = wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP
        dialog = wx.MessageDialog(self, message, caption, style)
        dialog.ShowModal()
        dialog.Destroy()
        
    def OnAbout(self, event) :    
        """Displays the about box."""
        dialog = wx.MessageDialog(self, aboutbox % globals(), \
                                        _("About"), \
                                        wx.OK | wx.ICON_INFORMATION)
#        dialog = wx.MessageDialog(self, configuracaobox % globals(), \
#                                  _("Configuração"), \
#                                  wx.OK | wx.ICON_INFORMATION)
#        dialog = wx.Mess
        dialog.ShowModal()
        dialog.Destroy()
        
    def showDialog(self, message, yesno) :
        """Opens a notification dialog."""
        self.dialogAnswer = None
        if yesno :
            caption = _("Confirmation")
            style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION
        else :
            caption = _("Information")
            style = wx.OK | wx.ICON_INFORMATION
        style |= wx.STAY_ON_TOP    
        dialog = wx.MessageDialog(self, message, caption, style)
        self.dialogAnswer = ((dialog.ShowModal() == wx.ID_NO) and "CANCEL") or "OK"
        dialog.Destroy()
        
    def askDatas(self, labels, varnames, varvalues) :
        """Opens a dialog box asking for data entry."""
        self.dialogAnswer = None
        dialog = GenericInputDialog(self, wx.ID_ANY, labels, varnames, varvalues)
        retvalues = {}
        if dialog.ShowModal() == wx.ID_OK :
            retvalues["isValid"] = True
            for i in range(len(varnames)) :
                retvalues[varnames[i]] = dialog.variables[i].GetValue()
        else :        
            retvalues["isValid"] = False
            for k in list(varvalues.keys()) :
                retvalues[k] = ""
        self.dialogAnswer = retvalues
        dialog.Destroy()
        
    def closeServer(self) :    
        """Tells the xml-rpc server to exit."""
        if not self.quitEvent.isSet() :
            self.quitEvent.set()
        server = xmlrpc.client.ServerProxy("http://localhost:%s" % self.options.port)    
        try :
            # wake the server with an empty request 
            # for it to see the event object
            # which has just been set
            server.nop()
        except :    
            # Probably already stopped
            pass
        
    def postInit(self, charset, options, arguments) :    
        """Starts the XML-RPC server."""
        self.charset = charset
        self.options = options
        
        self.tbicon = wx.adv.TaskBarIcon()
        self.greenicon = wx.Icon(os.path.join(iconsdir, "pykoticon-green.ico"), \
                                  wx.BITMAP_TYPE_ICO)
        self.redicon = wx.Icon(os.path.join(iconsdir, "pykoticon-red.ico"), \
                                  wx.BITMAP_TYPE_ICO)
        self.tbicon.SetIcon(self.greenicon, "PyKotIcon")
        
        wx.adv.EVT_TASKBAR_LEFT_DCLICK(self.tbicon, self.OnTaskBarActivate)
        wx.adv.EVT_TASKBAR_RIGHT_UP(self.tbicon, self.OnTaskBarMenu)
        
        self.TBMENU_ABOUT = wx.NewId()
        self.TBMENU_RESTORE = wx.NewId()
        self.TBMENU_CLOSE = wx.NewId()
        wx.EVT_MENU(self.tbicon, self.TBMENU_ABOUT, \
                                 self.OnAbout)
        wx.EVT_MENU(self.tbicon, self.TBMENU_RESTORE, \
                                 self.OnTaskBarActivate)
        wx.EVT_MENU(self.tbicon, self.TBMENU_CLOSE, \
                                 self.OnTaskBarClose)
        self.menu = wx.Menu()
        self.menu.Append(self.TBMENU_ABOUT, _("Sobre"), _("About this software"))
#        self.menu.Append(self.TBMENU_ABOUT, _("Configuração"), _("Configuração Extra"))
        if options.allowquit :
            self.menu.Append(self.TBMENU_CLOSE, _("Quit"), \
                                                _("Exit the application"))
        wx.EVT_ICONIZE(self, self.OnIconify)
        wx.EVT_CLOSE(self, self.OnClose)
        self.Show(True)
        self.Hide()
        
        self.quitEvent = threading.Event()
        self.server = MyXMLRPCServer(self, options, arguments)
        
    def UTF8ToUserCharset(self, text) :
        """Converts from UTF-8 to user's charset."""
        if text is not None :
            try :
                return text.decode("UTF-8").encode(self.charset, "replace") 
            except (UnicodeError, AttributeError) :    
                try :
                    # Maybe already in Unicode
                    return text.encode(self.charset, "replace") 
                except (UnicodeError, AttributeError) :
                    pass # Don't know what to do
        return text
        
    def userCharsetToUTF8(self, text) :
        """Converts from user's charset to UTF-8."""
        if text is not None :
            try :
                # We don't necessarily trust the default charset, because
                # xprint sends us titles in UTF-8 but CUPS gives us an ISO-8859-1 charset !
                # So we first try to see if the text is already in UTF-8 or not, and
                # if it is, we delete characters which can't be converted to the user's charset,
                # then convert back to UTF-8. PostgreSQL 7.3.x used to reject some unicode characters,
                # this is fixed by the ugly line below :
                return text.decode("UTF-8").encode(self.charset, "replace").decode(self.charset).encode("UTF-8", "replace")
            except (UnicodeError, AttributeError) :
                try :
                    return text.decode(self.charset).encode("UTF-8", "replace") 
                except (UnicodeError, AttributeError) :    
                    try :
                        # Maybe already in Unicode
                        return text.encode("UTF-8", "replace") 
                    except (UnicodeError, AttributeError) :
                        pass # Don't know what to do
        return text
        

class PyKotIconApp(wx.App):
    def OnInit(self) :
        self.frame = PyKotIcon(None, wx.ID_ANY)
        self.frame.Show(False)
        self.SetTopWindow(self.frame)
        return True
        
    def postInit(self, charset, options, arguments) :    
        """Continues processing."""
        self.frame.postInit(charset, options, arguments)
        
        
def main() :
    """Program's entry point."""
    try :
        locale.setlocale(locale.LC_ALL, "")
    except (locale.Error, IOError) :
        sys.stderr.write("Problem while setting locale.\n")
    try :
        gettext.install("pykoticon")
    except :
        gettext.NullTranslations().install()
        
    localecharset = None
    try :
        try :
            localecharset = locale.nl_langinfo(locale.CODESET)
        except AttributeError :    
            try :
                localecharset = locale.getpreferredencoding()
            except AttributeError :    
                try :
                    localecharset = locale.getlocale()[1]
                    localecharset = localecharset or locale.getdefaultlocale()[1]
                except ValueError :    
                    pass        # Unknown locale, strange...
    except locale.Error :            
        pass
    charset = os.environ.get("CHARSET") or localecharset or "ISO-8859-15"
    
    parser = optparse.OptionParser(usage="usage : pykoticon [options] server1 [server2 ...]")
    parser.add_option("-v", "--version", 
                            action="store_true", 
                            dest="version",
                            help=_("show PyKotIcon's version number and exit."))
    parser.add_option("-c", "--cache", 
                            type="int", 
                            default=0, 
                            dest="cache",
                            help=_("the duration of the cache in seconds to keep input forms' datas in memory. Defaults to 0 second, meaning no cache."))
    parser.add_option("-d", "--debug", 
                            action="store_true", 
                            dest="debug",
                            help=_("activate debug mode."))
    parser.add_option("-p", "--port", 
                            type="int", 
                            default=7654, 
                            dest="port",
                            help=_("the TCP port PyKotIcon will listen to, default is 7654."))
    parser.add_option("-q", "--allowquit", 
                            action="store_true", 
                            dest="allowquit",
                            help=_("allow the end user to close the application."))
    (options, arguments) = parser.parse_args()
    if options.version :
        print("PyKotIcon v%(__version__)s" % globals())
    else :
        if not (1024 <= options.port <= 65535) :
            sys.stderr.write(_("The TCP port number specified for --port must be between 1024 and 65535.\n"))
        elif not (0 <= options.cache <= 86400) :    
            sys.stderr.write(_("The duration specified for --cache must be between 0 and 86400 seconds.\n"))
        else :    
            app = PyKotIconApp()
            app.postInit(charset, options, arguments)
            app.MainLoop()
    
    
if __name__ == '__main__':
    main()
    
