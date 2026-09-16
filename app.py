"""Point d'entrée Streamlit.

`runpy` réexécute le module à chaque rerun de Streamlit. Un simple `import`
ne fonctionnerait pas : Python le mettrait en cache et la page resterait vide
dès la première interaction.
"""

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

runpy.run_module("copilote.ui", run_name="__main__")