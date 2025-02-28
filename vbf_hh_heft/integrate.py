import jinja2
import tempfile
from logging import info, warning, critical
import json
import os
import hashlib
import random
import shutil
import re
import math
import sys
import subprocess
import time

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        critical("Python versions older than 3.11 require the 'toml' package to be installed")
        sys.exit(1)

from rich.progress import Progress

from vbf_hh_heft.util import (
    get_src_location,
    execute_alt_screen,
    setup_env,
    get_install_info,
    parse_processes,
    expand_parameters,
)
from vbf_hh_heft.generate_libraries import generate_libraries

grid_mapping = {"born": 1, "real": 2, "virtual": 3, "dglap": 4}


def run_integration(config, param_dict, template, additional_description="", force=False):
    if param_dict is None:
        param_dict = {}
    template_name = os.path.splitext(template)[0]
    conf_hash = hashlib.sha256(
        json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")
    ).hexdigest()
    if not os.path.isdir("Grids"):
        os.mkdir("Grids")
    if os.path.exists(f"Grids/{conf_hash}.tar.gz") and not force:
        info("Grid for current configuration already exists, skipping")
        return
    with open(os.path.join(get_src_location(), "Templates", template)) as template_file:
        jinja_template = jinja2.Template(template_file.read())
    seed = random.randint(0, 10000000)
    input_string = jinja_template.render(
        {
            "model_path": os.path.join(get_src_location(), "Model"),
            "scale": param_dict["scale"] if "scale" in param_dict.keys() else 1.0,
            "seed": seed,
            "parameters": [(key, value) for key, value in param_dict.items() if key != "scale"],
            "generate_events": False,
        }
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "input.sin"), "w") as sindarin:
            sindarin.write(input_string)
        shutil.unpack_archive(os.path.join(get_src_location(), "Libraries", f"{template_name}.tar.gz"), tmpdir)
        os.chdir(tmpdir)
        if "mpi" in config.keys() and config["mpi"]:
            if "mpi_run" in config.keys():
                mpi_run = config["mpi_run"] + " "
            else:
                critical(
                    "Running in MPI mode, but 'mpi_run' is not specified. Please specify a config file setting 'mpi_run'"
                )
                sys.exit(1)
        else:
            mpi_run = ""
        execute_alt_screen(
            f"{additional_description}Running integration for template {template_name} with parameters {param_dict}...",
            [f"{mpi_run}{get_install_info()['prefix']}/bin/whizard input.sin"],
            logfile=os.path.join(get_src_location(), "integration.log"),
            env=setup_env(),
        )
        grid = re.findall(r'\$integrate_workspace = "(.+)"', input_string)[0]
        shutil.make_archive(os.path.join(get_src_location(), "Grids", f"{conf_hash}"), "gztar", os.getcwd(), grid)
        try:
            with open(os.path.join(get_src_location(), "Grids", "grid_db.json"), "r") as db_file:
                grid_db = json.load(db_file)
        except FileNotFoundError:
            grid_db = {}
        grid_db[conf_hash] = {"template": template_name, "parameters": param_dict, "seed": seed}
        with open(os.path.join(get_src_location(), "Grids", "grid_db.json"), "w") as db_file:
            json.dump(grid_db, db_file, indent=4)
        processes = parse_processes(input_string)
        for process, process_data in processes.items():
            xsecs = []
            errors = []
            for component, data in process_data.items():
                with open(os.path.join(grid, f"{data['name']}.m{grid_mapping[component]}.vg2")) as gridfile:
                    grid_string = gridfile.read()
                    xsecs.append(float(re.search(r"Integral\s*=\s*([\d.+-E]+)", grid_string).group(1)))
                    errors.append(float(re.search(r"Error\s*=\s*([\d.+-E]+)", grid_string).group(1)))
            uncertainty = sum(err**2 for err in errors)
            xsec = sum(xsecs)
            info(f"Total cross section for process {process}: {xsec} ± {math.sqrt(uncertainty)}")
    os.chdir(get_src_location())
    info(f"Successfully generated the integration grid for template {template_name} with parameters {param_dict}")


def submit_jobs(args, config, param_list):
    if not "submit_command" in config.keys():
        critical("The field 'submit_command' is required to run in cluster mode")
        sys.exit(1)
    command_args = f"-c {args.config}"
    if args.mpi:
        command_args += " --mpi"
    if args.force:
        command_args += " --force"
    for p in args.cmd_parameters:
        command_args += f" -P{p}"
    template_name = os.path.splitext(args.template)[0]
    grid_dict = {}
    ids = []
    for i, param_dict in enumerate(param_list):
        conf_hash = hashlib.sha256(
            json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")
        ).hexdigest()
        if not os.path.exists(os.path.join("Grids", f"{conf_hash}.tar.gz")) or args.force:
            grid_dict[f"{conf_hash}.tar.gz"] = False
            ids.append(i)
            if os.path.exists(os.path.join("Grids", f"{conf_hash}.tar.gz")):
                os.remove(os.path.join("Grids", f"{conf_hash}.tar.gz"))
    if len(ids) == 0:
        info("All grids already present for the given configuration, skipping...")
        return
    info(
        f"Submitting {len(ids)} integration jobs with command '{config['submit_command']} {get_src_location()}/vbf_hh_heft.py integrate --id <ID> {command_args} {args.template}'"
    )
    for i in range(len(ids)):
        subprocess.run(
            config["submit_command"].format(
                f"{get_src_location()}/vbf_hh_heft.py integrate --id {i} {command_args} {args.template}"
            ),
            stdout=subprocess.DEVNULL,
            shell=True,
        )

    with Progress(transient=True) as progress:
        task = progress.add_task(f"[green]Waiting for {len(param_list)} jobs to complete", total=len(param_list))
        while True:
            for grid in grid_dict.keys():
                if grid_dict[grid]:
                    continue
                else:
                    if os.path.exists(os.path.join(get_src_location(), "Grids", grid)):
                        grid_dict[grid] = True
                        progress.update(task, advance=1)
            if all(grid_exists for grid_exists in grid_dict.values()):
                break
            else:
                time.sleep(0.2)


def integrate_missing(args, config, param_list):
    template_name = os.path.splitext(args.template)[0]
    missing_points = []
    for param_dict in param_list:
        conf_hash = hashlib.sha256(
            json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")
        ).hexdigest()
        if not os.path.exists(os.path.join("Grids", f"{conf_hash}.tar.gz")) or args.force:
            missing_points.append(param_dict)
    info(f"Running integration for {len(missing_points)} parameter combinations...")
    for i, param_dict in enumerate(param_list):
        run_integration(
            config, param_dict, args.template, f"[orange]\\[{i + 1}/{len(missing_points)}][/orange] ", force=args.force
        )
    info(f"Successfully integrated {len(missing_points)} parameter combinations")


def integrate(args):
    template_name = os.path.splitext(args.template)[0]
    if not os.path.exists(f"Libraries/{template_name}.tar.gz"):
        generate_libraries(os.path.join(get_src_location(), "Templates", args.template))
    if args.config:
        with open(args.config, "rb") as config_file:
            config = tomllib.load(config_file)
    else:
        config = {}
    if args.mpi:
        if not get_install_info()["mpi"]:
            warning("Whizard was installed without MPI support, running serially")
        else:
            config["mpi"] = args.mpi
    param_list = expand_parameters(args.config, args.cmd_parameters)
    if args.cluster:
        submit_jobs(args, config, param_list)
        return
    if args.id:
        info(f"Running integration for the {id}-th parameter combination...")
        run_integration(config, param_list[args.id], args.template, force=args.force)
        return
    if len(param_list) == 1:
        run_integration(config, param_list[0], args.template, force=args.force)
    else:
        integrate_missing(args, config, param_list)
