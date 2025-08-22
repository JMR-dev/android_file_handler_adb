#!/bin/bash
poetry lock
poetry install
poetry run pyinstaller --onefile src/main.py --distpath dist --name android-file-handler-windows