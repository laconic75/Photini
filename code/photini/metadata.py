##  Photini - a simple photo metadata editor.
##  http://github.com/jim-easterbrook/Photini
##  Copyright (C) 2012  Jim Easterbrook  jim@jim-easterbrook.me.uk
##
##  This program is free software: you can redistribute it and/or
##  modify it under the terms of the GNU General Public License as
##  published by the Free Software Foundation, either version 3 of the
##  License, or (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
##  General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program.  If not, see
##  <http://www.gnu.org/licenses/>.

import datetime
import fractions
import os

import pyexiv2
from PyQt4 import QtCore

class GPSvalue(object):
    def __init__(self, degrees=0.0, latitude=True):
        self.degrees = degrees
        self.latitude = latitude

    def fromGPSCoordinate(self, value):
        self.degrees = (float(value.degrees) +
                       (float(value.minutes) / 60.0) +
                       (float(value.seconds) / 3600.0))
        if value.direction in ('S', 'W'):
            self.degrees = -self.degrees
        self.latitude = value.direction in ('S', 'N')
        return self

    def toGPSCoordinate(self):
        if self.degrees >= 0.0:
            direction = ('E', 'N')[self.latitude]
            value = self.degrees
        else:
            direction = ('W', 'S')[self.latitude]
            value = -self.degrees
        degrees = int(value)
        value = (value - degrees) * 60.0
        minutes = int(value)
        seconds = (value - minutes) * 60.0
        return pyexiv2.utils.GPSCoordinate(degrees, minutes, seconds, direction)

    def fromRational(self, value, ref):
        if isinstance(value, list):
            self.degrees = (float(value[0]) +
                           (float(value[1]) / 60.0) +
                           (float(value[2]) / 3600.0))
        else:
            self.degrees = float(value)
        if ref in ('S', 'W'):
            self.degrees = -self.degrees
        self.latitude = ref in ('S', 'N')
        return self

    def toRational(self):
        if self.degrees >= 0.0:
            ref = ('E', 'N')[self.latitude]
            value = self.degrees
        else:
            ref = ('W', 'S')[self.latitude]
            value = -self.degrees
        return fractions.Fraction(value).limit_denominator(1000000), ref

class Metadata(QtCore.QObject):
    keys = {
        'date'        : ('Exif.Photo.DateTimeOriginal',
                         'Exif.Photo.DateTimeDigitized', 'Exif.Image.DateTime'),
        'title'       : ('Xmp.dc.title', 'Iptc.Application2.ObjectName',
                         'Exif.Image.ImageDescription'),
        'creator'     : ('Xmp.dc.creator', 'Iptc.Application2.Byline',
                         'Exif.Image.Artist'),
        'description' : ('Xmp.dc.description', 'Iptc.Application2.Caption'),
        'keywords'    : ('Xmp.dc.subject', 'Iptc.Application2.Keywords'),
        'copyright'   : ('Xmp.dc.rights', 'Xmp.tiff.Copyright',
                         'Iptc.Application2.Copyright', 'Exif.Image.Copyright'),
        'latitude'    : ('Exif.GPSInfo.GPSLatitude', 'Xmp.exif.GPSLatitude'),
        'longitude'   : ('Exif.GPSInfo.GPSLongitude', 'Xmp.exif.GPSLongitude'),
        'orientation' : ('Exif.Image.Orientation',),
        }
    def __init__(self, path, parent=None):
        QtCore.QObject.__init__(self, parent)
        self._md = pyexiv2.ImageMetadata(path)
        self._md.read()
        self._new = False
##        print '### exif'
##        for key in self._md.exif_keys:
##            try:
##                print key, self._md[key].value
##            except:
##                pass
##        print '### iptc'
##        for key in self._md.iptc_keys:
##            print key, self._md[key].value
##        print '### xmp'
##        for key in self._md.xmp_keys:
##            print key, self._md[key].value

    def save(self):
        if not self._new:
            return
        self._md.write()
        self._set_status(False)

    def has_GPS(self):
        return (('Xmp.exif.GPSLatitude' in self._md.xmp_keys) or
                ('Exif.GPSInfo.GPSLatitude' in self._md.exif_keys))

    def get_item(self, name):
        # Turn every type of text data into a list of unicode strings.
        # Let caller decide what it means.
        for key in self.keys[name]:
            family, group, tag = key.split('.')
            if key in self._md.xmp_keys:
                item = self._md[key]
                if item.type.split()[0] in ('bag', 'seq'):
                    return item.value
                if item.type == 'Lang Alt':
                    return item.value.values()
                if item.type == 'GPSCoordinate':
                    return GPSvalue().fromGPSCoordinate(item.value)
                print key, item.type, item.value
                return item.value
            if key in self._md.iptc_keys:
                return map(lambda x: unicode(x, 'iso8859_1'),
                           self._md[key].value)
            if key in self._md.exif_keys:
                value = self._md[key].value
                if isinstance(value, (datetime.datetime, int)):
                    return value
                elif group == 'GPSInfo':
                    return GPSvalue().fromRational(
                        value, self._md['%sRef' % key].value)
                else:
                    return [unicode(value, 'iso8859_1')]
        return None

    def set_item(self, name, value):
        if value == self.get_item(name):
            return
        for key in self.keys[name]:
            family, group, tag = key.split('.')
            if family == 'Xmp':
                new_tag = pyexiv2.XmpTag(key)
                if new_tag.type.split()[0] in ('bag', 'seq'):
                    new_tag = pyexiv2.XmpTag(key, value)
                elif new_tag.type == 'Lang Alt':
                    new_tag = pyexiv2.XmpTag(key, {'': value[0]})
                elif new_tag.type == 'GPSCoordinate':
                    new_tag = pyexiv2.XmpTag(key, value.toGPSCoordinate())
                else:
                    raise KeyError("Unknown type %s" % new_tag.type)
            elif family == 'Iptc':
                new_tag = pyexiv2.IptcTag(key, value)
            elif family == 'Exif':
                if group == 'GPSInfo':
                    numbers, ref = value.toRational()
                    self._md['%sRef' % key] = ref
                    new_tag = pyexiv2.ExifTag(key, numbers)
                else:
                    new_tag = pyexiv2.ExifTag(key, value[0])
            self._md[key] = new_tag
        self._set_status(True)

    def del_item(self, name):
        changed = False
        for key in self.keys[name]:
            family, group, tag = key.split('.')
            if key in (self._md.xmp_keys +
                       self._md.iptc_keys +
                       self._md.exif_keys):
                del self._md[key]
                changed = True
        if changed:
            self._set_status(True)

    new_status = QtCore.pyqtSignal(bool)
    def _set_status(self, status):
        self._new = status
        self.new_status.emit(self._new)

    def changed(self):
        return self._new