#! /usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import logging
import os

from rich.logging import RichHandler
import argparse
from vbf_hh_heft import install, print_dep_check, gen_libs, integrate, purge, fit
from vbf_hh_heft.util import expand_parameters

try:
    from rich_argparse import RichHelpFormatter
    help_formatter = RichHelpFormatter
except ImportError:
    help_formatter = argparse.HelpFormatter

if __name__ == '__main__':
    logging.basicConfig(level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[
        RichHandler(show_path=False, rich_tracebacks=True),
    ])
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

    gen_libs_parser = subparsers.add_parser("gen_libs",
                                            description="Generate the process library for the given templates and store them under 'Libraries'",
                                            formatter_class=help_formatter
                                            )
    gen_libs_parser.add_argument("templates",
                                 help="Name of the templates in the 'Templates' folder to generate the libraries for",
                                 nargs="+"
                                 )
    gen_libs_parser.set_defaults(func=gen_libs)

    integrate_parser = subparsers.add_parser("integrate",
                                             description="Run the phase space integration for the given template and store the grid under 'grids'",
                                             formatter_class=help_formatter
                                             )
    integrate_parser.add_argument("template",
                                  help="Name of the template in the 'Templates' folder to integrate the phase space for"
                                  )
    integrate_parser.add_argument("-f", "--force", help="Force regeneration of the grids, even if they already exist", action="store_true")
    integrate_parser.add_argument("-p", "--parameters", help="TOML file containing the parameter values to set")
    integrate_parser.add_argument("-P",
                                  action="append",
                                  dest="cmd_parameters",
                                  default=[],
                                  metavar="parameter",
                                  help="Set a parameter to a specific value (Example: -Pc_V=1.1) (Can be used multiple times, overrides parameter file)"
                                  )
    integrate_parser.set_defaults(func=integrate)

    fit_parser = subparsers.add_parser("fit",
                                       help="Fit the total cross section to a given function of the model parameters")
    fit_parser.add_argument("template",
                              help="Name of the template in the 'Templates' folder to use"
                              )
    fit_parser.add_argument("-c", "--config", help="TOML file containing the configuration for the fit")
    fit_parser.set_defaults(func=fit)

    purge_parser = subparsers.add_parser("purge",
                                             description="Purge the grids and optionally the process library for the given template",
                                             formatter_class=help_formatter
                                             )
    purge_parser.add_argument("template",
                                  help="Name of the template in the 'Templates' folder to purge the grids for"
                                  )
    purge_parser.add_argument("-l", "--library", help="Also purge the process library", action="store_true")
    purge_parser.set_defaults(func=purge)

    try:
        import argcomplete
        argcomplete.autocomplete(root_parser)
    except ImportError:
        pass
    root_args = root_parser.parse_args()
    logging.getLogger().setLevel(root_args.loglevel)
    root_args.func(root_args)