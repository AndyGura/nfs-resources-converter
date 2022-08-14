import inspect
import os
import sys

import eel

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

eel.init('frontend/dist/gui')
eel.start('index.html')
