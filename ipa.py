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
    'IPAFile',
]

def _apple_keys_first(items):
    """Attempt to put all custom keys last"""
    key, val = items
    if key == 'BuildMachineOSBuild':
        return -11
    if key.startswith('CF'):
        return -10
    if key.startswith('DT'):
        return -9
    if key == 'MinimumOSVersion':
        return -8
    if key.startswith('UI'):
        return -7

    return key


class BadIPAError(Exception):
    pass


class IPAFile(ZipFile):
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
        app_dir_regex = re.compile(ur'^Payload/\w+\.app/$', re.UNICODE)
        matched = len([x for x in [re.match(app_dir_regex, y)
                                   for y in filenames]
                       if x]) == 1
        is_ipa = 'iTunesMetadata.plist' in filenames and matched

        if not is_ipa:
            self._raise_ipa_error()

        self._get_app_info()

    def _raise_ipa_error(self):
        self.close()
        raise BadIPAError('File not detected as iOS application '
                          'distribution file')

    def _get_app_info(self):
        """Find application's Info.plist and read it"""
        info_plist = None
        info_plist_regex = re.compile(ur'Payload/\w+\.app/Info\.plist',
                                      re.UNICODE)

        for data in self.filelist:
            if re.match(info_plist_regex, data.filename):
                info_plist = data

        if not info_plist:
            self._raise_ipa_error()

        info_plist = self.read(info_plist)
        self.app_info = readPlistFromString(info_plist)

        return self.app_info

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
    print(IPAFile(sys.argv[1]))
