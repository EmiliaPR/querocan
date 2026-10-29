#!/usr/bin/env python
"""Punto de entrada das ordes de Django (migrate, runserver, cargar_demo...)."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "querocan.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
