#!/usr/bin/env python
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

from ipa import InvalidIPAError, IPAFile

class TestIPAFile(unittest.TestCase):
    _temp_files = []

    def _random_string(self, length=10):
        ret = []

        for n in range(length):
            ret.append(random.choice(string.ascii_letters + string.digits))

        return ''.join(ret)

    def _create_ipa(self, create_info_plist=True, universal=False,
                    iphone=False, ipad=False, app_name=None, 
                    bundle_display_name=None):
        h, zippath = mkstemp(prefix='libipa-', suffix='.ipa')
        self._temp_files.append(zippath)

        if not app_name:
            app_name = self._random_string()
        if six.PY2:
            app_dir = b'%s.app' % (app_name)
        else:
            app_dir = '{0}.app'.format(app_name).encode('utf-8')
            
        with ZipFile(zippath, 'w', ZIP_DEFLATED) as h:
            if create_info_plist:
                info = dict(
                    CFBundleIdentifier='com.{0}.{1}'.format(
                        self._random_string(), self._random_string(),
                    ),
                    CFBundleDisplayName=app_name,
                    LSRequiresIPhoneOS=True,
                    MinimumOSVersion='6.0',
                    UIStatusBarStyle='UIStatusBarStyleDefault',
                )

                if six.PY3 and type(app_dir) is str:
                    app_dir = app_dir.encode('utf-8')
                if six.PY3 and type(app_name) is str:
                    app_name = app_name.encode('utf-8')

                app_dir = b'Payload/' + app_dir + b'/'
                app_path = app_dir + app_name

                if six.PY3:
                    app_path = app_path.decode('utf-8')

                h.writestr(app_path, b'FACE')

                if bundle_display_name is False:
                    del info['CFBundleDisplayName']

                if universal:
                    info['UIDeviceFamily'] = [1, 2]
                elif iphone:
                    info['UIDeviceFamily'] = [1]
                elif ipad:
                    info['UIDeviceFamily'] = [2]
                else:
                    # Default to one.
                    info['UIDeviceFamily'] = [1]

                info_plist_name = app_dir + b'Info.plist'

                if six.PY3:
                    info_plist_name = info_plist_name.decode('utf-8')

                h.writestr(info_plist_name, writePlistToString(info))
                h.writestr(
                    'iTunesMetadata.plist', writePlistToString({'Test':'Data'})
                )

        return zippath

    def test_bad_ipa(self):
        self.assertRaises(
            InvalidIPAError, IPAFile, self._create_ipa(create_info_plist=False)
        )

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
        name = u'ありがとう你好ברוכים'
        ipa = IPAFile(self._create_ipa(app_name=name))
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
    
    # Test the following methods.
    def test_ipa_is_universal(self):
        is_universal = None
        ipa = IPAFile(self._create_ipa(universal=True))
        is_universal = ipa.is_universal()
        self.assertEqual(is_universal, True)
    
    def test_ipa_is_iphone(self):
        is_iphone = None
        ipa = IPAFile(self._create_ipa(iphone=True))
        is_iphone = ipa.is_iphone()
        self.assertEqual(is_iphone, True)
    
    def test_ipa_is_ipad(self):
        is_ipad = False
        ipa = IPAFile(self._create_ipa(ipad=True))
        is_ipad = ipa.is_ipad()
        self.assertEqual(is_ipad, True)
   
    def test_ipa_is_not_universal(self):
        is_universal = None
        ipa = IPAFile(self._create_ipa(iphone=True))
        is_universal = ipa.is_universal()
        self.assertEqual(is_universal, False)
    
    def test_ipa_is_not_iphone(self):
        is_iphone = None
        ipa = IPAFile(self._create_ipa(ipad=True))
        is_iphone = ipa.is_iphone()
        self.assertEqual(is_iphone, False)
    
    def test_ipa_is_not_ipad(self):
        is_ipad = None
        ipa = IPAFile(self._create_ipa(iphone=True))
        is_ipad = ipa.is_ipad()
        self.assertEqual(is_ipad, False)
     
    def test_ipa_universal(self):
        ipa = IPAFile(self._create_ipa(universal=True))
        self.assertGreater(len(ipa.app_info['UIDeviceFamily']), 1)

    def test_get_bin_name_normal(self):
        ipa = IPAFile(self._create_ipa(app_name='A Name'))
        self.assertEqual('A Name', ipa.get_bin_name())

    def test_get_bin_name_no_display_name(self):
        ipa = IPAFile(
            self._create_ipa(app_name='A Name', bundle_display_name=False)
        )
        self.assertEqual('A Name', ipa.get_bin_name())

    def test_get_bin_name_full(self):
        ipa = IPAFile(self._create_ipa(app_name='A Name'))
        self.assertEqual(
            'Payload/A Name.app/A Name', ipa.get_bin_name(full=True)
        )

    def test_get_bin_name_full_no_display_name(self):
        ipa = IPAFile(self._create_ipa(app_name='A Name', 
                                       bundle_display_name=False))
        self.assertEqual(
            'Payload/A Name.app/A Name', ipa.get_bin_name(full=True)
        )

    def tearDown(self):
        for z in self._temp_files:
            try:
                with open(z, 'rb'):
                    pass
                rm(z)
            except IOError:
                continue