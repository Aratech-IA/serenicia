import os
import sys

import requests
import json
import time
from .models import Client
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact with the Django database
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

import requests
import json
from app1_base.models import Client
from app4_ehpad_base.models import ProfileSerenicia
from datetime import timedelta, datetime


@csrf_exempt
def get_client(request, password):
    if password == "aicnevuoj*26":
        client = list(ProfileSerenicia.objects.all().values('user__first_name', 'user__last_name',
                                                            'user__groups__name', 'folder'))
        return JsonResponse(client, safe=False)
    else:
        time.sleep(60)


@csrf_exempt
def get_client_inactive(request, password):
    if password == "aicnevuoj*26":
        date_filter = datetime.now().date() - timedelta(weeks=1)
        client = list(ProfileSerenicia.objects.filter(status='deceased',
                                                      date_status_deceased__lte=date_filter).values('user__first_name',
                                                                                                    'user__last_name',
                                                                                                    'folder'))
        return JsonResponse(client, safe=False)
    else:
        time.sleep(60)


def updatelocaldatabase():
    """Update the local database from Netsoins/Titan database   return True when finish"""
    try:
        # get all the residents from the netsoins's database
        queryset_result = requests.get(
            "https://test.netsoins.org/webservice.php/teranga/Resident?type=teranga&key=1dfqgaf1grd4vz4g0axrahibr81ibbks1o8obrd1%20&output=json&statut_actif=tous&statut_archive=tous",
            timeout=60
        )
        # parse json
        result = json.loads(queryset_result.text)
        # get the list of resident to iterate
        listresident = result['Resident']
        for resident in listresident:
            print("\n\n resident :", resident)
            # update or create a resident from app1_base.models (client)
            # TODO sécuriser en cas d'homonyme, voir ajout de clé externe dans APP1.models.Client
            created_obj, iscreated = Client.objects.update_or_create(first_name=resident['Prenom'],
                                                                     name=resident['Nom']
                                                                     )
            print("\n", created_obj.id, " ", created_obj.name, "is created : ", iscreated)
            # update or create a resident from app4_ehpad_base.models (clientsserenicia extension)
            ClientsSerenicia.objects.update_or_create(client=created_obj,
                                                      external_key=resident['IdentifiantAdministratif']
                                                      )
            # check different available fields to update
            if "EtablissementChambre" in resident:
                print("\najout numéro chambre")
                ClientsSerenicia.objects.filter(external_key=resident['IdentifiantAdministratif']).update(
                    room_number=resident['EtablissementChambre']['Libelle'])
            if "VilleNaissance" in resident:
                print("\najout ville de naissance")
                ClientsSerenicia.objects.filter(external_key=resident['IdentifiantAdministratif']).update(
                    birth_city=resident['VilleNaissance'])
            if "DateNaissance" in resident:
                print("\najout date de naissance")
                ClientsSerenicia.objects.filter(external_key=resident['IdentifiantAdministratif']).update(
                    birth_date=resident['DateNaissance'].split('T')[0])
            if "DateEntree" in resident:
                print("\najout date d'entrée")
                ClientsSerenicia.objects.filter(external_key=resident['IdentifiantAdministratif']).update(
                    entry_date=resident['DateEntree'].split('T')[0])
        return True
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
        raise Exception(err)


def updatedistantdatabase():
    """Update the distant database from the local database  return True when finish"""
    # get the list of local resident
    local_database = Client.objects.all()
    # url POST request to netsoin Resident's database
    url = "https://test.netsoins.org/webservice.php/teranga/Resident?type=teranga&key=1dfqgaf1grd4vz4g0axrahibr81ibbks1o8obrd1%20&input=json&output=json"
    for resident in local_database:
        print("resident :", resident)
        # create temp object to send
        tmpdata = [{
            "IdentifiantExterne": str(resident.id),
            "IdentifiantAdministratif": str(resident.clientsserenicia.external_key),
            "Actif": 1,
            "Nom": resident.name,
            "Prenom": resident.first_name,
            "VilleNaissance": resident.clientsserenicia.birth_city,
            "DateNaissance": str(resident.clientsserenicia.birth_date) + "T00:00:00.0000"
        }]
        # json encoder
        jsondata = json.dumps(tmpdata)
        print("\ndata format json : ", tmpdata)
        try:
            print("\nPOST !")
            ret = requests.post(url, data=jsondata, timeout=60)
            ret = json.loads(ret.text)
            print("\nretour de roquette :", ret)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
            raise Exception(err)
    return True

# Champs POST Resident disponibles pour Netsoin :

# [
#   {
#     "IdentifiantExterne": "string",
#     "Actif": 1,
#     "Archive": 1,
#     "Civilite": "MONSIEUR",
#     "Genre": "HOMME",
#     "Nom": "string",
#     "NomJeuneFille": "string",
#     "NomReligion": "string",
#     "Prenom": "string",
#     "Nationalite": "string",
#     "Telephone": "string",
#     "Mail": "string",
#     "DateNaissance": "2020-09-29T09:51:44.599Z",
#     "CodePostalNaissance": "string",
#     "VilleNaissance": "string",
#     "IdentifiantDepartementNaissance": 11,
#     "IdentifiantPaysNaissance": "004",
#     "SituationFamiliale": "CELIBATAIRE",
#     "UriResidentCouple": "string",
#     "IdentifiantAdministratif": "string",
#     "ResidentPieceIdentite": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "TypePieceIdentite": "CARTE_IDENTITE",
#         "UriPersonnel": "string",
#         "Date": "2020-09-29T09:51:44.599Z",
#         "DateDemande": "2020-09-29T09:51:44.599Z",
#         "DateDebut": "2020-09-29T09:51:44.599Z",
#         "DateFin": "2020-09-29T09:51:44.599Z",
#         "Numero": "string",
#         "DemandeEnCours": 0,
#         "DelivrerPar": "string",
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "AccordReglement": 0,
#     "DateAccordReglement": "2020-09-29T09:51:44.600Z",
#     "AssuranceResponsabiliteCivile": "string",
#     "NumeroAssuranceResponsabiliteCivile": "string",
#     "DateDebutAssuranceResponsabiliteCivile": "2020-09-29T09:51:44.600Z",
#     "DateFinAssuranceResponsabiliteCivile": "2020-09-29T09:51:44.600Z",
#     "CommentaireContrat": "string",
#     "ProvenanceIdentifiantProximite": "AGGLOMERATION",
#     "ProvenanceProximiteIdentifiantPays": "004",
#     "IdentifiantProvenance": "FAMILLE",
#     "ProvenanceFiness": "string",
#     "ProvenanceLibelle": "string",
#     "ProvenanceAdresse": "string",
#     "ProvenanceCodePostal": "string",
#     "ProvenanceVille": "string",
#     "ProvenanceIdentifiantDepartement": 11,
#     "ProvenanceIdentifiantPays": "004",
#     "ProvenanceTelephoneFixe": "string",
#     "ProvenanceAutreTelephoneFixe": "string",
#     "IdentifiantModeResidence": "AUCUN",
#     "DernierDomicileAdresse": "string",
#     "DernierDomicileCodePostal": "string",
#     "DernierDomicileVille": "string",
#     "DernierDomicileIdentifiantDepartement": 11,
#     "DernierDomicileIdentifiantPays": "004",
#     "DernierDomicileTelephoneFixe": "string",
#     "DernierDomicileAutreTelephoneFixe": "string",
#     "DomicileSecoursAdresse": "string",
#     "DomicileSecoursCodePostal": "string",
#     "DomicileSecoursVille": "string",
#     "DomicileSecoursIdentifiantDepartement": 11,
#     "DomicileSecoursIdentifiantPays": "004",
#     "DomicileSecoursTelephoneFixe": "string",
#     "DomicileSecoursAutreTelephoneFixe": "string",
#     "ResidentSecuriteSociale": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriSecuriteSociale": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "NumeroSecuriteSociale": "string",
#         "PetitRegime": "string",
#         "CodeBeneficiaire": "ASSURE",
#         "Nom": "string",
#         "Prenom": "string",
#         "Justificatif": "string",
#         "Adresse": "string",
#         "CodePostal": "string",
#         "Ville": "string",
#         "IdentifiantPays": "004",
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "ResidentMutuelle": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriMutuelle": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "ValiditePermanente": 0,
#         "Numero": "string",
#         "Principale": 0,
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "ResidentCaisse": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriCaisse": "string",
#         "Principale": 0,
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "ValiditePermanente": 0
#       }
#     ],
#     "ResidentAide": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "IdentifiantTypeAide": "ACS",
#         "DateDemande": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "DateRetroactivite": "2020-09-29T09:51:44.600Z",
#         "NumeroDossier": "string",
#         "Commentaire": "string",
#         "AideLogementMontant": 0,
#         "AideLogementIdentifiantTypeAideLogement": "APL",
#         "AideLogementIdentifiantTypeVersement": "RESIDENT",
#         "AideSocialeIdentifiantTypeAideSociale": "HEBERGEMENT_UNIQUEMENT",
#         "AideSocialeDateRemise": "2020-09-29T09:51:44.600Z",
#         "AideSocialeDateAcceptation": "2020-09-29T09:51:44.600Z",
#         "AideSocialeResteACharge": 0,
#         "AideSocialePecule": 0,
#         "AideSocialePeculeMontant": 0,
#         "AideSocialePeculePourcent": 0,
#         "AideSocialeReversementConseilGeneral": 0,
#         "AideSocialeIdentifiantTypeVersement": "RESIDENT",
#         "APAMontant": 0,
#         "APAFrequence": "string",
#         "APAIdentifiantTypeVersement": "CALCUL_ETABLISSEMENT",
#         "Departement": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "DerogationGIR60": 0,
#     "DroitVote": 0,
#     "DroitVoteCommentaire": "string",
#     "ResidentPraticien": [
#       {
#         "IdentifiantExterne": "string",
#         "UriPersonnel": "string",
#         "MedecinTraitant": 0,
#         "PharmacienTraitant": 0,
#         "Referent": 0,
#         "Kine": 0,
#         "Commentaire": "string"
#       }
#     ],
#     "OrganismePompeFunebre": "string",
#     "NumeroContratObseques": "string",
#     "Cremation": 0,
#     "PaceMaker": 0,
#     "DateControlePaceMaker": "2020-09-29T09:51:44.600Z",
#     "CommentairePaceMaker": "string",
#     "CommentaireAuQuotidien": "string",
#     "CommentaireInformationsGenerales": "string",
#     "ResidentContact": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "IdentifiantAdministratif": "string",
#         "LienParente": "PERE_MERE",
#         "Civilite": "MONSIEUR",
#         "Genre": "HOMME",
#         "Nom": "string",
#         "NomJeuneFille": "string",
#         "NomReligion": "string",
#         "Prenom": "string",
#         "DateNaissance": "2020-09-29T09:51:44.600Z",
#         "CodePostalNaissance": "string",
#         "VilleNaissance": "string",
#         "IdentifiantDepartementNaissance": 11,
#         "IdentifiantPaysNaissance": "004",
#         "Adresse": "string",
#         "CodePostal": "string",
#         "Ville": "string",
#         "IdentifiantDepartement": 11,
#         "IdentifiantPays": "004",
#         "Mail": "string",
#         "TelephoneFixe": "string",
#         "AutreTelephoneFixe": "string",
#         "TelephoneProfessionnel": "string",
#         "TelephoneMobile": "string",
#         "AutreTelephoneMobile": "string",
#         "TelephoneVacances": "string",
#         "Fax": "string",
#         "PrevenirLaNuit": 1,
#         "ReferentFamilial": 1,
#         "PersonneDeConfiance": 1,
#         "Commentaire": "string",
#         "OrdreAppel": 0,
#         "TypeRelationAutre": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ],
#         "DestinataireFacture": true,
#         "CautionSolidaire": true
#       }
#     ],
#     "ResidentInventaire": [
#       {
#         "IdentifiantExterne": "string",
#         "UriInventaire": "string",
#         "Prix": 0,
#         "Commentaire": "string",
#         "TrousseauHospitalisation": 0,
#         "UriPersonnel": "string"
#       }
#     ],
#     "CompteTiers": "string",
#     "CompteAuxiliaire": "string",
#     "FacturationCouple": 1,
#     "FacturationAdresse": "string",
#     "FacturationCodePostal": "string",
#     "FacturationVille": "string",
#     "FacturationIdentifiantDepartement": 11,
#     "FacturationIdentifiantPays": "004",
#     "FacturationTelephoneFixe": "string",
#     "FacturationAutreTelephoneFixe": "string",
#     "FacturationCommentaire": "string",
#     "FacturationCommentaireFacture": "string",
#     "FacturationDateDebutCommentaireFacture": "2020-09-29T09:51:44.600Z",
#     "FacturationDateFinCommentaireFacture": "2020-09-29T09:51:44.600Z",
#     "ModeReglement": "ACOMPTE",
#     "ModeReglementTitulaire": "string",
#     "UriBanqueModeReglement": "string",
#     "ModeReglementBic": "string",
#     "ModeReglementRib": "string",
#     "ModeReglementIban": "string",
#     "ModeReglementJourEcheance": 0,
#     "ModeReglementDateAutorisation": "2020-09-29T09:51:44.600Z",
#     "ModeReglementIdentifiantComptableSEPA": "string",
#     "Mandat": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Rum": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "ModeReglement": "ACOMPTE",
#         "ModeReglementTitulaire": "string",
#         "UriBanqueModeReglement": "string",
#         "ModeReglementBic": "string",
#         "ModeReglementRib": "string",
#         "ModeReglementIban": "string",
#         "ModeReglementJourEcheance": 0,
#         "ModeReglementDateAutorisation": "2020-09-29T09:51:44.600Z",
#         "ModeReglementIdentifiantComptableSEPA": "string",
#         "Recurrent": 1,
#         "DatePremier": "2020-09-29T09:51:44.600Z",
#         "IdentifiantComptableMandat": "string",
#         "IdentifiantExterneResidentContact": "string"
#       }
#     ],
#     "ResidentDebiteur": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Montant": "string",
#         "Pourcentage": "string",
#         "ModeParticipation": "MODE_MONTANT",
#         "PosteParticipation": "POSTE_RESTEACHARGE",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Ordre": "string",
#         "CompteTiers": "string",
#         "CompteAnalytique": "string",
#         "CompteAuxiliaire": "string",
#         "Commentaire": "string",
#         "ModeReglement": "ACOMPTE",
#         "ReglementTitulaire": "string",
#         "UriReglementBanque": "string",
#         "ReglementNumero": "string",
#         "ReglementIban": "string",
#         "ReglementBic": "string",
#         "ReglementJourEcheance": 0,
#         "ReglementDateAutorisation": "2020-09-29T09:51:44.600Z",
#         "ReglementIdentifiantComptable": "string",
#         "IdentifiantExterneResidentContact": "string"
#       }
#     ],
#     "ResidentPathologie": [
#       {
#         "IdentifiantExterne": "string",
#         "UriPathologie": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Fini": 0,
#         "UriPersonnel": "string",
#         "DansEtablissement": 0,
#         "Antecedent": "CHIRURGICAL"
#       }
#     ],
#     "ResidentAld": [
#       {
#         "IdentifiantExterne": "string",
#         "UriPathologie": "string",
#         "ValiditePermanente": 0,
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "TypeAld": "CNAM",
#         "Commentaire": "string"
#       }
#     ],
#     "ResidentHypersensibilite": [
#       {
#         "IdentifiantExterne": "string",
#         "UriHypersensibilite": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Fini": 0,
#         "UriPersonnel": "string",
#         "Alimentaire": 0
#       }
#     ],
#     "ResidentVaccin": [
#       {
#         "IdentifiantExterne": "string",
#         "UriVaccin": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "NumeroLot": "string",
#         "Commentaire": "string",
#         "PriseEnCharge": "NON",
#         "StopAlerte": 0,
#         "Refuse": 0,
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentBacterie": [
#       {
#         "IdentifiantExterne": "string",
#         "UriBacterie": "string",
#         "UriProtocole": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Fini": 0,
#         "UriPersonnel": "string",
#         "DansEtablissement": 0,
#         "Precaution": 0,
#         "PrecautionAir": 0,
#         "PrecautionGouttelette": 0,
#         "PrecautionContact": 0
#       }
#     ],
#     "ResidentRisque": [
#       {
#         "IdentifiantExterne": "string",
#         "UriRisque": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z"
#       }
#     ],
#     "ResidentRegime": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTypeRegime": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentTexture": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTexture": "string",
#         "UriTextureComplement": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Commentaire": "string",
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentModeAlimentation": [
#       {
#         "IdentifiantExterne": "string",
#         "UriModeAlimentation": "string",
#         "Commentaire": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentComplementAliment": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTypeComplementAlimentaire": "string",
#         "UriComplementAlimentaireForme": "string",
#         "Commentaire": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "FormeAutre": "string"
#       }
#     ],
#     "ResidentBoisson": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTypeBoisson": "string",
#         "UriPersonnel": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Commentaire": "string"
#       }
#     ],
#     "BonneHydratation": 0,
#     "BoitSeule": 0,
#     "StimulationPourBoire": 0,
#     "HydratationCommentaire": "string",
#     "AlimentationAlcool": 0,
#     "Douloureux": 0,
#     "TroubleHumeurComportement": 0,
#     "AnomaliePied": 0,
#     "TroubleSensibilite": 0,
#     "Sourd": 0,
#     "AppareilAuditif": 0,
#     "Malvoyant": 0,
#     "AppareilVisuel": 0,
#     "MobiliteReduite": 0,
#     "TypeAideTechnique": "AUCUNE",
#     "Desorientation": 0,
#     "Deambulant": 0,
#     "AidePriseMedicament": 0,
#     "TraitementsEcrases": 0,
#     "AideAlimentaire": 0,
#     "TroubleDeglutition": 0,
#     "ResidentTransfusion": [
#       {
#         "IdentifiantExterne": "string",
#         "Commentaire": "string",
#         "DateFait": "2020-09-29T09:51:44.600Z",
#         "DateSaisie": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string"
#       }
#     ],
#     "DerniereProfession": "string",
#     "NombreEnfantsTotal": 0,
#     "NombreEnfantsDecedes": 0,
#     "ResidentConsentement": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "ConstanteConsentement": "TELEMEDECINE",
#         "ConstanteAccord": "NON",
#         "UriPersonnel": "string",
#         "UriPersonnelReccueillant": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateAccord": "2020-09-29T09:51:44.600Z",
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "Photo": {
#       "IdentifiantExterne": "string",
#       "Actif": 1,
#       "Nom": "string",
#       "Type": "string",
#       "Donnees": "Unknown Type: base64Binary"
#     },
#     "FichierInfo": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoMedical": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoFacturation": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoProjetDeVie": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoAlimentation": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoAdministratif": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "ResidentContrat": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "NomContrat": "string",
#         "PrenomContrat": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFinFacturation": "2020-09-29T09:51:44.600Z",
#         "DateVersement": "2020-09-29T09:51:44.600Z",
#         "ModeVersement": "CHEQUE",
#         "TypeContrat": "CONTRAT_DE_SOUTIEN_ET_D_AIDE_PAR_LE_TRAVAIL",
#         "TypeContratSejour": "HEBERGEMENT_TEMPORAIRE",
#         "TitulaireCompte": "string",
#         "JoursPreavis": "string",
#         "Terme": "string",
#         "MontantHT": 0,
#         "MontantTTC": 0,
#         "MontantTTCReservation": 0,
#         "MontantTTCMoins60Ans": 0,
#         "MontantTTCReservation60": 0,
#         "ModeTTC": "string",
#         "UriArticle": "string",
#         "MontantArticleForfaitJournalier": 0,
#         "MontantArticleForfaitHospitalier": 0,
#         "MontantArticleForfaitPsy": 0,
#         "UriBanque": "string",
#         "UriConseilGeneralDependance": "string",
#         "SansDependance": 0,
#         "NumeroCheque": "string",
#         "Commentaire": "string",
#         "CommentaireRestitution": "string",
#         "MontantRestitution": 0,
#         "DateRestitution": "2020-09-29T09:51:44.600Z",
#         "PrixFacture": 0,
#         "DelaiRestitution": 0,
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "ResidentArticle": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriArticle": "string",
#         "Quantite": 0,
#         "MontantUnitaireTTC": 0,
#         "Frequence": "PONCTUEL",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Presentiel": 1,
#         "CarenceHospitalisation": 0,
#         "CarenceVacances": 0,
#         "AideSociale": 1,
#         "Commentaire": "string"
#       }
#     ],
#     "AlimentationInterdit": "string",
#     "ResidentQuantiteRepas": [
#       {
#         "IdentifiantExterne": "string",
#         "UriMomentRepas": "string",
#         "Quantite": "NORMAL",
#         "Commentaire": "string"
#       }
#     ],
#     "PriseDuRepas": "AUTONOME",
#     "AlimentationAccompagnement": 0,
#     "RepasCommentaireAutonomie": "string",
#     "AdresseEtablissementFacturation": 0
#   }
# ]
