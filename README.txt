``odfit``
===========

Produces textual information based on the contents of
OpenDocument Format files and other archives.

The information produced includes metadata like
the names, uncompressed size, and modification times of archive members.

A checksum is calculated, and basic filetype detection performed on each.

For each member determined to contain UTF-8 text,
the lines in the file are output.

``odfit`` is similar in purpose but different in operation,
and in its level of detail,
to tools like `odt2txt`_ which output a text-mode
rendering of the archive as a document.

This means that it presents a much more complete set of data,
including embedded macros, formatting, and other details.

Information on binary files is limited to metadata
and hashes, including a SHA1 checksum.

XML files will be pretty-printed
so as to make their contents more readily ``diff``-able.

.. _odt2txt: http://stosberg.net/odt2txt/


SETUP
-----

The ``odfit`` script can make do with
the standard library's complement of modules.

It will attempt to make use of the `lxml`_ package
for XML pretty-printing,
but will fall back to standard library modules if necessary.

So it should be possible to use ``odfit`` with any Python 2.6 or later,
without requiring installation.

This means that the executable module file ``odfit.py``
can be distributed with source repos with some reliability.

Pythons older than 2.6 may also work,
but the script has not been tested with them.

If ``lxml`` is available, XML processing will be faster (> 3x)
and more robust when dealing with incorrect or incomplete XML.

In addition to running the script ``odfit.py`` directly,
the module can be installed from source
or via `PyPI`_.
This will cause an equivalent script to be installed system-wide,
enabling the command ``odfit`` on the system path.

.. _lxml: http://pypi.python.org/pypi/lxml
.. _PyPI: http://pypi.python.org/pypi/odfit


USAGE
-----

``odfit`` is a command-line tool.

To get a listing of the members of an archive, run e.g. ::

    $ odfit some_file.odt

For a typical OpenOffice document, this will produce many lines of data.

``odfit`` is mostly intended for use with version control systems like `git`_,
in order to identify changes between versions of OpenDocument Format files.

For example, with git 1.6.1 or later,
setting up a repo to use ``odfit`` to generate ``git diff`` listings
can be accomplished by

-   adding lines to ``.git/config`` or equivalent
    to set the ``textconv`` option for the ``odf`` driver name::

        [diff "odf"]
            textconv=odfit -D

-   associating the various ODF filetypes with the ``odf`` driver name
    by adding lines like the following
    to a ``.gitattributes`` file in the repo working tree
    or in ``.git/info/attributes``::

        *.odt diff=odf
        *.ods diff=odf
        *.odp diff=odf
        *.odb diff=odf

The ``-D`` option to ``odfdump`` instructs it
to omit the timestamp of each archive member.
OpenOffice seems to reset this timestamp for all members
whenever it saves a new version of a document.
Because of this, this piece of data is not meaningful
and shouldn't normally be displayed as part of a diff.
For this reason, I expect that ``-D`` should normally be passed
when generating a dump for the purposes of diffing.

More info (based on using `odt2txt`_ instead of ``odfit``)
is available from the `git wiki`_.

``odfit`` is also suitable for use with other pkzip-formatted archives.
See the note about `filetype detection`_ in `BUGS, ISSUES, and WARNINGS`_.

.. _git: http://git-scm.com/
.. _git wiki: https://git.wiki.kernel.org/index.php/GitTips#Instructions_for_Git_1.6.1_or_later


OUTPUT FORMAT
-------------

Metadata Header
^^^^^^^^^^^^^^^

Output for each contained file will consist of a series of header lines,
each prefixed with the member filename and a colon followed by two spaces.
For example::

    path/to/member/file:  date_time: 2010-10-12T21:32:24
    path/to/member/file:  file_size: 42
    path/to/member/file:  CRC: 4144865272

Each line contains a name/value pair delimited by an additional colon and space.

The metadata included in the header is that stored in the archive file itself,
plus the exception of the ``sha1`` element,
which is calculated by ``odfit`` from the archive member's data.

Not all member attributes are dumped.
The attributes which are dumped if nonempty for a given archive member are:

-   timestamp: ``date_time``
-   ``comment``
-   ``extra``
-   ``file_size``
-   CRC-32 checksum: ``CRC``

The timestamp will only be output if the ``-D`` option
has not been passed on the command line.

After these attributes, two more header lines will be output,
containing the member's SHA-1 hash and the detected filetype.
The detected filetype will be either
``binary``, ``utf-8`` (which subsumes ASCII), or ``unknown``.


Content section
^^^^^^^^^^^^^^^

After the header, printable files (those whose filetype is ``utf-8``)
will have their content dumped.

The output for the content section
is similar to that used for the header section.

Rather than name/value pairs, lines of the file are output.

The delimiter between filename and content is two colons and a space.

For example::

    path/to/member/file:: The first line of the file
    path/to/member/file:: The second line of the file
    path/to/member/file:: The third line of the file

A file is assumed to be printable if it is not detected as binary.
See `filetype detection`_ for more information.

XML Files
^^^^^^^^^

The content of files whose names end in ``.xml``
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
    but will falsely detect as binary files in encodings such as UTF-16.

-   There are no plans to guarantee consistency between versions.
    So a dump created with an older version  of ``odfit``
    shouldn't be compared with a dump created with a newer version.
    Even with the same version of ``odfit``, dumps of the same document
    may differ because of different dependencies:
    ``odfit`` will use different XML packages depending on
    what is locally installed, and the pretty-printed output of XML files
    will vary depending on the XML package used.
    The `lxml`_ package will be used if it is locally available.

-   The output format is intended only for reading and comparison purposes.
    It is not intended to be a reversable translation of the original,
    even for archives which contain only text files.
    In particular, filenames containing ':' characters
    are not properly escaped.
    There will be additional ambiguities in dumps from files
    containing members with identical filenames.

-   I haven't yet checked to see if the order of members
    of an odf file is stable.
    ``odfit`` currently does not sort the members before outputting them:
    member output is done in archive file order.
    This means that comparison of dumps of equivalent documents
    may end up showing significant differences.

-   There are many performance optimizations which could be put in place,
    particularly if the script were to be reworked as a diff routine.
    Having knowledge of both of the compared documents would allow
    ``odfit`` to, for example, only output XML for files which have changed.
    It's also very unlikely that a SHA-1 comparison
    will detect changes that a CRC-32 comparison does not.

-   ``odfit`` is not tested with Python versions other than 2.6.
    This means that there's little guarantee
    that it will work on any particular system,
    since 2.5 and even 2.4 are not uncommon in the field.

LICENSE
-------

``odfit`` is copyright 2010 by Ted Tibbetts
and is licensed under the FreeBSD license.

See the file COPYING for details.
