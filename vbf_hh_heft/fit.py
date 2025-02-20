import sys
import os
from logging import info, warning, critical
import inspect
import hashlib
import json
import tarfile
import re
import math

from vbf_hh_heft.util import expand_parameters, get_src_location
from vbf_hh_heft.integrate import run_integration

from rich.console import Console
from rich.table import Table

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        critical("Python versions older than 3.11 require the 'toml' package to be installed")
        sys.exit(1)

try:
    import iminuit
    from iminuit.cost import LeastSquares
    import numpy as np
    import numba
except ImportError:
    critical("Fitting the total cross section requires the '[link=https://scikit-hep.org/iminuit/]iminuit[/link]' package to be installed")
    sys.exit(1)

def corr_chi2(x, data, covariance_matrix, model):
    def res_func(params):
        cm_inv = np.linalg.inv(covariance_matrix)
        diff = data - model(x, *params)
        return diff@cm_inv@diff
    f = res_func
    f.errordef = iminuit.Minuit.LEAST_SQUARES
    f.ndata = len(data)
    return f

def fit(args):
    if not args.config:
        critical("A configuration file containing the fit function and parameter points is required")
        sys.exit(1)
    with open(args.config, "rb") as f:
        config = tomllib.load(f)
    d = {}
    exec(config["fit"]["code"], d)
    fit_function = d[config["fit"]["function_name"]]
    n_params = len(inspect.signature(fit_function).parameters)-1
    param_list = expand_parameters(args.config, [])
    if len(param_list) < n_params:
        critical(f"The given fit function requires {n_params} parameter points to be fully determined, but the config only has {len(param_list)} parameter combinations")
        sys.exit(1)
    missing_points = []
    template_name = os.path.splitext(args.template)[0]
    for param_dict in param_list:
        conf_hash = hashlib.sha256(
            json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")).hexdigest()
        if not os.path.isfile(os.path.join(get_src_location(), "Grids", f"{conf_hash}.tar.gz")):
            missing_points.append(param_dict)
    if len(missing_points) > 0:
        info(f"Running integration for {len(missing_points)} missing parameter combinations...")
        for i, param_dict in enumerate(missing_points):
            run_integration(param_dict, args.template, f"[orange]\\[{i + 1}/{len(missing_points)}][/orange] ")
        info(f"Successfully integrated {len(param_list)} missing parameter combinations")
    info(f"Fitting the total cross section with the given function for {len(param_list)} parameter combinations...")
    xsec_list = []
    xsec_err_list = []
    for param_dict in param_list:
        conf_hash = hashlib.sha256(
            json.dumps({"template": template_name, "parameters": param_dict}).encode("utf-8")).hexdigest()
        xsecs = []
        errors = []
        with tarfile.open(os.path.join(get_src_location(), "Grids", f"{conf_hash}.tar.gz"), "r:gz") as grid_archive:
            for file in grid_archive.getmembers():
                if file.name.endswith(".vg2"):
                    grid = grid_archive.extractfile(file).read().decode("utf-8")
                    xsecs.append(float(re.search(r"Integral\s*=\s*([\d.+-E]+)", grid).group(1)))
                    errors.append(float(re.search(r"Error\s*=\s*([\d.+-E]+)", grid).group(1)))
        uncertainty = 1 / sum(1 / err ** 2 for err in errors)
        xsec = sum(xsec / err ** 2 for xsec, err in zip(xsecs, errors)) * uncertainty
        xsec_list.append(xsec)
        xsec_err_list.append(math.sqrt(uncertainty))

    x = [list(d.values()) for d in param_list]
    if config["fit"]["normalize"]:
        try:
            i_norm = x.index([1.0]*len(config["parameters"]))
        except ValueError:
            warning(f"Unit value parameter point not found in the configuration, normalizing to {param_list[0]}")
            i_norm = 0
        xsec_norm = xsec_list[i_norm]
        xsec_norm_list = [xsec / xsec_norm for xsec in xsec_list]
        cov_matrix = np.array(
            [
                [
                    xsec_list[i]*xsec_list[j]*xsec_err_list[i_norm]**2/xsec_norm**4 + (xsec_err_list[i]**2/xsec_norm**2 if i == j else 0)
                    for j in range(len(param_list))
                ]
                for i in range(len(param_list))
            ]
        )
        x = np.array(x)
        least_squares = corr_chi2(x.T, xsec_norm_list, cov_matrix, fit_function)
    else:
        x = np.array(x)
        least_squares = LeastSquares(x.T, xsec_list, xsec_err_list, fit_function)
    m = iminuit.Minuit(least_squares, ([1] * n_params), name = tuple(list(inspect.signature(fit_function).parameters)[1:]))
    m.migrad()
    m.hesse()
    if not m.valid:
        warning(f"Migrad did not converge to a valid minimum")
    else:
        m.minos()
    info(f"Fit terminated with final 𝜒²/ndf = {m.fmin.reduced_chi2}")
    table = Table(title="Fit result", show_lines=True)
    table.add_column("Parameter")
    table.add_column("Value")
    table.add_column("Error")
    for param in m.params:
        table.add_row(param.name, str(param.value), str(param.error))
    console = Console()
    console.print(table)