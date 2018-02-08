"""This is setup.py file for ingit."""

import setup_boilerplate


class Package(setup_boilerplate.Package):

    """Package metadata."""

    name = 'ingit'
    description = 'git repository collection management tool'
    download_url = 'https://github.com/mbdevpl/ingit'
    license_str = 'GNU General Public License v3 or later (GPLv3+)'
    classifiers = [
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Version Control',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: System :: Archiving :: Mirroring',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities'
        ]
    keywords = ['tools', 'vcs', 'repository management', 'git', 'submodules']
    entry_points = {'console_scripts': ['ingit = ingit.__main__:main']}


if __name__ == '__main__':
    Package.setup()
