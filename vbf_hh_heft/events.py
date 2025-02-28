import jinja2
import tempfile
from logging import info, warning, critical
import json
import os
import hashlib
import random
import shutil
import time
import sys
import subprocess
import tarfile

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
    guess_mpi_processes,
)
from vbf_hh_heft.generate_libraries import generate_libraries
from vbf_hh_heft.integrate import integrate_missing, submit_jobs as submit_integration


def run_event_generation(config, param_dict, template, additional_description="", stamp_id=None):
    info(f"Running event generation for template '{template}' with parameters {param_dict}")
    if param_dict is None:
        param_dict = {}
    template_name = os.path.splitext(template)[0]
    seed = random.randint(0, 10000000)
    conf_hash = hashlib.sha256(
        json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")
    ).hexdigest()
    if not os.path.isdir("Events"):
        os.mkdir("Events")
    with open(os.path.join(get_src_location(), "Templates", template)) as template_file:
        jinja_template = jinja2.Template(template_file.read())
    input_string = jinja_template.render(
        {
            "model_path": os.path.join(get_src_location(), "Model"),
            "scale": param_dict["scale"] if "scale" in param_dict.keys() else 1.0,
            "seed": 1,
            "parameters": [(key, value) for key, value in param_dict.items() if key != "scale"],
            "generate_events": True,
            "evt_gen_seed": seed,
        }
    )
    proc_info = parse_processes(input_string)
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "input.sin"), "w") as sindarin:
            sindarin.write(input_string)
        shutil.unpack_archive(os.path.join(get_src_location(), "Libraries", f"{template_name}.tar.gz"), tmpdir)
        shutil.unpack_archive(os.path.join(get_src_location(), "Grids", f"{conf_hash}.tar.gz"), tmpdir)
        os.chdir(tmpdir)
        if "mpi" in config.keys() and config["mpi"]:
            mpi_run = config["mpi_run"] + " "
            mpi_processes = config["mpi_processes"]
        else:
            mpi_run = ""
            mpi_processes = None
        analysis_processes = []
        env = setup_env()
        rivet_cmd = f"rivet -a {','.join(config['analyses'])} -o {{}} {{}}"
        for process in proc_info.values():
            for component, data in process.items():
                if mpi_processes:
                    for i in range(mpi_processes):
                        os.mkfifo(f"{data['sample']}_{i}.hepmc")
                        analysis_processes.append(
                            subprocess.Popen(
                                rivet_cmd.format(f"{data['sample']}_{i}.yoda", f"{data['sample']}_{i}.hepmc"),
                                shell=True,
                                env=env,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                        )
                else:
                    os.mkfifo(f"{data['sample']}.hepmc")
                    analysis_processes.append(
                        subprocess.Popen(
                            rivet_cmd.format(f"{data['sample']}.yoda", f"{data['sample']}.hepmc"),
                            shell=True,
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    )
        execute_alt_screen(
            f"{additional_description}Running event generation for template {template_name} with parameters {param_dict}...",
            [f"{mpi_run}{get_install_info()['prefix']}/bin/whizard input.sin"],
            logfile=os.path.join(get_src_location(), "event_generation.log"),
            env=env,
        )
        for proc in analysis_processes:
            if proc.poll() is None:
                proc.terminate()
        info("Merging YODA-files")
        os.mkdir("event_files")
        if os.path.exists(os.path.join(get_src_location(), "Events", f"{conf_hash}.tar.gz")):
            shutil.unpack_archive(
                os.path.join(get_src_location(), "Events", f"{conf_hash}.tar.gz"), os.path.join(tmpdir, "event_files")
            )
        os.mkdir(os.path.join("event_files", str(seed)))
        for name, process in proc_info.items():
            for component, data in process.items():
                subprocess.run(
                    f"rivet-merge -e --assume-reentrant -o {name}_{component}.yoda {data['sample']}*.yoda",
                    shell=True,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                shutil.copy2(f"{name}_{component}.yoda", os.path.join(tmpdir, "event_files", str(seed)))
                subprocess.run(
                    f"rivet-merge -e --assume-reentrant -o event_files/{name}_{component}.yoda event_files/*/{name}_{component}.yoda",
                    shell=True,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            subprocess.run(
                f"rivet-merge --assume-reentrant -o event_files/{name}.yoda event_files/{name}_*.yoda",
                shell=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if os.path.exists(os.path.join("event_files", "content.json")):
            with open(os.path.join("event_files", "content.json")) as content_db:
                content = json.load(content_db)
            content["metadata"]["n_events"] = {
                name: {
                    component: content["metadata"]["n_events"][name][component] + data["n_events"]
                    for component, data in process.items()
                }
                for name, process in proc_info.items()
            }
        else:
            content = {
                "metadata": {
                    "template": template,
                    "params": param_dict,
                    "processes": list(proc_info.keys()),
                    "n_events": {
                        name: {component: data["n_events"] for component, data in process.items()}
                        for name, process in proc_info.items()
                    },
                },
                "samples": {},
            }
        content["samples"][str(seed)] = {
            name: {component: data["n_events"] for component, data in process.items()}
            for name, process in proc_info.items()
        }
        n_events = content["metadata"]["n_events"]
        with open(os.path.join("event_files", "content.json"), "w") as content_db:
            json.dump(content, content_db, indent=4)
        os.chdir("event_files")
        with tarfile.open(os.path.join(get_src_location(), "Events", f"{conf_hash}.tar.gz"), "w:gz") as archive:
            for obj in os.listdir("."):
                archive.add(obj)
        if os.path.exists(os.path.join(get_src_location(), "Events", "event_db.json")):
            with open(os.path.join(get_src_location(), "Events", "event_db.json"), "r") as event_db:
                events = json.load(event_db)
        else:
            events = {}
        events[conf_hash] = {"template": template_name, "parameters": param_dict, "n_events": n_events}
        with open(os.path.join(get_src_location(), "Events", "event_db.json"), "w") as event_db:
            json.dump(events, event_db, indent=4)
    os.chdir(get_src_location())
    if stamp_id is not None:
        with open(os.path.join(get_src_location(), "Events", f"{stamp_id}.stamp"), "w") as _:
            pass
    info(f"Successfully generated events for template '{template}' with parameters {param_dict}")


def submit_jobs(args, config, param_list):
    if not "submit_command" in config.keys():
        critical("The field 'submit_command' is required to run in cluster mode")
        sys.exit(1)
    command_args = f"-c {args.config}"
    if args.mpi:
        command_args += " --mpi"
    for p in args.cmd_parameters:
        command_args += f" -P{p}"
    info(
        f"Submitting {len(param_list)} event generation jobs with command '{config['submit_command'].format(f'{get_src_location()}/vbf_hh_heft.py generate --id <ID> {command_args} {args.template}')}'"
    )
    for i in range(len(param_list)):
        subprocess.run(
            config["submit_command"].format(
                f"{get_src_location()}/vbf_hh_heft.py generate --id {i} {command_args} {args.template}"
            ),
            stdout=subprocess.DEVNULL,
            shell=True,
        )
    finished = [False] * len(param_list)
    with Progress(transient=True) as progress:
        task = progress.add_task(f"[green]Waiting for {len(param_list)} jobs to complete", total=len(param_list))
        while True:
            for i in range(len(param_list)):
                if finished[i]:
                    continue
                else:
                    if os.path.exists(os.path.join(get_src_location(), "Events", f"{i}.stamp")):
                        finished[i] = True
                        progress.update(task, advance=1)
            if all(finished for finished in finished):
                break
            else:
                time.sleep(0.2)
    for i in range(len(param_list)):
        os.remove(os.path.join(get_src_location(), "Events", f"{i}.stamp"))


def generate_events(args):
    template_name = os.path.splitext(args.template)[0]
    args.force = False
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
        if not "mpi_processes" in config.keys():
            config["mpi_processes"] = guess_mpi_processes(config["mpi_run"])
    param_list = expand_parameters(args.config, args.cmd_parameters)
    if args.cluster:
        submit_integration(args, config, param_list)
    else:
        integrate_missing(args, config, param_list)
    if args.cluster:
        submit_jobs(args, config, param_list)
        return
    if args.id is not None:
        info(f"Running event generation for the {id}-th parameter combination...")
        run_event_generation(config, param_list[args.id], args.template, stamp_id=args.id)
        return
    if len(param_list) == 1:
        run_event_generation(config, param_list[0], args.template)
    else:
        info(f"Running event generation for {len(param_list)} parameter combinations...")
        for i, param_dict in enumerate(param_list):
            run_event_generation(config, param_dict, args.template, f"[orange]\\[{i + 1}/{len(param_list)}][/orange] ")
        info(f"Successfully generated events for {len(param_list)} parameter combinations")
