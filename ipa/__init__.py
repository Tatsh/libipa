# -*- coding: utf-8 -*-

from __future__ import print_function
import json
import logging
import re
import sys
from zipfile import (
    ZIP_STORED,
    ZipFile,
)

from biplist import readPlistFromString

__all__ = [
    'AppNameOrVersionError',
    'BadIPAError',
    'IPAFile',
    'IPAInfo',
    'UnknownDeviceFamilyError',
]


def _apple_keys_first(items):
    """Attempt to put all Apple official keys first.

    https://developer.apple.com/library/ios/documentation/general/Reference/InfoPlistKeyReference/Introduction/Introduction.html"""
    key, val = items
    if key.startswith('AP'):  # APInstallerURL
        return -13
    if key.startswith('ATS'):  # ATSApplicationFontsPath
        return -12
    if key == 'BuildMachineOSBuild':
        return -11
    if key.startswith('CF'):
        return -10
    if key.startswith('CS'):  # CSResourcesFileMapped
        return -9
    if key.startswith('DT'):
        return -8
    if key.startswith('GK'):  # GameKit keys
        return -7
    if key.startswith('LS'):  # Launch Services
        return -6
    if key == 'MinimumOSVersion':
        return -5
    if key.startswith('MK'):
        return -4
    if key.startswith('NS'):
        return -3
    if key.startswith('QL'):  # QLSandboxUnsupported
        return -2
    if key == 'QuartzGLEnable':
        return -1
    if key.startswith('UI'):
        return 0
    if key.startswith('UT'):  # UTExportedTypeDeclarations
        return 1

    return key


class BadIPAError(Exception):
    msg = 'File "%s" not detected as iOS application distribution file.'

    def __init__(self, filename, msg=None):
        if msg:
            self.msg = msg
        self.msg = self.msg % (filename,)


class AppNameOrVersionError(Exception):
    pass


class UnknownDeviceFamilyError(Exception):
    pass


class IPAFile(ZipFile):
    info_plist_regex = re.compile(r'^Payload/[\w\-_\s]+\.app/Info\.plist$',
                                  re.UNICODE)
    app_info = None
    logger = logging.getLogger(__name__)

    def __init__(self,
                 file,
                 mode='r',
                 compression=ZIP_STORED,
                 allowZip64=True,
                 level=logging.ERROR):
        """Open IPA file. Primary difference from ZipFile is that allowZip64
        is set to True by default because many IPA files are larger than 2
        GiB in file size."""
        ZipFile.__init__(self,
                         file,
                         mode=mode,
                         compression=compression,
                         allowZip64=allowZip64)

        filenames = self.namelist()
        matched = len([x for x in [re.match(self.info_plist_regex, y)
                                   for y in filenames]
                       if x]) == 1
        is_ipa = 'iTunesMetadata.plist' in filenames and matched

        if not is_ipa:
            self._raise_ipa_error()

        self._get_app_info()

    def _raise_ipa_error(self):
        self.close()
        raise BadIPAError(self.filename)

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

    def get_device_family(self):
        device_families = self.app_info['UIDeviceFamily']

        if len(device_families) == 1:
            family = device_families[0]

            # Sometimes these values are not longs, but instead strings
            # (NSString of course)
            if isinstance(family, str):
                family = int(family)

            if family == 2:
                device_family = 'ipad'
            elif family == 1:
                device_family = 'iphone'  # iPhone/iPod Touch only app
            else:
                raise UnknownDeviceFamilyError('Unknown device family ID %d' % (family,))
        else:
            device_family = 'universal'

        return device_family

    def is_universal(self):
        return get_device_family() == 'universal'

    def get_app_name(self):
        keys = (
            'CFBundleDisplayName',
            'CFBundleName',
            'CFBundleExecutable',
            'CFBundleIdentifier',
        )
        name = None

        for key in keys:
            if key not in self.app_info:
                continue

            name = self.app_info[key].strip()

            if not name:
                continue
            else:
                break

        if not name:
            raise AppNameOrVersionError('Unable to get an application name %s' %
                                        (app_info,))

        return name

    def get_app_version(self):
        try:
            val = self.app_info['CFBundleShortVersionString'].strip()

            if val:
                return val
        except KeyError:
            val = self.app_info['CFBundleVersion'].strip()

            if val:
                return val

        raise AppNameOrVersionError('Cannot get application version string')

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
        except UnicodeEncodeError as e:
            self.logger.error('UnicodeEncodeError with name or version key '
                              '(%s)' % (self.app_info['CFBundleIdentifier'],))
            raise e

        raise AppNameOrVersionError('Could not determine an IPA file name')

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


class IPAInfo(IPAFile):
    def __init__(self, app_info={}, logger=None):
        self.app_info = app_info


if __name__ == '__main__':
    try:
        print('Reading %s' % (sys.argv[1],), file=sys.stderr)
        print(unicode(IPAFile(sys.argv[1])))
    except BadIPAError as e:
        print(e.msg, file=sys.stderr)
