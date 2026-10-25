# PyInstaller configuration: a single program file "SongBridge" (or .exe on Windows).
#   pip install pyinstaller && pyinstaller packaging/SongBridge.spec   ->  dist/SongBridge
# (run from the project folder)
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent
PKG = ROOT / "songbridge"
PROTO = PKG / "propresenter" / "proto"

pb2 = [p.stem for p in PROTO.glob("*_pb2.py")]

a = Analysis(
    [str(Path(SPECPATH) / "main.py")],
    pathex=[str(ROOT), str(PROTO)],  # the *_pb2 modules import each other without a package prefix
    datas=[
        (str(PKG / "web"), "songbridge/web"),
        (str(PKG / "resources"), "songbridge/resources"),
        (str(PROTO / "LICENSE-ProPresenter7-Proto"), "songbridge/propresenter/proto"),
        *copy_metadata("keyring"),  # keyring finds its backends (system keychain) via the package metadata
    ],
    # songbridge/version.py is written by the build (missing when running from source)
    hiddenimports=pb2 + ["songbridge.version"] + collect_submodules("keyring.backends"),
    # pymupdf >= 2 imports an AI layout module (onnxruntime + model files) that SongBridge does not need
    # (it only renders PDF pages to images). When bundled, its data files were missing and the playlist
    # export crashed. Without the module, pymupdf catches the ImportError itself.
    excludes=["tkinter", "pymupdf.layout", "pymupdf4llm", "onnxruntime", "networkx"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="SongBridge",
    console=True,  # the window shows address/data folder; closing it quits the program
    upx=False,
)
