import os
import json
from logging import info
from vbf_hh_heft.util import get_src_location


def purge(args):
    template_name = os.path.splitext(args.template)[0]
    if args.library:
        info(f"Purging process library and grids for template {args.template}")
        if os.path.isfile(os.path.join(get_src_location(), "Libraries", f"{template_name}.tar.gz")):
            os.remove(os.path.join(get_src_location(), "Libraries", f"{template_name}.tar.gz"))
    else:
        info(f"Purging grids for template {args.template}")
    if os.path.isfile(os.path.join(get_src_location(), "Grids", "grid_db.json")):
        with open(os.path.join(get_src_location(), "Grids", "grid_db.json"), "r") as db:
            grid_db = json.load(db)
        for conf_hash, config in list(grid_db.items()):
            if config["template"] == template_name:
                os.remove(os.path.join(get_src_location(), "Grids", f"{conf_hash}.tar.gz"))
                grid_db.pop(conf_hash)
        with open(os.path.join(get_src_location(), "Grids", "grid_db.json"), "w") as db:
            json.dump(grid_db, db, indent=4)
