#!/usr/bin/env bash
#MISE description="Clipboard -> new problem folder(s) -> generate tests"
pbpaste | python tools/new_problem.py && python tools/gen_tests.py
