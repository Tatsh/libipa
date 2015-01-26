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
    
    The following is an example of the speed increase of this modification.
    ```
    >>> timeit.timeit('a="ATS"\nif a.startswith("ATS"):\n pass', number=1000)
    0.0004978179931640625
    >>> timeit.timeit('a="ATS"\nif a[0:3] is "ATS":\n pass', number=1000)
    0.0002808570861816406
    ```
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
   # if key.startswith('AP'):  # APInstallerURL
   #     return -13
    #if key.startswith('ATS'):  # ATSApplicationFontsPath
      #  return -12
    #if key == 'BuildMachineOSBuild':
      #  return -11
    #if key.startswith('CF'):
     #   return -10
    #if key.startswith('CS'):  # CSResourcesFileMapped
      #  return -9
    #if key.startswith('DT'):
      #  return -8
    #if key.startswith('GK'):  # GameKit keys
     #   return -7
    #if key.startswith('LS'):  # Launch Services
     #   return -6
    #if key == 'MinimumOSVersion':
     #   return -5
    #if key.startswith('MK'):
      #  return -4
    #if key.startswith('NS'):
      #  return -3
    #if key.startswith('QL'):  # QLSandboxUnsupported
     #   return -2
    #if key == 'QuartzGLEnable':
   #     return -1
    #if key.startswith('UI'):
     #   return 0
    #if key.startswith('UT'):  # UTExportedTypeDeclarations
     #   return 1

    return key


class InvalidIPAError(Exception):
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
    info_plist_regex = re.compile(r'^Payload/[\w\-_\s]+\.app/Info\.plist$',
                                  re.UNICODE)
    app_info = None
    logger = logging.getLogger('IPAFile')
    debug = False
    
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
        raise InvalidIPAError(self.filename)
    
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
        device_families = self.app_info['UIDeviceFamily']
        has_device_id = len(device_families) == 1
        
        if not has_device_id:
            return 'universal'
        
        family = self._vailidate_family(device_families[0])
        
        if family == 1:
            return 'iphone'
        elif family == 2:
            return 'ipad'
        
        raise UnknownDeviceFamilyError(
            'Unknown device family id ({0})'.format(family)
        )
    
    
    def _determine_app_name(self, name):
        return name if name else None
    
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
        
        if not name:
            raise InvalidApplicationNameError(
                'Application name cannot be found.'
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
            self.logger.error(
                'UnicodeEncodeError with name or version key '
               '(%s)'.format(self.app_info['CFBundleIdentifier'])
             )
             
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
                       if re.match(r'Payload/.+\.app', x)][0].split('/')[0:2][1]
            bin_name = app_dir[0:-4]

        if full:
            if alt:
                return 'Payload/%s/%s' % (app_dir, bin_name,)

            return 'Payload/%s.%s/%s' % (
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

# In the long run this will be removed and testing will be
# accessed in the setup.py.
if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    
    try:
        logging.info('Reading {0}'.format(sys.argv[1]))
        logging.info(unicode(IPAFile(sys.argv[1])))
        #print('Reading %s' % (sys.argv[1],), file=sys.stderr)
        #print(unicode(IPAFile(sys.argv[1])))
    except BadIPAError as e:
        logging.exception(e.msg)
        #print(e.msg, file=sys.stderr)