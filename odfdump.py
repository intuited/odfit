#!/usr/bin/env python
"""Creates dumps of files in OpenDocument Format.

This includes .odt's, .odb's, or really any file which is an archive.

Normalizes xml files by parsing and dumping them with ``lxml.etree``.

Normalizes non-utf-8 files by converting them to that encoding.
"""
from functools import partial
import logging
from sys import stderr

def make_logger(name, level=logging.DEBUG, strm=stderr):
    import logging
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(strm=stderr)
    logger.addHandler(handler)
    logger.handler = handler
    return logger
warnings = make_logger('warnings')


def is_in_charset(string, charset='ascii'):
    try:
        string.decode(charset)
    except UnicodeDecodeError:
        return False
    return True

is_utf8 = partial(is_in_charset, charset='utf-8')


class FiletypeDetector(object):
    """Scans into a file to determine its nature.

    A call on an instantiated FiletypeDetector object
    returns 'binary', 'utf-8', or 'unknown' depending on the file contents.

    ``how_far`` is used as a key into ``self.thoroughness``
    to determine how many bytes into the file should be scanned.
    """
    @property
    def thoroughness(self):
        """How far into the file to scan for stuff."""
        return {'abide': 800,
                'mellow': 8000, # what ``git diff`` does
                'strict': None, # scan the whole thing
                }

    def __call__(self, file_, how_far='mellow'):
        chunk_size = 8192
        left_to_scan = self.thoroughness[how_far]
        scan_to_the_end = (self.thoroughness[how_far] is not None)
        file_.seek(0)
        while True:
            chunk = file_.read(chunk_size)
            if not chunk:
                break
            if '\000' in chunk:
                return 'binary'
            if not is_utf8(chunk):
                return 'unknown'
            if not scan_to_the_end:
                left_to_scan -= len(chunk)
                if left_to_scan < 0 and thoroughness[how_far]:
                    break
        return 'utf-8'


class XMLParseError(Exception):
    pass

def tidy_xml(xml_file):
    """Returns a tidied version of the xml in ``xml_file``."""
    from lxml import etree
    try:
        tree = etree.parse(xml_file)
        return etree.tostring(tree, pretty_print=True)
    except etree.XMLSyntaxError as e:
        raise XMLParseError("lxml.etree.parse reported parse error '{0}'"
                            .format(e))

def is_xml(archive, info):
    """Indicates if the file in ``archive`` identified by ``info`` is XML."""
    return info.filename.endswith('.xml')

def format_header(info, content):
    """Format ``content`` as a header for the file identified by ``info``.

    ``content`` must not contain any newlines.
    """
    assert content.find('\n') == -1
    return '{0}:  {1}'.format(info.filename, content)


def progressive_hash(hash_, file_, chunk_size=1048576):
    """Updates ``hash_`` with reads from ``file_``."""
    while True:
        chunk = file_.read(chunk_size)
        if not chunk:
            return hash_.hexdigest()
        hash_.update(chunk)


def sha1_hash(info, member):
    """Returns a (name, hash) pair: ``name`` identifies the algorithm."""
    from hashlib import sha1
    member.seek(0)
    return ('sha1', progressive_hash(sha1(), member))


def iterate_metadata(info, member, hash_=sha1_hash):
    """Yields (name, value) tuples of metadata information."""
    from functools import partial
    from itertools import chain
    info_items = ('date_time', 'comment', 'extra', 'file_size', 'CRC')
    drop_empties = frozenset(('comment', 'extra')).__contains__
    get = partial(getattr, info)
    item_strings = ((attr, str(get(attr))) for attr in info_items)
    item_strings = chain(item_strings, (hash_(info, member),))
    return (pair for pair in item_strings
                 if pair[1] or not drop_empties(pair[0]))

def format_metadata(pair):
    """Formats a (name, value) pair as a string for header inclusion.
    
    Any newlines in ``name`` or ``value`` are replaced with two spaces.
    """
    strings = (str(element) for element in pair)
    joined_lines = (s.replace('\n', '  ') for s in strings)
    return '{0}: {1}'.format(*joined_lines)

def format_content(info, line):
    """Formats a line of content for dumping."""
    assert line.find('\n') == -1
    return '{0}:: {1}'.format(info.filename, line)

# Written for use in `detail` to allow a common interface between
# tidied XML files and other files.
class ResettableZipEntry(object):
    """Adds ``seek(0)`` to the ZipExtFile API.
    
    Call ``ResettableZipEntry(archive, info)``
    instead of ``archive.open(info)``.
    """
    def __init__(self, archive, info):
        self._archive = archive
        self._info = info
        self._zef = archive.open(info)
    def seek(self, position):
        if position != 0:
            raise ValueError("SeekableZipEntry only supports seeking"
                             " to position 0.")
        self._zef.close()
        self._zef = self._archive.open(self._info)
    def __iter__(self):
        return iter(self._zef)
    def __getattr__(self, attr):
        return getattr(self._zef, attr)

def detail(archive, info,
           format_header=format_header,
           iterate_metadata=iterate_metadata,
           format_metadata=format_metadata,
           hash_=sha1_hash,
           is_xml=is_xml,
           tidy_xml=tidy_xml,
           FiletypeDetector=FiletypeDetector,
           format_content=format_content,
           ):
    """Yields lines of detail from the file identified by ``info``.

    The first set of lines contains metadata about the file,
    including a checksum.

    These lines begin with the filename, followed by ':: '.

    For binary files, no further lines are yielded.

    For text files, subsequent lines contain lines of the file
    with the filename + ": " prepended.

    XML files are tidied before being output.

    For info on the keyword arguments,
    see the docstrings for the functions that implement their defaults.
    """
    from StringIO import StringIO
    from contextlib import closing

    with closing(ResettableZipEntry(archive, info)) as member:
        for md in iterate_metadata(info, member):
            yield format_header(info, format_metadata(md))

        if is_xml(archive, info) and info.file_size > 2:
            member.seek(0)
            try:
                member = StringIO(tidy_xml(member))
            except XMLParseError as e:
                warnings.warning("Error parsing XML in member '{0}': {1}; "
                                 "XML tidying aborted."
                                 .format(info.filename, e))

        member.seek(0)
        filetype = FiletypeDetector()(member)

        yield format_header(info, format_metadata(('filetype', filetype)))

        if filetype == 'utf-8':
            member.seek(0)
            for line in member:
                yield format_content(info, line.rstrip('\n'))


def archive_details(filename, options=object()):
    """Yields annotated lines of files and/or metadata from the archive."""
    from zipfile import ZipFile
    from itertools import chain
    from contextlib import closing
    with closing(ZipFile(filename, 'r')) as archive:
        infos = archive.infolist()
        details = (detail(archive, info) for info in infos)
        for file_detail in details:
            for line in file_detail:
                yield line
        

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description=__doc__
        )
    parser.add_argument('filename')
    options = parser.parse_args()
    if hasattr(options, 'filename'):
        for line in archive_details(options.filename, options):
            print line

if __name__ == '__main__':
    exit(main())
