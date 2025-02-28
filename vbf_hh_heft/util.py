import os.path
import re
import subprocess
from logging import info, warning, critical
import sys
import pathlib
import json
import itertools

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        critical("Python versions older than 3.11 require the 'toml' package to be installed")
        sys.exit(1)
from rich.live import Live
from rich.spinner import Spinner
from rich.console import Console

console = Console()


def execute_alt_screen(task_description, commands, logfile=None, env=os.environ):
    failed = False
    failed_command = ""
    return_code = 0
    cmd_output = [
        f"Running task '{task_description}' with commands:\n",
        *["    " + command + "\n" for command in commands],
        "-" * 80 + "\n",
    ]
    with console.screen():
        spinner = Spinner("dots", text="[bold red]" + task_description + "[/bold red]", style="bold green")
        with Live(spinner, console=console, transient=True) as live:
            for command in commands:
                with subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, env=env
                ) as proc:
                    for line in proc.stdout:
                        line = line.decode("utf-8")
                        live.console.print(line, end="")
                        cmd_output.append(line)
                        live.refresh()
                    if proc.returncode and proc.returncode != 0:
                        failed = True
                        failed_command = command
                        return_code = proc.returncode
                        break
    if logfile:
        with open(logfile, "w") as file:
            file.writelines(cmd_output)
    if failed:
        with open(os.path.join(get_src_location(), "vbf_hh_heft.log"), "w") as file:
            file.writelines(cmd_output)
        critical(f"Command {failed_command} failed with code {return_code}, output written to 'vbf_hh_heft.log'.")
        sys.exit(1)


def get_src_location():
    return pathlib.Path(os.path.realpath(__file__)).parent.parent


def get_install_info():
    if not os.path.exists(os.path.join(get_src_location(), "installation.json")):
        critical(f"Unable to find 'installation.json', did you run './vbf_hh_heft.py install' yet?")
        sys.exit(1)
    with open(os.path.join(get_src_location(), "installation.json")) as file:
        installation = json.load(file)
    return installation


def setup_env():
    installation = get_install_info()
    env = os.environ.copy()
    if "PATH" in env:
        env[
            "PATH"
        ] = f"{os.path.join(installation['prefix'], 'bin/GoSam')}:{os.path.join(installation['prefix'], 'bin')}:{env['PATH']}"
    else:
        env[
            "PATH"
        ] = f"{os.path.join(installation['prefix'], 'bin/GoSam')}:{os.path.join(installation['prefix'], 'bin')}"
    if "LD_LIBRARY_PATH" in env:
        env[
            "LD_LIBRARY_PATH"
        ] = f"{os.path.join(installation['prefix'], 'lib')}:{os.path.join(installation['prefix'], 'lib64')}:{env['LD_LIBRARY_PATH']}"
    else:
        env[
            "LD_LIBRARY_PATH"
        ] = f"{os.path.join(installation['prefix'], 'lib')}:{os.path.join(installation['prefix'], 'lib64')}"
    with open(os.path.join(installation["prefix"], "share", "Rivet", "rivetenv.sh"), "r") as file:
        python_path = re.findall(r"export PYTHONPATH=\"([^\"\n]*)\"", file.read())[0]
    env["PYTHONPATH"] = python_path
    return env


def parse_processes(sindarin):
    processes = {}
    process_declarations = re.findall(r"(?<=\n)[^#\n]*(?=process)(.*)", sindarin)
    processes_set = set()
    for declaration in process_declarations:
        match = re.findall(r"process\s+(?:([^=\s]+)(?:_BORN|_REAL|_VIRTUAL|_DGLAP)|([^=\s]+))", declaration)[-1]
        if match[0] == "":
            processes_set.add(match[1])
        else:
            processes_set.add(match[0])
    for process_name in processes_set:
        declarations = list(
            filter(
                lambda decl: re.search(
                    r"process\s+(?:(" + process_name + ")(?:_BORN|_REAL|_VIRTUAL|_DGLAP)|(" + process_name + r"))", decl
                )
                is not None,
                process_declarations,
            )
        )
        d = {}
        for declaration in declarations:
            match = re.search(r"nlo_calculation\s*=\s*(\w+)", declaration)
            if match:
                d[match.group(1)] = {"name": f"{process_name}_{match.group(1).upper()}"}
            else:
                d["born"] = {"name": f"{process_name}"}
        processes[process_name] = d

        n_events_global_match = re.search(r"\n[\t ]*n_events\s*=\s*(\d+)", sindarin)
        if n_events_global_match:
            n_events = int(n_events_global_match.group(1))
        else:
            n_events = None

    for process_name, process_data in processes.items():
        for component, data in process_data.items():
            int_decl = re.search(
                r"(?<=\n)[^#\n]*integrate[ \t]*\([ \t]*" + data["name"] + r"[ \t]*\).*", sindarin
            ).group(0)
            int_match = re.search(r"iterations\s*=\s*((?:\d+:\d+(?::\"\w+\")?,?\s*)*)", int_decl).group(1)
            n_iter = sum([int(stage.split(":")[0]) for stage in int_match.split(",")])
            data["n_iter"] = n_iter

            sim_decl = re.search(r"(?<=\n)[^#\n]*simulate[ \t]*\([ \t]*" + data["name"] + r"[ \t]*\).*", sindarin)
            if sim_decl:
                sim_decl = sim_decl.group(0)
                sample_match = re.search(r"\$sample\s*=\s*\"([^\"\n]*)\"", sim_decl).group(1)
                data["sample"] = sample_match
                n_events_match = re.search(r"\$n_events\s*=\s*(\d+)", sim_decl)
                if n_events_match is None:
                    if n_events is None:
                        data["n_events"] = 0
                    else:
                        data["n_events"] = n_events
                else:
                    data["n_events"] = n_events_match

    return processes


def expand_parameters(file, cmd_params):
    param_dict = {}
    if file:
        try:
            with open(file, "rb") as file:
                param_dict = tomllib.load(file)
        except FileNotFoundError as e:
            critical(f"Unable to load parameter config file {file}: {e}")
            sys.exit(1)
        if "param_list" in param_dict:
            param_list = param_dict["param_list"]
        else:
            param_list = []
        if "parameters" in param_dict:
            param_dict = param_dict["parameters"]
    else:
        param_list = []
    for param, value in param_dict.items():
        if isinstance(value, list):
            continue
        elif isinstance(value, float):
            param_dict[param] = [value]
        elif isinstance(value, int):
            param_dict[param] = [float(value)]
        elif isinstance(value, str):
            range_params = value.split(":")
            if len(range_params) == 1:
                param_dict[param] = float(range_params[0])
            elif len(range_params) == 3:
                range_params = [float(x) for x in range_params]
                param_dict[param] = [
                    range_params[0] + i * range_params[2]
                    for i in range(0, int((range_params[1] - range_params[0]) / range_params[2]) + 1)
                ]
    for param_value in cmd_params:
        param = param_value.split("=", 1)[0].strip()
        value = param_value.split("=", 1)[1].strip()
        try:
            value = float(value)
            param_dict[param] = [value]
        except ValueError:
            if value[0] == "[" and value[-1] == "]":
                values = [float(x) for x in value[1:-1].split(",")]
                param_dict[param] = values
            elif len(value.split(":")) == 3:
                range_params = [float(x) for x in value.split(":")]
                param_dict[param] = [
                    range_params[0] + i * range_params[2]
                    for i in range(0, int((range_params[1] - range_params[0]) / range_params[2]) + 1)
                ]
            else:
                critical(f"Unable to parse parameter '{param}': '{value}'")
                sys.exit(1)
    if "scale" in param_dict:
        scales = param_dict.pop("scale")
    else:
        scales = [1.0]
    l =  [
        {coupling: value for coupling, value in zip(param_dict.keys(), vals)}
        for vals in itertools.product(*param_dict.values())
    ]
    for d in l:
        if not d in param_list and len(d) > 0:
            param_list.append(d)
    param_list = [
        *[{**d, **{"scale": scale}} for scale in scales for d in param_list]
    ]
    return param_list


def guess_mpi_processes(command):
    match = re.findall(r"--?(?:np|c|n)[ \t]*(\d+)", command)
    if len(match) > 0:
        return int(match[0])
    else:
        critical(
            "'mpi_processes' is not set and the number of MPI processes cannot be guesses from 'mpi_command', please set 'mpi_processes'"
        )
        sys.exit(1)
