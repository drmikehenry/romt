#!/usr/bin/env python3
# coding=utf-8

import romt.crate


def test_crate_prefix_from_name() -> None:
    assert romt.crate.crate_prefix_from_name("a") == "1"
