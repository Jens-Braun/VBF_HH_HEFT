import os.path
import subprocess
from logging import critical
import sys
import pathlib
from rich.live import Live
from rich.spinner import Spinner
from rich.console import Console

console = Console()

def execute_alt_screen(task_description, commands, logfile=None):
    failed = False
    failed_command = ""
    return_code = 0
    cmd_output = []
    with console.screen():
        spinner = Spinner("dots", text= "[bold red]" + task_description + "[/bold red]", style="bold green")
        with Live(spinner, console=console, transient=True) as live:
            for command in commands:
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True) as proc:
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