import sys
import os

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
# noinspection PyPep8
import django
django.setup()

from app5_ehpad_messaging.batch.algo_affectation_V3 import main

if __name__ == "__main__":
    main()

