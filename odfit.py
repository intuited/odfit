#!/usr/bin/env python
"""Creates textual dumps of OpenDocument Format files and other zip archives.

This includes .odt's, .odb's, or really any file which is an archive.

Normalizes XML files by parsing and pretty-printing them.
"""
# Licensed under the FreeBSD license.
# See the file COPYING for details.

from functools import partial
import logging
from sys import stderr


# logging

def make_logger(name, level=logging.DEBUG, strm=stderr):
    import logging
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(strm=stderr)
    logger.addHandler(handler)
    logger.handler = handler
    return logger
warnings = make_logger('warnings')


# Filetype detection

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


# XML Processing

class XMLParseError(Exception):
    """Raised in response to errors when parsing an archived XML file."""
    pass

def tidy_xml(xml_file):
    """Returns a tidied version of the xml in ``xml_file``.

    Prefers ``lxml.etree`` for speed and robustitude;
    falls back to ``xml.etree.ElementTree``.
    """
    try:
        from lxml.etree import parse, tostring
        from functools import partial
        pretty_print = partial(tostring, pretty_print=True)
    except ImportError:
        from xml.dom.minidom import parse
        from operator import methodcaller
        pretty_print = methodcaller('toprettyxml', indent='  ')
    try:
        tree = parse(xml_file)
    except Exception as e:
        # The xml libraries don't make it clear
        # what exceptions their ``parse`` functions raise,
        # so we catch everything.
        # TODO: re-raise anything that's related to the underlying file.
        raise XMLParseError("XML parse routine raised error '{0}'"
                            .format(e))
    return pretty_print(tree)

def is_xml(archive, info):
    """Indicates if the file in ``archive`` identified by ``info`` is XML."""
    return info.filename.endswith('.xml')


# metadata generation and formatting

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

class FormattedZipInfo(object):
    """Proxies a ZipInfo object, providing formatted versions of its data."""
    def __init__(self, info):
        self._info = info
    def __getattr__(self, attr):
        return getattr(self._info, attr)
    @property
    def date_time(self):
        return ('{0:02}-{1:02}-{2:02}T{3:02}:{4:02}:{5:02}'
                .format(*self._info.date_time))

# TODO: The sha1 and filetype should be part of this sequence.
#       Actually this should be a class with interdependent properties
metadata_items = ('date_time', 'comment', 'extra', 'file_size', 'CRC')

def iterate_metadata(info, member,
                     metadata_items=metadata_items,
                     hash_=sha1_hash):
    """Yields (name, value) tuples of formatted metadata information.

    The attribs of the ``info`` object are filtered through a
    FormattedZipInfo object.
    """
    from functools import partial
    from itertools import chain
    drop_empties = frozenset(('comment', 'extra')).__contains__
    info = FormattedZipInfo(info)
    get = partial(getattr, info)
    item_strings = ((attr, str(get(attr))) for attr in metadata_items)
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


# content formatting

def format_content(info, line):
    """Formats a line of content for dumping."""
    assert line.find('\n') == -1
    return '{0}:: {1}'.format(info.filename, line)


# dumping of each archive member

# Written for use in `detail` to allow a common interface between
# tidied XML files (as StringIO instances) and other files.
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


# dumping entire archive

def archive_details(filename, detail=detail):
    """Yields annotated lines of files and/or metadata from the archive.

    The function argument ``detail`` can be provided
    to customize formatting of archive members.
    """
    from zipfile import ZipFile
    from itertools import chain
    from contextlib import closing
    with closing(ZipFile(filename, 'r')) as archive:
        infos = archive.infolist()
        details = (detail(archive, info) for info in infos)
        for file_detail in details:
            for line in file_detail:
                yield line


# do it!

def main():
    import optparse
    from functools import partial

    parser = optparse.OptionParser(
        "usage: %prog [-h] FILENAME",
        description=__doc__
        )
    parser.add_option('-D', '--no-dump-date',
        help="Do not dump the date of each archive member.",
        action='append_const',
        const='date_time',
        dest='nodump',
        default=[],
        )

    opts, args = parser.parse_args()

    if len(args) != 1:
        parser.error("The document FILENAME"
                     " must be given as the only argument.")
    filename = args[0]

    md_items_to_dump = [i for i in metadata_items if not i in opts.nodump]
    iterate_metadata_nodump = partial(iterate_metadata,
                                      metadata_items=md_items_to_dump)

    detail_nodump = partial(detail, iterate_metadata=iterate_metadata_nodump)

    lines = archive_details(filename, detail=detail_nodump)

    for line in lines:
        print line

if __name__ == '__main__':
    exit(main())
