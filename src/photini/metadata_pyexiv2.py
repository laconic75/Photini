##  Photini - a simple photo metadata editor.
##  http://github.com/jim-easterbrook/Photini
##  Copyright (C) 2012-13  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

from __future__ import unicode_literals

import logging

import pyexiv2

class MetadataHandler(object):
    def __init__(self, path):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._md = pyexiv2.ImageMetadata(path)
        self._md.read()

    def save(self):
        try:
            self._md.write()
        except IOError as ex:
            self.logger.exception(ex)
            return False
        return True

    def copy(self, other, exif=True, iptc=True, xmp=True, comment=True):
        # copy from other to self (pyexiv2 copies from self to other)
        other._md.copy(self._md, exif=exif, iptc=iptc, xmp=xmp, comment=comment)

    def get_exif_tags(self):
        return self._md.exif_keys

    def get_iptc_tags(self):
        return self._md.iptc_keys

    def get_xmp_tags(self):
        return self._md.xmp_keys

    def get_exif_tag_string(self, tag):
        return self._md[tag].raw_value

    def get_iptc_tag_multiple(self, tag):
        return self._md[tag].value

    def get_xmp_tag_string(self, tag):
        return self._md[tag].raw_value

    def get_xmp_tag_multiple(self, tag):
        item = self._md[tag]
        if item.type == 'Lang Alt':
            return item.value.values()
        return item.value

    def set_exif_tag_string(self, tag, value):
        new_tag = pyexiv2.ExifTag(tag)
        new_tag.raw_value = value.encode('utf-8')
        self._md[tag] = new_tag

    def set_exif_tag_long(self, tag, value):
        self._md[tag] = pyexiv2.ExifTag(tag, value)

    def set_iptc_tag_multiple(self, tag, value):
        self._md[tag] = pyexiv2.IptcTag(tag, value)

    def set_xmp_tag_string(self, tag, value):
        new_tag = pyexiv2.XmpTag(tag)
        new_tag.raw_value = value
        self._md[tag] = new_tag

    def set_xmp_tag_multiple(self, tag, value):
        new_tag = pyexiv2.XmpTag(tag)
        if new_tag.type == 'Lang Alt':
            new_tag = pyexiv2.XmpTag(tag, {'x-default': value[0]})
        else:
            new_tag = pyexiv2.XmpTag(tag, value)
        self._md[tag] = new_tag

    def clear_tag(self, tag):
        del self._md[tag]
