> [!CAUTION]
> The code in this repository is not yet functional, as the required versions of `GoSam` and `Whizard` are not yet public. 
> This repository will become usable once the versions of these codes are published.

# Repository Content

- `Analysis`: The `Rivet` analysis
- `Model`: The UFO model 
- `Templates`: `WHIZARD` Sindarin template files
- `vbf_hh_heft.py`: Utility script for running `VBF_HH_HEFT`

# `vbf_hh_heft.py`
The utility script can be used to install the requirements and run a template for specific coupling values. Running the script requires the [`rich`](https://pypi.org/project/rich/) and [`Jinja`](https://pypi.org/project/Jinja2/) python libraries. See `./vbf_hh_heft.py --help` for details.