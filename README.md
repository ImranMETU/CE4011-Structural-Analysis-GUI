Refer to the UserManual.pdf and InstallationManual.PDF

CE4011 SOLVER - WINDOWS DISTRIBUTION
====================================

RUNNING THE DISTRIBUTED APPLICATION

1. Keep the complete dist\CE4011_Solver folder together.
2. Run:

   dist\CE4011_Solver\CE4011_Solver.exe

3. Do not move CE4011_Solver.exe away from its adjacent _internal folder.
   The _internal folder contains python311.dll, Tcl/Tk, NumPy, SciPy,
   Matplotlib, and the bundled demonstration data.

The build\ directory is temporary PyInstaller working output. Do not run the
application from build\, and do not submit or distribute that directory.


BUILDING FROM SOURCE

Open Anaconda Prompt or PowerShell at the repository root:

   conda activate CE4011
   python -m PyInstaller --clean --noconfirm CE4011_Solver.spec

The finished application will be created at:

   dist\CE4011_Solver\CE4011_Solver.exe


PYTHON FALLBACK

If the executable cannot be used, run the documented Python workflow from the
repository root:

   conda activate CE4011
   python scripts\run_static_gui.py


DISTRIBUTION NOTE

Distribute the entire dist\CE4011_Solver folder, preferably as a ZIP archive.
Copying only CE4011_Solver.exe will cause a "Failed to load Python DLL" error.
