#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pkipplib : IPP and CUPS support for Python
#
# (c) 2003-2013 Jerome Alet <alet@librelogiciel.com>
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
# $Id$

import sys

sys.path.insert(0, "../pkipplib")
import pkipplib

cups = pkipplib.CUPS()
answer = cups.createSubscription("ipp://localhost/", ["printer-added", "printer-deleted"],
                                                             userdata="samplenotifier:blah",
                                                                                                                  recipient="samplenotifier",
                                                                                                                                                                       charset="utf-8")
print answer

#print answer.operation["attributes-charset"]

