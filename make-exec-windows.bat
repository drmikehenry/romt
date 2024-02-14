@echo off

pyinstaller ^
    --onefile ^
    --name romt ^
    --distpath dist\windows ^
    --specpath build\windows ^
    --workpath build\windows ^
    --add-data="../../README.rst;romt" ^
    --log-level WARN ^
    romt-wrapper.py
