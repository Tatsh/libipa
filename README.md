# Library to read IPA files

[![Build Status](https://travis-ci.org/Tatsh/libipa.svg?branch=master)](https://travis-ci.org/Tatsh/libipa)

Compatible with Python 2.7 and 3.4 and above. Python 3.3 is not supported.

## Installation
```
pip install libipa
```

## Usage

See below.

Note that `IPAFile` is just a subclass of `ZipFile` from the [`zipfile`](https://docs.python.org/2/library/zipfile.html)  module. On the object will be the attribute `app_info` which contains all the information read from `Payload/app_name.app/Info.plist` where `app_name` is the application's name.

```
>>> from ipa import IPAFile
>>> ipa = IPAFile('Chrome 37.2062.52.ipa')
>>> ipa.app_info['CFBundleIdentifier']
'com.google.chrome.ios'
>>> ipa.is_universal()
True
```
