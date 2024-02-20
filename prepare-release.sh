#!/bin/sh

die()
{
    echo "$@"
    exit 1
}

version=$(perl -ne \
    'if (/^\s*version\s*=\s*"((\d|\.)+)"/) { print "$1\n"; }' \
    pyproject.toml \
)

echo "Release version: $version"

echo "Cleanup directories..."
rm -rf dist build

echo "Make Linux executable..."
./make-exec-linux.sh || die "Could not build for Linux"

echo "Build egg and wheel..."
poetry build || die "Failed to build egg/wheel"

echo "twine check..."
twine check dist/romt-"$version"* || die "twine check failed"

echo "Create github release area..."
mkdir -p dist/github
cp dist/linux/romt dist/github/romt-"$version"-x86_64-linux

echo
echo "** Remaining manual steps:"
echo
echo "On Windows machine:"
echo "  make-exec-windows.bat"
printf '  copy %s %s\n' \
    'dist\windows\romt.exe' \
    'dist\github\romt-'"$version"'-x86_64-windows.exe'
echo
echo "Tag and push:"
echo "  git tag -am 'Release v$version.' v$version"
echo "  git push; git push --tags"
echo
echo "Upload to PyPI:"
echo "  twine upload dist/romt-$version.tar.gz" \
    "dist/romt-$version-py3-none-any.whl"
echo
echo "Create Github release for $version from dist/github/ tree."
