``odfdump``
===========

Produces a textual dump of the contents of an OpenDocument Format file
or other archive.

This differs from tools like `odt2txt`_ in that the output consists of
the actual contents of the files within the ODF container
rather than an textual representation of the document.

This means that it presents a much more complete set of data,
including macros, formatting, and other details.

Information on binary files is limited to metadata
and hashes, including a SHA1 checksum.

.. _odt2txt: http://stosberg.net/odt2txt/


SETUP
-----

The ``odfdump`` script can make do with
the standard library's complement of modules.

It will attempt to make use of the `lxml`_ module
for XML pretty-printing,
but will fall back to standard library modules if that is unavailable.

So it should be possible to use ``odfdump`` with any Python 2.6 or later.

Earlier Pythons may work as well, but the script has not been tested with them.

If ``lxml`` is available, XML processing will be faster (> 3x)
and more robust in the face of incorrect or incomplete XML.

.. _lxml: http://pypi.python.org/pypi/lxml


USAGE
-----

``odfdump`` is mostly intended for use with version control systems like `git`_,
in order to identify changes between versions of OpenDocument Format files.

For example, with git 1.6.1 or later,
setting up a repo to use ``odfdump`` to produce diff input
can be accomplished by

-   adding lines to ``.git/config`` or equivalent
    to set the ``textconv`` option for the ``odf`` driver name::

        [diff "odf"]
            textconv=odfdump -D

-   associating the various ODF filetypes with the ``odf`` driver name
    by adding lines like the following to a ``.gitattributes`` file
    or ``.git/info/attributes``::

        *.odt diff=odf
        *.ods diff=odf
        *.odp diff=odf
        *.odb diff=odf

More info (based on using `odt2txt`_ instead of ``odfdump``)
is available from the `git wiki`_.

``odfdump`` is also suitable for use with other pkzip-formatted archives.
See the note about `filetype detection`_ in `BUGS, ISSUES and WARNINGS`_.

The ``-D`` option to ``odfdump`` instructs it
to omit the timestamp of each archive member.
OpenOffice seems to reset this timestamp for all members
whenever it saves a new version of a document.
Because of this, this piece of data is not meaningful
and shouldn't normally be displayed as part of a diff.
For this reason, I expect that ``-D`` should normally be passed
when generating a dump for the purposes of diffing.

.. _git: http://git-scm.com/
.. _git wiki: https://git.wiki.kernel.org/index.php/GitTips#Instructions_for_Git_1.6.1_or_later


OUTPUT FORMAT
-------------

Metadata Header
^^^^^^^^^^^^^^^

Output for each contained file will consist of a series of header lines
prefixed with the member filename and a colon followed by two spaces, e.g.::

    path/to/member/file:: date_time: 2010-10-12T21:32:24
    path/to/member/file:: file_size: 42
    path/to/member/file:: CRC: 4144865272

Each line contains a name/value pair delimited by an additional colon and space.

The metadata included in the header is that stored in the archive file itself,
plus the exception of the ``sha1`` element,
which is calculated by ``odfdump`` from the archive member's data.

Not all attributes are dumped.
The attributes which are dumped if present for a given archive member are:

-   date_time
-   comment
-   extra
-   file_size
-   CRC

The ``date_time`` will only be output if the ``-D`` option
has not been passed on the command line.

After these attributes, two more header lines will be output,
containing the member's SHA-1 hash and the detected filetype.
The detected filetype will be either
'binary', 'utf-8' (which subsumes ASCII), or 'unknown'.


Content section
^^^^^^^^^^^^^^^

After the header, printable files (those whose filetype is 'utf-8')
will have their content dumped.

The output for the content section is similar to that used for the header section.

Rather than name/value pairs, lines of the file are output.

The delimiter between filename and content is two colons and a space.

For example::

    path/to/member/file:  The first line of the file
    path/to/member/file:  The second line of the file
    path/to/member/file:  The third line of the file

A file is assumed to be printable if it is not detected as binary.
See _`filetype detection` for more information.

XML Files
^^^^^^^^^

The content of files which end in ``.xml``
will be passed through an XML tidying routine before being dumped.

This is intended to make the output more ``diff``-able
by splitting long lines containing multiple elements.

The presence of files containing poorly-formed XML
may result in errors because of this.
This should not be a problem for documents created with OpenOffice.


BUGS, ISSUES, and WARNINGS
--------------------------

-   Binary _`filetype detection` uses the same stupid algorithm as ``git diff``:
    scanning for nulls within the first 8000 bytes of the file.
    This works well enough with ASCII or UTF-8 text,
    but will fail spectacularly on files in e.g. UTF-16.

-   There are no plans to guarantee consistency between versions.
    So a dump created with an older version  of ``odfdump``
    shouldn't be compared with a dump created with a newer version.
    Even with the same version of ``odfdump``, dumps of the same document
    may differ because of different dependencies:
    ``odfdump`` will use different XML packages depending on
    what is locally installed.
    The `lxml`_ module will be used if it is locally available.

-   The output format is intended only for reading and comparison purposes.
    It is not intended to be a reversable translation of the original,
    even for archives which contain only text files.
    In particular, filenames containing ':' characters
    are not properly escaped.
    There will be additional ambiguities in dumps from files
    containing members with identical filenames.

-   I haven't yet checked to see if the order of members
    of an odf file is stable.
    ``odfdump`` currently does not sort the members before outputting them:
    the dump is done in archive file order.
    This means that comparison of dumps of identical documents
    may end up showing significant differences.


LICENSE
-------

``odfdump`` is licensed under the FreeBSD license.

See the file COPYING for details.
