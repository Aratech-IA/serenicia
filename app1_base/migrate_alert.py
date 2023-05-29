import sys, os

# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django
django.setup()


from app1_base.models import Alert, AlertStuffsChoice

alert = Alert.objects.all()

for a in alert:
    a.action_char = a.get_actions_display()
    b = AlertStuffsChoice.objects.get(stuffs=a.get_stuffs_display())
    a.stuffs_char_foreign = b
    try:
        a.save()
    except django.db.IntegrityError:
        print('duplicate')



