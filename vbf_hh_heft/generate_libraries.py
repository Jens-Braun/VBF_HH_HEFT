import jinja2
import tempfile
from logging import info, critical
import tarfile
import os
import pathlib
import re
import glob

from vbf_hh_heft.util import get_src_location, execute_alt_screen


def generate_libraries(template_path):
    os.chdir(get_src_location())
    template_name = os.path.splitext(pathlib.Path(template_path).name)[0]
    if not os.path.isdir("Libraries"):
        os.mkdir("Libraries")
    else:
        if os.path.isfile(os.path.join("Libraries", template_name + ".tar.gz")):
            info(f"Found existing library archive '{template_name + '.tar.gz'}, skipping library generation")
            return
    info(f"Generating libraries for template '{template_path}'")
    with open(template_path) as template_file:
        template = jinja2.Template(template_file.read())
    input_string = template.render({
        "model_path": os.path.join(get_src_location(), "Model"),
        "scale": 1.0,
        "seed": 1,
        "generate_events": False
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "input.sin"), "w") as sindarin:
            sindarin.write(input_string)
        os.chdir(tmpdir)
        execute_alt_screen(f"Generating libraries for {template_path}", [
            "whizard --single-event input.sin"
        ], logfile=os.path.join(get_src_location(), "vbf_hh_heft.log"))
        with tarfile.open(os.path.join(get_src_location(), "Libraries", template_name + ".tar.gz"), "w:gz") as archive:
            archive.add(re.findall(r'\$compile_workspace = "(.+)"', input_string)[0])
            for process in re.findall(r'process\s+([a-zA-Z0-9_+\-])\s*=', input_string):
                archive.add(f"{process}_olp_modules/build/libgolem_olp.so")
            for file in glob.glob("*.ol?"):
                archive.add(file)
    info(f"Finished generating libraries for template '{template_path}'")

def gen_libs(args):
    for template in args.templates:
        generate_libraries(os.path.join(get_src_location(), "Templates", template))