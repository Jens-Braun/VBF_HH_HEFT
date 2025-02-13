#! /usr/bin/env python

import logging
import os

from rich.logging import RichHandler
import argparse
from vbf_hh_heft import install, print_dep_check, gen_libs

try:
    from rich_argparse import RichHelpFormatter
    help_formatter = RichHelpFormatter
except ImportError:
    help_formatter = argparse.HelpFormatter

if __name__ == '__main__':
    logging.basicConfig(level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
    root_parser = argparse.ArgumentParser(
        prog="VBF_HH_HEFT",
        description="Utility script for the Di-Higgs production in VBF in HEFT [arXiv:]",
        formatter_class=help_formatter,
    )
    root_parser.add_argument("-v", "--version", action="version", version="0.0.1")
    root_parser.add_argument("-l", "--loglevel", default="INFO", choices=("DEBUG", "INFO", "WARNING", "CRITICAL"))
    subparsers = root_parser.add_subparsers()

    install_parser = subparsers.add_parser("install",
                                           description="Install GoSam, Whizard and all dependencies required to run this repository",
                                           formatter_class=help_formatter
                                           )
    install_parser.add_argument("--prefix",
                                default=os.path.join(os.getcwd(), "local"),
                                help="Absolute location to install to [default: $PWD/local]")
    install_parser.add_argument("--mpi", action="store_true", help="Compile Whizard with MPI support")
    install_parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count(),  help="Number of jobs to use")
    install_parser.set_defaults(func=install)

    check_parser = subparsers.add_parser("check_deps",
                                         description="Check build dependencies required to compile this repository",
                                         formatter_class=help_formatter
                                         )
    check_parser.add_argument("--mpi", action="store_true", help="Check MPI compilers and library")
    check_parser.set_defaults(func=print_dep_check)

    gen_libs_parser = subparsers.add_parser("gen_libs")
    gen_libs_parser.add_argument("templates",
                                 help="Name of the templates in the 'Templates' folder to generate the libraries for",
                                 nargs="+"
                                 )
    gen_libs_parser.set_defaults(func=gen_libs)

    root_args = root_parser.parse_args()
    logging.getLogger().setLevel(root_args.loglevel)
    root_args.func(root_args)