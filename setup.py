# Require setuptools for script installation
try:
    from setuptools import setup
    raise ImportError
except ImportError:
    from sys import stderr
    print >> stderr, (
        'Sorry, you must install the ``setuptools`` module'
        ' in order to install this package.\n'
        '``setuptools`` can be installed with the command\n'
        '    easy_install setuptools\n'
        'or by download from <http://pypi.python.org/pypi/setuptools>.\n'
        )
    raise


from textwrap import dedent, fill

def format_desc(desc):
    if len(desc) > 200:
        raise ValueError("Description cannot exceed 200 characters.")
    return fill(dedent(desc), 200)

def format_classifiers(classifiers):
    return dedent(classifiers).strip().split('\n')

def split_keywords(keywords):
    return dedent(keywords).strip().replace('\n', ' ').split(' ')

def file_contents(filename):
    with open(filename) as f:
        return f.read()

setup(
    name = "odfdump",
    version = "0.6",
    author = "Ted Tibbetts",
    author_email = "intuited@gmail.com",
    url = "http://github.com/intuited/odfdump",
    description = format_desc("""
        Creates textual dumps of OpenDocument Format files and other zip archives.
        """),
    long_description = file_contents('README.txt'),
    classifiers = format_classifiers("""
        Development Status :: 4 - Beta
        Intended Audience :: Developers
        License :: OSI Approved :: BSD License
        Operating System :: OS Independent
        Programming Language :: Python
        Programming Language :: Python :: 2
        Topic :: Software Development :: Libraries :: Python Modules
        Topic :: Utilities
        Topic :: System :: Archiving
        """),
    keywords = split_keywords("""
        xml opendocument odt ods odb odp openoffice archive zip dump diff
        """),
    packages = ['odfdump'],
    package_dir = {'odfdump': ''},
    entry_points = {
        'console_scripts': ['odfdump = odfdump:main']
        },
    )
