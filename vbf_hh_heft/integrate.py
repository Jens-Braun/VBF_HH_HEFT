import jinja2
import tempfile
from logging import info, critical
import json
import os
import hashlib
import random
import shutil
import re
import math

from vbf_hh_heft.util import get_src_location, execute_alt_screen, setup_env, get_install_info, parse_processes, \
    expand_parameters
from vbf_hh_heft.generate_libraries import generate_libraries

grid_mapping = {"born": 1, "real": 2, "virtual": 3, "dglap": 4}

def run_integration(param_dict, template, additional_description="", force=False):
    if param_dict is None:
        param_dict = {}
    template_name = os.path.splitext(template)[0]
    conf_hash = hashlib.sha256(json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")).hexdigest()
    if not os.path.isdir("Grids"):
        os.mkdir("Grids")
    if os.path.exists(f"Grids/{conf_hash}.tar.gz") and not force:
        info("Grid for current configuration already exists, skipping")
        return
    with open(os.path.join(get_src_location(), "Templates", template)) as template_file:
        jinja_template = jinja2.Template(template_file.read())
    seed = random.randint(0, 10000000)
    input_string = jinja_template.render({
        "model_path": os.path.join(get_src_location(), "Model"),
        "scale": param_dict["scale"] if "scale" in param_dict.keys() else 1.0,
        "seed": seed,
        "parameters": [(key, value) for key, value in param_dict.items() if key != "scale"],
        "generate_events": False
    })

    if not os.path.exists(f"Libraries/{template_name}.tar.gz"):
        generate_libraries(os.path.join(get_src_location(), "Templates", template))

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "input.sin"), "w") as sindarin:
            sindarin.write(input_string)
        shutil.unpack_archive(os.path.join(get_src_location(), "Libraries", f"{template_name}.tar.gz"), tmpdir)
        os.chdir(tmpdir)
        execute_alt_screen(f"{additional_description}Running integration for template {template_name} with parameters {param_dict}...",
                           [
                               f"{get_install_info()['prefix']}/bin/whizard input.sin"
                           ],
                           logfile=os.path.join(get_src_location(), "integration.log"))
        grid = re.findall(r'\$integrate_workspace = "(.+)"', input_string)[0]
        shutil.make_archive(os.path.join(get_src_location(), "Grids", f"{conf_hash}"), "gztar", os.getcwd(), grid)
        try:
            with open(os.path.join(get_src_location(), "Grids", "grid_db.json"), "r") as db_file:
                grid_db = json.load(db_file)
        except FileNotFoundError:
            grid_db = {}
        grid_db[conf_hash] = {"template": template_name, "parameters": param_dict, "seed": seed}
        with open(os.path.join(get_src_location(), "Grids", "grid_db.json"), "w") as db_file:
            json.dump(grid_db, db_file)
        processes = parse_processes(input_string)
        for process, process_data in processes.items():
            xsecs = []
            errors = []
            for component, data in process_data.items():
                with open(os.path.join(grid, f"{data['name']}.m{grid_mapping[component]}.vg2")) as gridfile:
                    grid = gridfile.read()
                    xsecs.append(float(re.search(r"Integral\s*=\s*([\d.+-E]+)", grid).group(1)))
                    errors.append(float(re.search(r"Error\s*=\s*([\d.+-E]+)", grid).group(1)))
            uncertainty = 1/sum(1/err**2 for err in errors)
            xsec = sum(xsec/err**2 for xsec, err in zip(xsecs, errors))*uncertainty
            info(f"Total cross section for process {process}: {xsec} ± {math.sqrt(uncertainty)}")
    os.chdir(get_src_location())
    info(f"Successfully generated the integration grid for template {template_name} with parameters {param_dict}")

def integrate(args):
    param_list = expand_parameters(args.parameters, args.cmd_parameters)
    if len(param_list) == 1:
        run_integration(param_list[0], args.template, force=args.force)
    else:
        info(f"Running integration for {len(param_list)} parameter combinations...")
        for i, param_dict in enumerate(param_list):
            run_integration(param_dict, args.template, f"[orange]\\[{i+1}/{len(param_list)}][/orange] ", force=args.force)
        info(f"Successfully integrated {len(param_list)} parameter combinations")
