import sys
from pathlib import Path

# Add exercise root directory to sys.path so tests can import modules
exercise_root = Path(__file__).resolve().parent.parent
if str(exercise_root) not in sys.path:
    sys.path.insert(0, str(exercise_root))
