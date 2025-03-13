"""Setup script for ingit package."""

import boilerplates.setup


class Package(boilerplates.setup.Package):
    """Package metadata."""

    name = 'ingit'
    description = 'Tool for managing a large collection of repositories in git.'
    url = 'https://github.com/mbdevpl/ingit'
    license_str = 'GNU General Public License v3 or later (GPLv3+)'
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Version Control',
        'Topic :: Software Development :: Version Control :: Git',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: System :: Archiving :: Mirroring',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities',
        'Typing :: Typed']
    keywords = ['tools', 'vcs', 'repository management', 'git', 'submodules']
    entry_points = {'console_scripts': ['ingit = ingit.__main__:main']}


if __name__ == '__main__':
    Package.setup()
