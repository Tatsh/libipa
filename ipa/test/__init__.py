# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from os import remove as rm
from tempfile import mkstemp
from zipfile import ZipFile, ZIP_DEFLATED
import random
import string
import unittest

from biplist import writePlistToString
import six

try:
    from ipa import BadIPAError, IPAFile
except ImportError:
    execfile('../__init__.py')

class TestIPAFile(unittest.TestCase):
    _temp_files = []

    def _random_string(self, length=10):
        ret = []

        for n in range(length):
            ret.append(random.choice(string.ascii_letters + string.digits))

        return ''.join(ret)

    def _create_ipa(self, create_info_plist=True, universal=False, app_name=None):
        h, zippath = mkstemp(prefix='libipa-', suffix='.ipa')
        self._temp_files.append(zippath)
        app_dir = '%s.app' % (self._random_string(),) if not app_name else app_name

        with ZipFile(zippath, 'w', ZIP_DEFLATED) as h:
            if create_info_plist:
                info = dict(
                    CFBundleIdentifier='com.%s.%s' % (self._random_string(), self._random_string(),),
                    CFBundleDisplayName=self._random_string(),
                    LSRequiresIPhoneOS=True,
                    MinimumOSVersion='6.0',
                    UIStatusBarStyle='UIStatusBarStyleDefault',
                )

                if universal:
                    info['UIDeviceFamily'] = [1, 2]
                else:
                    info['UIDeviceFamily'] = [1]

                if six.PY3 and type(app_dir) is str:
                    app_dir = app_dir.encode('utf-8')

                info_plist_name = (b'Payload/' + app_dir + b'/Info.plist').decode('utf-8')

                h.writestr(info_plist_name, writePlistToString(info))
                h.writestr('iTunesMetadata.plist', writePlistToString({'Test': 'Data'}))

        return zippath

    def test_bad_ipa(self):
        self.assertRaises(BadIPAError, IPAFile, self._create_ipa(create_info_plist=False))

    def test_ipa_info(self):
        ipa = IPAFile(self._create_ipa())
        keys = (
            'CFBundleIdentifier',
            'CFBundleDisplayName',
            'LSRequiresIPhoneOS',
            'MinimumOSVersion',
            'UIStatusBarStyle',
            'UIDeviceFamily',
        )

        for k in keys:
            self.assertIn(k, ipa.app_info)

    def test_unicode_app_name(self):
        ipa = IPAFile(self._create_ipa(app_name='ありがとう你好مرحبا.app'.encode('utf-8')))
        keys = (
            'CFBundleIdentifier',
            'CFBundleDisplayName',
            'LSRequiresIPhoneOS',
            'MinimumOSVersion',
            'UIStatusBarStyle',
            'UIDeviceFamily',
        )

        for k in keys:
            self.assertIn(k, ipa.app_info)

    def test_string_repr(self):
        data = str(IPAFile(self._create_ipa()))
        keys = (
            'CFBundleIdentifier',
            'CFBundleDisplayName',
            'LSRequiresIPhoneOS',
            'MinimumOSVersion',
            'UIStatusBarStyle',
            'UIDeviceFamily',
        )

        for k in keys:
            self.assertIn('%s:' % (k,), data)

    def test_ipa_non_universal(self):
        ipa = IPAFile(self._create_ipa())
        self.assertEqual([1], ipa.app_info['UIDeviceFamily'])

    def test_ipa_universal(self):
        ipa = IPAFile(self._create_ipa(universal=True))
        self.assertGreater(len(ipa.app_info['UIDeviceFamily']), 1)

    def tearDown(self):
        for z in self._temp_files:
            try:
                with open(z, 'rb'):
                    pass
                rm(z)
            except IOError:
                continue
