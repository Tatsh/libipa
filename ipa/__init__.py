#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import logging
import re

from zipfile import (
    ZIP_STORED,
    ZipFile,
)

from biplist import readPlistFromString

__all__ = [
    'BadIPAError',
    'IPAFile',
    'IPAInfo',
    'UnknownDeviceFamilyError',
]


def _apple_keys_first(items):
    """Attempt to put all Apple official keys first.

    https://developer.apple.com/library/ios/documentation/general/Reference/InfoPlistKeyReference/Introduction/Introduction.html"""
    key, val = items
    if key[0:2] is 'AP':
        return -13
    if key[0:3] is 'ATS':
        return -12
    if key == 'BuildMachineOSBuild':
        return -11
    if key[0:2] is 'CF':
        return -10
    if key[0:2] is 'CS':
        return -9
    if key[0:2] is 'DT':
        return -8
    if key[0:2] is 'GK':
        return -7
    if key[0:2] is 'LS':
        return -6
    if key == 'MinimumOSVersion':
        return -5
    if key[0:2] is 'MK':
        return -4
    if key[0:2] is 'NS':
        return -3
    if key[0:2] is 'QL':
        return -2
    if key == 'QuartzGLEnable':
        return -1
    if key[0:2] is 'UI':
        return 0
    if key[0:2] is 'UT':
        return 1

    return 777


def _yn(s):
    return 'Yes' if s else 'No'


def _tests_fails(a, b):
    return 1 if a and not b else 2


def _tests_report(a, b):
    msg_info = 'Could not obtain the "Info.plist" file from archive.'
    msg_itunes = ('Could not obtain the "iTunesMetadata.plist" file from ' +
                  'archive.')
    msg_both = (
        'Could not obtain the "Info.plist" and "iTunesMetadata.plist"' +
        'files from archive.')

    if not a and not b:
        return msg_both

    return msg_info if not a and b else msg_itunes


def _family_tests_report(a=None):
    if a is 1:
        return 'iPhone'

    if a is 2:
        return 'iPad'


class BadIPAError(Exception):
    msg = 'File "{0}" not detected as iOS application distribution file.'

    def __init__(self, filename, msg=None):
        if msg:
            self.msg = msg

        self.msg = self.msg.format(filename)


class InvalidApplicationNameError(Exception):
    pass


class InvalidUnicodeApplicationNameError(UnicodeEncodeError):
    pass


class UnknownApplicationNameError(Exception):
    pass


class UnknownApplicationVersionError(Exception):
    pass


class UnknownDeviceFamilyError(Exception):
    pass


class IPAFile(ZipFile):
    info_plist_regex = re.compile(r'^Payload/[^/]+/Info\.plist$',
                                  re.UNICODE)
    app_info = None
    _logger = logging.getLogger('libipa')

    def __init__(self,
                 file,
                 strict=False,
                 mode='r',
                 compression=ZIP_STORED,
                 allowZip64=True):
        """Open IPA file. Primary difference from ZipFile is that allowZip64
        is set to True by default because many IPA files are larger than 2
        GiB in file size."""
        ZipFile.__init__(self,
                         file,
                         mode=mode,
                         compression=compression,
                         allowZip64=allowZip64)

        filenames = self.namelist()

        self._logger.debug('Files within the archive.\n{0}'.format(filenames))

        matched = len([x for x in [re.match(self.info_plist_regex, y)
                                   for y in filenames]
                       if x]) == 1

        self._logger.debug('IPA file passes test phase one: {0}'.format(
            _yn(matched)))
        if strict:
            is_ipa = 'iTunesMetadata.plist' in filenames and matched
            self._logger.debug('IPA file passes test phase two: {0}'.format(
                _yn(is_ipa)))
        else:
            is_ipa = matched

        if not is_ipa:
            self._logger.debug(
                'IPA file failed {0}/2 test phases, IPA file is invalid.'.
                format(_tests_fails(matched, is_ipa)))

            self._logger.debug('IPA file test phase report: {0}'.format(
                _tests_report(matched, is_ipa)))

            self._raise_ipa_error('Not an IPA')

        self._logger.debug(
            'IPA file passes all test phases, IPA file is valid.')

        self._get_app_info()

    def _raise_ipa_error(self, msg):
        self.close()
        self._logger.debug('Closing Zipfile.')
        raise BadIPAError(self.filename if not msg else msg)

    def _get_app_info(self):
        """Find application's Info.plist and read it"""
        info_plist = None

        for data in self.filelist:
            if re.match(self.info_plist_regex, data.filename):
                info_plist = data

        if not info_plist:
            self._raise_ipa_error()

        info_plist = self.read(info_plist)
        self.app_info = readPlistFromString(info_plist)

        return self.app_info

    def _vailidate_family(self, family):
        return family if not isinstance(family, str) else int(family)

    def get_device_family(self):
        has_device_id = False
        try:
            device_families = self.app_info[b'UIDeviceFamily']
            has_device_id = True
        except KeyError:
            try:
                device_families = self.app_info['UIDeviceFamily']
                has_device_id = True
            except KeyError:
                pass
        self._logger.info('IPA info file contains device id: {0}'.format(
            _yn(has_device_id)))

        if not has_device_id:
            self._logger.debug('IPA Device: iPhone (assumed).')
            return 'iphone'

        if len(device_families) > 1:
            self._logger.debug('IPA Device: Universal (assumed).')
            return 'universal'

        family = self._vailidate_family(device_families[0])
        self._logger.debug('IPA Device: {0}'.format(
            _family_tests_report(family)))

        if family is 2:
            return 'ipad'

        return 'iphone'

    @property
    def logger(self):
        return self._logger

    def get_app_name(self):
        keys = (
            'CFBundleDisplayName',
            'CFBundleName',
            'CFBundleExecutable',
            'CFBundleIdentifier',
        )

        name = None

        for key in keys:
            if key in self.app_info:
                name = self.app_info[key].strip()
                break

        self._logger.debug('IPA application name: {0}'.format(name))

        if not name:
            raise InvalidApplicationNameError(
                'libipa cannot determine the IPA application name.'
            )

        return name

    def get_app_version(self):
        keys = (
            'CFBundleShortVersionString',
            'CFBundleVersion',
        )

        version = None

        for key in keys:
            if key in self.app_info:
                version = self.app_info[key].strip()
                break

        self._logger.debug('IPA application version {0}'.format(version))

        if not version:
            raise UnknownApplicationVersionError(
                'libipa cannot determine the IPA version.'
            )

        return version

    def is_ipad(self):
        return self.get_device_family() == 'ipad'

    def is_iphone(self):
        return self.get_device_family() == 'iphone'

    def is_universal(self):
        return self.get_device_family() == 'universal'

    def get_ipa_filename(self):
        """
        Returns an approximate name of the IPA that iTunes would use when
        saving which is normally 'Application Name <versionNumber>.ipa'.
        """
        try:
            return '%s %s.ipa' % (
                self.get_app_name(),
                self.get_app_version(),
            )
        except InvalidUnicodeApplicationNameError as e:
            self._logger.exception(e.msg)

            raise e

        raise UnknownApplicationNameError(
            'Could not determine an IPA file name'
        )

    def get_bin_name(self, full=False):
        alt = False

        try:
            bin_name = self.app_info['bundleDisplayName']
        except KeyError:
            self.logger.info('Using alternative method to guess binary name')

            alt = True
            app_dir = [x for x in self.namelist()
                       if re.match(r'Payload/.+\.app', x)
                       ][0].split('/')[0:2][1]
            bin_name = app_dir[0:-4]
            self._logger.debug('IPA application directory {0}.'.format(
                app_dir))
            self._logger.debug('IPA binary name {0}.'.format(bin_name))

        if full:
            if alt:
                return 'Payload/{0}/{1}'.format(
                    app_dir,
                    bin_name
                )

            return 'Payload/{0}.{1}/{2}'.format(
                self.app_info['bundleDisplayName'],
                self.app_info['fileExtension'],
                bin_name,
            )

        return bin_name

    def __str__(self):
        structured_types = (list, dict,)
        ret = []
        items = sorted(self.app_info.items(),
                       key=_apple_keys_first)

        for (k, v) in items:
            if type(v) in structured_types:
                v = json.dumps(v)
            ret.append('%s: %s' % (k, v,))

        return '\n'.join(ret)

    __repr__ = __str__


class IPAInfo(IPAFile):
    def __init__(self, app_info={}, logger=None):
        self.app_info = app_info
