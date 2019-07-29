# AirStuff

This small utility helps the poor guys who need to import publications into the AIR (Archivio Istituzionale della Ricerca). By default the program points to the UniMI database https://air.unimi.it/

It automatizes the extraction of: title, full authors list, list of authors for a given institution (see -h), keyword from the address of the inspirehep web page.

## Install
The program needs gtk and its dependency, for example:

   * gcc or a c++ compiler
   * cairo: https://pycairo.readthedocs.io/en/latest/getting_started.html
   * gobject
   * cairo-gobject

Then possibly in a virtualenv:

    pip install airstuff

This can also help you to install dependencies.

## Run it
Just run:

    airstuff.py

Presently it is suggested to precompute the list of publications from air and inspire with:

    python airstuff/inspire.py --max-results 1000 --out inspire.txt --workers 15

and

    python airstuff/air.py --max-results 1000 --workers 20 --out air.txt

The last do not terminate. Terminate it when it stops to find results.

Then you can run with:

    python airstuff/app.py --air-file air.txt  --inspire-file inspire.txt

For other options (as adding additional authors) try `-h` option.

# Old version

    parse_inspire.py

![screenshot](https://raw.githubusercontent.com/wiso/AirStuff/master/screenshot.png)
