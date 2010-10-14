``odfdump``
===========




BUGS, ISSUES, and WARNINGS
--------------------------

-   Binary filetype detection uses the same stupid algorithm as ``git diff``:
    scanning for nulls within the first 8000 bytes of the file.
    This works well enough with ASCII or UTF-8 text,
    but will fail spectacularly on files in e.g. UTF-16.

-   There's no guarantee of consistency between versions of ``odfdump``.
    So a dump created with an older version shouldn't be compared
    with a dump created with a newer version.
