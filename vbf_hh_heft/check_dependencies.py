import shutil
import subprocess
from logging import info, critical
from rich.console import Console
from rich.table import Table

requirements = {
    "python": {
        "command": "python",
        "version_command": r"python -V | grep -E -o '[0-9]+\.[0-9]+\.[0-9]*'",
        "min_version": "3.9.0",
    },
    "cython": {"command": "cython", "version_command": r"cython -V | grep -E -o '[0-9]+\.[0-9]+\.[0-9]*'"},
    "make": {"command": "make", "version_command": r"make --version | grep -E -o '[[:space:]][0-9]\.[0-9]'"},
    "cmake": {"command": "cmake", "version_command": r"cmake --version | grep -E -o '[0-9]+\.[0-9]+\.[0-9]*'"},
    "meson": {"command": "meson", "version_command": "meson --version", "min_version": "1.4.0"},
    "ocaml": {"command": "ocamlc", "version_command": "ocamlc --version", "min_version": "4.02.3"},
    "gfortran": {"command": "gfortran", "version_command": "gfortran -dumpfullversion", "min_version": "9.5.0"},
    "gcc": {"command": "gcc", "version_command": "gcc -dumpfullversion", "min_version": "9.5.0"},
    "g++": {"command": "g++", "version_command": "g++  -dumpfullversion", "min_version": "9.5.0"},
    "mpi": {
        "command": "mpirun",
        "version_command": r"mpirun --version | grep -E -o '[0-9]+\.[0-9]+\.[0-9]*'",
    },
    "mpifort": {"command": "mpifort", "version_command": "mpifort  -dumpfullversion", "min_version": "9.5.0"},
    "mpicc": {"command": "mpicc", "version_command": "mpicc  -dumpfullversion", "min_version": "9.5.0"},
    "mpic++": {"command": "mpic++", "version_command": "mpic++  -dumpfullversion", "min_version": "9.5.0"},
}


def cmp_version(version1, version2):
    v1 = tuple(int(x) for x in version1.split("."))
    v2 = tuple(int(x) for x in version2.split("."))
    return v1 > v2


def check_dependencies(args):
    dep_results = {}
    for dep, data in requirements.items():
        if not args.mpi and "mpi" in dep:
            continue
        location = shutil.which(data["command"])
        if not location:
            dep_results[dep] = None
            continue
        version = subprocess.check_output(data["version_command"], shell=True).decode("utf-8").strip()
        if "min_version" in data:
            if cmp_version(version, data["min_version"]):
                ok = True
            else:
                ok = False
        else:
            ok = True
        dep_results[dep] = {
            "ok": ok,
            "version": version,
            "location": location,
        }
    return dep_results


def print_dep_table(dep_results):
    table = Table(title="VBF_HH_HEFT build dependencies", show_lines=True)
    table.add_column("Dependency")
    table.add_column("Req. Version")
    table.add_column("Found Version")
    table.add_column("Location")
    for dep, data in dep_results.items():
        if "min_version" in requirements[dep]:
            min_version = requirements[dep]["min_version"]
        else:
            min_version = "-"
        if data:
            if data["ok"]:
                style = "green"
            else:
                style = "red"
            table.add_row(dep, min_version, data["version"], data["location"], style=style)
        else:
            table.add_row(dep, min_version, "-", "Not Found", style="red")
    c = Console()
    c.print(table)


def print_dep_check(args):
    info(f"Checking for build dependencies...")
    dep_results = check_dependencies(args)
    print_dep_table(dep_results)
    if any(not data["ok"] for _, data in dep_results.items()):
        critical("Dependency check failed, see the table for which build dependencies are not available.")
    else:
        info(f"Dependency check passed.")
