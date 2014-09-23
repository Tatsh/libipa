# -*- coding: utf-8 -*-

from __future__ import print_function
import json
import re
import sys
from zipfile import (
    ZIP_STORED,
    ZipFile,
)

from biplist import readPlistFromString

__all__ = [
    'BadIPAError',
    'IPAFile',
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


class IPAFile(ZipFile):
    info_plist_regex = re.compile(ur'^Payload/[\w\-_\s]+\.app/Info\.plist$',
                                  re.UNICODE)
    app_info = None

    def __init__(self,
                 file,
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

    def is_universal(self):
        try:
            data = self.app_info['UIDeviceFamily']
        except KeyError:
            return False

        return len(data) > 1

    def __str__(self):
        structured_types = (list, dict,)
        ret = []
        items = sorted(IPAFile(sys.argv[1]).app_info.items(),
                       key=_apple_keys_first)

        for (k, v) in items:
            if type(v) in structured_types:
                v = json.dumps(v)
            ret.append('%s: %s' % (k, v,))

        return '\n'.join(ret)


if __name__ == '__main__':
    try:
        print('Reading %s' % (sys.argv[1],), file=sys.stderr)
        print(unicode(IPAFile(sys.argv[1])))
    except BadIPAError as e:
        print(e.msg, file=sys.stderr)
