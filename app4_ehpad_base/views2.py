from .models import MotDirection, MotPoleSoins, MotHotelResto, MotCVS


def getnewlist(index, mots):
    listresult = []
    for mot in mots:
        if str(mot.id) == index:
            listresult.insert(0, mot)
        else:
            listresult.append(mot)
    return listresult


def index_comgeneral(request):
    # Récupère le dernier post
    motdirection = MotDirection.objects.last()
    motpolesoins = MotPoleSoins.objects.last()
    mothotelresto = MotHotelResto.objects.last()
    motcvs = MotCVS.objects.last()

    motsdirection = None
    textsuitedirection = None
    motspolesoins = None
    textsuitepolesoins = None
    motshotelresto = None
    textsuitehotelresto = None
    motscvs = None
    textsuitecvs = None

    if motdirection is not None:
        # Récupère les derniers titres
        # Récupère les 6 derniers post par l'id
        motsdirection = MotDirection.objects.order_by('-id')[:6]
        # Sépare le texte en 2 (40 premiers mots puis la suite)
        textsuitedirection = motdirection.text.split()[40:]

    if motpolesoins is not None:
        motspolesoins = MotPoleSoins.objects.order_by('-id')[:6]
        textsuitepolesoins = motpolesoins.text.split()[40:]

    if mothotelresto is not None:
        motshotelresto = MotHotelResto.objects.order_by('-id')[:6]
        textsuitehotelresto = mothotelresto.text.split()[40:]

    if motcvs is not None:
        motscvs = MotCVS.objects.order_by('-id')[:6]
        textsuitecvs = motcvs.text.split()[40:]

    if request.method == 'POST':
        if request.POST.get("idtextdirection"):
            motsdirection = getnewlist(request.POST.get("idtextdirection"), motsdirection)
        elif request.POST.get("idtextpolesoins"):
            motspolesoins = getnewlist(request.POST.get("idtextpolesoins"), motspolesoins)
        elif request.POST.get("idtexthotelresto"):
            motshotelresto = getnewlist(request.POST.get("idtexthotelresto"), motshotelresto)
        elif request.POST.get("idtextcvs"):
            motscvs = getnewlist(request.POST.get("idtextcvs"), motscvs)

    communication = {'motsdirection': motsdirection, 'motspolesoins': motspolesoins, 'motshotelresto': motshotelresto, 'motscvs': motscvs, 'textsuitedirection': textsuitedirection, 'textsuitepolesoins': textsuitepolesoins, 'textsuitehotelresto': textsuitehotelresto, 'textsuitecvs': textsuitecvs}

    return communication
