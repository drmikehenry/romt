#!/usr/bin/env python
# coding=utf-8

import setuptools

NAME = "romt"

description = """
Romt (Rust Offline Mirror Tool) enables mirroring of Rust programming
language tools and crates for use in an offline context.
""".strip().replace("\n", " ")

keywords = "Rust mirror toolchain crates"


__version__ = None
for line in open("src/{}/cli.py".format(NAME), encoding="utf-8"):
    if line.startswith("__version__"):
        __version__ = line.split('"')[1]
        break

with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", encoding="utf-8") as f:
    requirements = f.read()

with open("dev-requirements.txt", encoding="utf-8") as f:
    dev_requirements = f.read()

setuptools.setup(
    name=NAME,
    version=__version__,
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    install_requires=requirements,
    extras_require={"dev": dev_requirements},
    entry_points={"console_scripts": ["{}={}.cli:main".format(NAME, NAME)]},
    description=description,
    long_description=long_description,
    keywords=keywords,
    url="https://github.com/drmikehenry/romt",
    author="Michael Henry",
    author_email="drmikehenry@drmikehenry.com",
    license="MIT",
    zip_safe=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
