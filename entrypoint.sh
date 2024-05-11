#!/bin/bash

# This is run as the `ENTRYPOINT` for the `Dockerfile` used to build for Linux.

poetry install && poetry run nox -s build
