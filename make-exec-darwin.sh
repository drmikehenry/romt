#!/bin/sh

echo 'Completely untested on Mac; this probably fails somehow.'

target=darwin

pyinstaller \
    --onefile \
    --name romt \
    --distpath dist/$target \
    --specpath build/$target \
    --workpath build/$target \
    --add-data="../../README.rst:romt" \
    --log-level WARN \
    romt-wrapper.py
