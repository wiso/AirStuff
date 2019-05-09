import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="AirStuff",
    version="0.0.3",
    author="Ruggero Turra",
    author_email="ruggero.turra@cern.ch",
    description="Utilities to speedup AIR (Archivio Istituzionale della Ricerca) document upload, for HEP users",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wiso/airstuff",
    packages=setuptools.find_packages(),
    install_requires=['bibtexparser', 'requests', 'bs4', 'xmltodict'],
    entry_points={'console_scripts': ['parse_inspire=airstuff.parse_inspire:main'], },
    python_requires='>=3.4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
    ],
)
