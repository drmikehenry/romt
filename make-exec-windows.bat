pyinstaller ^
    --onefile ^
    --name romt ^
    --distpath dist\windows ^
    --specpath build\windows ^
    --workpath build\windows ^
    --hidden-import pkg_resources.py2_warn ^
    --add-data="../../README.rst;romt" ^
    romt-wrapper.py
