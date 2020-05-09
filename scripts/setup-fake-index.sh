#!/bin/bash

die()
{
    echo "$@"
    exit 1
}

mkdir_cd()
{
    { mkdir "$1" && cd "$1"; } || die "failed to mkdir/cd to $1"
}

make_branch()
{
    git branch -f "$@" || die "could not make branch with args:" "$@"
}

checkout()
{
    git checkout "$@" || die "could not checkout with args:" "$@"
}

mkdir_cd fake-index
git init

COMMIT_FIRST30='09614655eb317dd9a515aec42b118c55bcead40c'
git fetch https://github.com/rust-lang/crates.io-index.git \
  "$COMMIT_FIRST30":first30 || die "Could not fetch $COMMIT_FIRST30"

make_branch num30 first30
make_branch num20 num30~10
make_branch num10 num20~10

git checkout num30
GIT_EDITOR='sed -i -e "2,19s/^pick/fixup/"' git rebase -i HEAD~30 ||
    die "failed to rebase num30"

git checkout num20
GIT_EDITOR='sed -i -e "2,9s/^pick/fixup/"' git rebase -i HEAD~20 ||
    die "failed to rebase num20"

make_branch master num10
make_branch step1 num10~9
make_branch step2 num10~5
make_branch step3 num10
make_branch step4 num20~9
make_branch step5 num20~5
make_branch step6 num20
make_branch step7 num30~9
make_branch step8 num30~5
make_branch step9 num30

make_branch master step1
