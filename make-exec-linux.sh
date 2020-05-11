#!/bin/sh

target=linux

pyinstaller \
    --onefile \
    --name romt \
    --distpath dist/$target \
    --specpath build/$target \
    --workpath build/$target \
    --hidden-import pkg_resources.py2_warn \
    --add-data="../../README.rst:romt" \
    --log-level WARN \
    romt-wrapper.py
