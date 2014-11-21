from distutils.core import setup

setup(
    name='libipa',
    version='0.0.4',
    author='Andrew Udvare',
    author_email='audvare@gmail.com',
    packages=['ipa'],
    url='https://github.com/Tatsh/libipa',
    license='LICENSE.txt',
    description='Library to read IPA files (iOS application archives).',
    long_description='No description.',
    install_requires=[
        'biplist>=0.7',
        'six>=1.7.3',
    ],
)
