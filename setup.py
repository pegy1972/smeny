from cx_Freeze import setup, Executable
import sys
import os

# přidej cestu k šablonám
build_exe_options = {
    "packages": ["flask"],
    "include_files": [
        ("C:\\Users\\pekha\\WebováAplikace2\\my_flask_app\\templates", "templates")
    ]
}

base = None
if sys.platform == "win32":
    base = "win32GUI"

setup(
    name="BreakList",
    version="1.0",
    description="Moje Flask aplikace",
    options={"build_exe": build_exe_options},
    executables=[Executable("C:\\Users\\pekha\\WebováAplikace2\\my_flask_app\\app.py", base=base)]
)