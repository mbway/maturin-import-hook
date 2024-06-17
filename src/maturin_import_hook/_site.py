import site
from pathlib import Path
from textwrap import dedent

from maturin_import_hook._logging import logger

MANAGED_INSTALL_START = "# <maturin_import_hook>"
MANAGED_INSTALL_END = "# </maturin_import_hook>\n"
MANAGED_INSTALL_COMMENT = """
# the following commands install the maturin import hook during startup.
# see: `python -m maturin_import_hook site`
"""

MANAGED_INSTALLATION_PRESETS = {
    "debug": dedent("""\
        try:
            import maturin_import_hook
        except ImportError:
            pass
        else:
            maturin_import_hook.install()
    """),
    "release": dedent("""\
        try:
            import maturin_import_hook
            from maturin_import_hook.settings import MaturinSettings
        except ImportError:
            pass
        else:
            maturin_import_hook.install(MaturinSettings(release=True))
    """),
}


def get_sitecustomize_path() -> Path:
    site_packages = site.getsitepackages()
    if not site_packages:
        msg = "could not find sitecustomize.py (site-packages not found)"
        raise FileNotFoundError(msg)
    for path in site_packages:
        sitecustomize_path = Path(path) / "sitecustomize.py"
        if sitecustomize_path.exists():
            return sitecustomize_path
    return Path(site_packages[0]) / "sitecustomize.py"


def get_usercustomize_path() -> Path:
    user_site_packages = site.getusersitepackages()
    if user_site_packages is None:
        msg = "could not find usercustomize.py (user site-packages not found)"
        raise FileNotFoundError(msg)
    return Path(user_site_packages) / "usercustomize.py"


def has_automatic_installation(module_path: Path) -> bool:
    if not module_path.is_file():
        return False
    code = module_path.read_text()
    return MANAGED_INSTALL_START in code


def remove_automatic_installation(module_path: Path) -> None:
    logger.info(f"removing automatic activation from '{module_path}'")
    if not has_automatic_installation(module_path):
        logger.info("no installation found")
        return

    code = module_path.read_text()
    managed_start = code.find(MANAGED_INSTALL_START)
    if managed_start == -1:
        msg = f"failed to find managed install start marker in '{module_path}'"
        raise RuntimeError(msg)
    managed_end = code.find(MANAGED_INSTALL_END)
    if managed_end == -1:
        msg = f"failed to find managed install start marker in '{module_path}'"
        raise RuntimeError(msg)
    code = code[:managed_start] + code[managed_end + len(MANAGED_INSTALL_END) :]

    if code.strip():
        module_path.write_text(code)
    else:
        logger.info("module is now empty. Removing file.")
        module_path.unlink(missing_ok=True)


def insert_automatic_installation(module_path: Path, preset_name: str, force: bool) -> None:
    if preset_name not in MANAGED_INSTALLATION_PRESETS:
        msg = f"Unknown managed installation preset name: '{preset_name}'"
        raise ValueError(msg)

    logger.info(f"installing automatic activation into '{module_path}'")
    if has_automatic_installation(module_path):
        if force:
            logger.info("already installed, but force=True. Overwriting...")
            remove_automatic_installation(module_path)
        else:
            logger.info("already installed. Aborting install.")
            return

    parts = []
    if module_path.exists():
        parts.append(module_path.read_text())
        parts.append("\n")
    parts.extend([
        MANAGED_INSTALL_START,
        MANAGED_INSTALL_COMMENT,
        MANAGED_INSTALLATION_PRESETS[preset_name],
        MANAGED_INSTALL_END,
    ])
    code = "".join(parts)
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(code)
    logger.info("automatic activation written successfully.")
