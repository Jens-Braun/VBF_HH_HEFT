from logging import info, critical
from urllib.request import urlopen, Request
import os
from functools import partial
import shutil
import sys
import json
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


from vbf_hh_heft.check_dependencies import check_dependencies, print_dep_table
from vbf_hh_heft.util import execute_alt_screen

package_data = {
    "lhapdf": {
        "url": "https://lhapdf.hepforge.org/downloads/LHAPDF-6.5.5.tar.gz",
        "dirname": "LHAPDF-6.5.5",
        "pdf_urls": ["https://lhapdfsets.web.cern.ch/lhapdfsets/current/PDF4LHC21_mc.tar.gz",
                     "https://lhapdfsets.web.cern.ch/lhapdfsets/current/CT10.tar.gz",
                     "https://lhapdfsets.web.cern.ch/lhapdfsets/current/cteq6l1.tar.gz"],
        "configure": "./configure --prefix={prefix}",
        "install": "make install -j {jobs}"
    },
    "hepmc": {
        "url": "https://hepmc.web.cern.ch/hepmc/releases/HepMC3-3.3.0.tar.gz",
        "dirname": "HepMC3-3.3.0",
        "configure": "cmake -DCMAKE_INSTALL_PREFIX={prefix} -DHEPMC3_ENABLE_ROOTIO=OFF   -DHEPMC3_ENABLE_PYTHON=OFF CMakeLists.txt",
        "build": "cmake --build . -j {jobs}",
        "install": "cmake --install ."
    },
    "fastjet": {
        "url": "https://fastjet.fr/repo/fastjet-3.4.3.tar.gz",
        "dirname": "fastjet-3.4.3",
        "configure": "./configure --prefix={prefix} --enable-shared --disable-auto-ptr --enable-allcxxplugins",
        "install": "make install -j {jobs}",
        "contrib_url": "https://fastjet.hepforge.org/contrib/downloads/fjcontrib-1.100.tar.gz",
        "contrib_dirname": "fjcontrib-1.100",
        "contrib_configure": "./configure --fastjet-config={prefix}/bin/fastjet-config CXXFLAGS=-fPIC",
        "contrib_install": "make install fragile-shared-install -j {jobs}"
    },
    "yoda": {
        "url": "https://yoda.hepforge.org/downloads/YODA-2.0.2.tar.gz",
        "dirname": "YODA-2.0.2",
        "configure": "./configure --prefix={prefix}",
        "install": "make install -j {jobs}"
    },
    "rivet": {
        "url": "https://rivet.hepforge.org/downloads/Rivet-4.0.2.tar.gz",
        "dirname": "Rivet-4.0.2",
        "configure": "./configure --prefix={prefix} --with-yoda={prefix} --with-hepmc={prefix} --with-fastjet={prefix}",
        "install": "make install -j {jobs}"
    },
    "gosam": {
        "url": "https://github.com/gudrunhe/gosam/releases/download/3.0.0/GoSam-3.0.0-1c107f1.tar.gz",
        "dirname": "GoSam-3.0.0-1c107f1",
        "configure": "meson setup build --prefix {prefix}",
        "build": "meson compile -C build -j {jobs}",
        "install": "meson install -C build"
    },
    "whizard": {
        "url": "https://whizard.hepforge.org/downloads/whizard-3.1.6.tar.gz",
        "dirname": "whizard-3.1.6",
        "configure": "./configure --prefix={prefix} " +
                     "--enable-lhapdf LHAPDF_DIR={prefix} " +
                     "--enable-hepmc --with-hepmc={prefix} " +
                     "--enable-fastjet --with-fastjet={prefix} " +
                     "--enable-gosam --with-gosam={prefix}",
        "mpi_flags": "FC=mpifort CC=mpicc CXX=mpic++ --enable-fc-mpi",
        "install": "make install -j {jobs}"
    }
}

src_dir = os.getcwd()

def download_archive(url):
    info(f"Downloading {url}...")
    with Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            transient=True,
        ) as progress:
        filename = url.split("/")[-1]
        task_id = progress.add_task("download", filename=filename, start=False)
        response = urlopen(Request(url, headers={'User-Agent': 'vbf_hh_heft', 'Accept': '*/*'}))
        if response.info()["Content-length"]:
            progress.update(task_id, total=int(response.info()["Content-length"]))
        else:
            progress.update(task_id, total=None)
        with open(filename, "wb") as dest_file:
            progress.start_task(task_id)
            for data in iter(partial(response.read, 32768), b""):
                dest_file.write(data)
                progress.update(task_id, advance=len(data))


def download_unpack(url, dest_dir, dirname):
    filename = url.split("/")[-1]
    if not os.path.isdir(os.path.join(dest_dir, dirname)):
        if not os.path.isfile(filename):
            download_archive(url)
        else:
            info(f"Using existing '{filename}'")
        shutil.unpack_archive(filename, extract_dir=dest_dir, format="gztar")
    else:
        info(f"Using existing '{dirname}'")

def install_lhapdf(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/lhapdf-config")):
        info(f"[1/{len(package_data)}] LHAPDF already installed in {args.prefix}, skipping")
        return
    info(f"[1/{len(package_data)}] Installing LHAPDF...")
    os.chdir("download_cache")
    download_unpack(package_data["lhapdf"]["url"], ".", package_data["lhapdf"]["dirname"])
    os.chdir(package_data["lhapdf"]["dirname"])
    execute_alt_screen("Installing LHAPDF...", [
        package_data["lhapdf"]["configure"].format(prefix=args.prefix),
        package_data["lhapdf"]["install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("..")
    for pdf_url in package_data["lhapdf"]["pdf_urls"]:
        pdf = pdf_url.split("/")[-1].split(".")[0]
        info(f"[1/{len(package_data)}] Installing default PDF '{pdf}'...")
        download_unpack(pdf_url, os.path.join(args.prefix, f"share/LHAPDF"), pdf)
    os.chdir("..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/lhapdf-config")):
        critical("An error occurred while installing LHAPDF, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[1/{len(package_data)}] Successfully installed LHAPDF and the required PDFs")

def install_hepmc(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/HepMC3-config")):
        info(f"[2/{len(package_data)}] HepMC already installed in {args.prefix}, skipping")
        return
    info(f"[2/{len(package_data)}] Installing HepMC...")
    os.chdir("download_cache")
    download_unpack(package_data["hepmc"]["url"], ".", package_data["hepmc"]["dirname"])
    os.chdir(package_data["hepmc"]["dirname"])
    execute_alt_screen("Installing HepMC...", [
        package_data["hepmc"]["configure"].format(prefix=args.prefix),
        package_data["hepmc"]["build"].format(jobs=args.jobs),
        package_data["hepmc"]["install"]
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("../..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/HepMC3-config")):
        critical("An error occurred while installing HepMC, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[2/{len(package_data)}] Successfully installed HepMC")

def install_fastjet(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/fastjet-config")):
        info(f"[3/{len(package_data)}] FastJet already installed in {args.prefix}, skipping")
        return
    info(f"[3/{len(package_data)}] Installing FastJet...")
    os.chdir("download_cache")
    download_unpack(package_data["fastjet"]["url"], ".", package_data["fastjet"]["dirname"])
    os.chdir(package_data["fastjet"]["dirname"])
    execute_alt_screen("Installing FastJet...", [
        package_data["fastjet"]["configure"].format(prefix=args.prefix),
        package_data["fastjet"]["install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("..")
    download_unpack(package_data["fastjet"]["contrib_url"], ".", package_data["fastjet"]["contrib_dirname"])
    os.chdir(package_data["fastjet"]["contrib_dirname"])
    execute_alt_screen("Installing FastJet contrib...", [
        package_data["fastjet"]["contrib_configure"].format(prefix=args.prefix),
        package_data["fastjet"]["contrib_install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("../..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/fastjet-config")):
        critical("An error occurred while installing FastJet, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[3/{len(package_data)}] Successfully installed FastJet")

def install_yoda(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/yoda-config")):
        info(f"[4/{len(package_data)}] Yoda already installed in {args.prefix}, skipping")
        return
    info(f"[4/{len(package_data)}] Installing Yoda...")
    os.chdir("download_cache")
    download_unpack(package_data["yoda"]["url"], ".", package_data["yoda"]["dirname"])
    os.chdir(package_data["yoda"]["dirname"])
    execute_alt_screen("Installing Yoda...", [
        package_data["yoda"]["configure"].format(prefix=args.prefix),
        package_data["yoda"]["install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("../..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/yoda-config")):
        critical("An error occurred while installing Yoda, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[4/{len(package_data)}] Successfully installed Yoda")

def install_rivet(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/rivet-config")):
        info(f"[5/{len(package_data)}] Rivet already installed in {args.prefix}, skipping")
        return
    info(f"[5/{len(package_data)}] Installing Rivet...")
    os.chdir("download_cache")
    download_unpack(package_data["rivet"]["url"], ".", package_data["rivet"]["dirname"])
    os.chdir(package_data["rivet"]["dirname"])
    execute_alt_screen("Installing Rivet...", [
        package_data["rivet"]["configure"].format(prefix=args.prefix),
        package_data["rivet"]["install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("../..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/rivet-config")):
        critical("An error occurred while installing Rivet, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[5/{len(package_data)}] Successfully installed Rivet")

def install_gosam(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/gosam.py")):
        info(f"[6/{len(package_data)}] GoSam already installed in {args.prefix}, skipping")
        return
    info(f"[6/{len(package_data)}] Installing GoSam...")
    os.chdir("download_cache")
    download_unpack(package_data["gosam"]["url"], ".", package_data["gosam"]["dirname"])
    os.chdir(package_data["gosam"]["dirname"])
    execute_alt_screen("Installing GoSam...", [
        package_data["gosam"]["configure"].format(prefix=args.prefix),
        package_data["gosam"]["install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("../..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/GoSam/gosam.py")):
        critical("An error occurred while installing GoSam, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[6/{len(package_data)}] Successfully installed GoSam")

def install_whizard(args):
    if os.path.isfile(os.path.join(args.prefix, "bin/whizard-config")):
        info(f"[7/{len(package_data)}] Whizard already installed in {args.prefix}, skipping")
        return
    info(f"[7/{len(package_data)}] Installing Whizard...")
    os.chdir("download_cache")
    download_unpack(package_data["whizard"]["url"], ".", package_data["whizard"]["dirname"])
    os.chdir(package_data["whizard"]["dirname"])
    execute_alt_screen("Installing Whizard...", [
        package_data["whizard"]["configure"].format(prefix=args.prefix)
        + (package_data["whizard"]["mpiflags"] if args.mpi else ""),
        package_data["whizard"]["install"].format(jobs=args.jobs)
    ], logfile=os.path.join(src_dir, "install.log"))
    os.chdir("../..")
    if not os.path.isfile(os.path.join(args.prefix, "bin/whizard-config")):
        critical("An error occurred while installing Whizard, see 'install.log' for details")
        sys.exit(1)
    else:
        info(f"[7/{len(package_data)}] Successfully installed Whizard")

def install(args):
    info("Checking build dependencies...")
    dep_results = check_dependencies(args)
    if any(not data["ok"] for _, data in dep_results.items()):
        print_dep_table(dep_results)
        critical(f"Build requirements not satisfied")
        sys.exit(1)
    info(f"Installing VBF_HH_HEFT toolchain to {args.prefix}")
    if not os.path.isdir("download_cache"):
        os.mkdir("download_cache")
    install_lhapdf(args)
    install_hepmc(args)
    install_fastjet(args)
    install_yoda(args)
    install_rivet(args)
    install_gosam(args)
    install_whizard(args)
    if os.path.isfile("install.log"):
        os.remove("install.log")
    info(f"Successfully installed VBF_HH_HEFT toolchain to {args.prefix}")
    with open("installation.json", "w") as file:
        json.dump({
            "prefix": args.prefix,
            "mpi": args.mpi,
        }, file)