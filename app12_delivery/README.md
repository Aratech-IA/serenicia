Notice application de livraison
=

Instalation :
- 

<p>Afin de mettre en place toutes les tables de données qui permet le bon fonctionnement veuillez lancer la commande surivant dans le dossier racine de votre projet.<p>

>  

> python3 manage makemigartions

> python3 manage migrate

> python3 app12_delivery/batch/install_cron.py  

Ce rendre dans l'admin de votre site dans le section -> AUTHENTIFICATION ET AUTORISATION -> Utilisateurs -> Ajout un utilisateur

!! le profile entreprise doit être unique et donc le seul à avoir le groupe Delivery Business !!
Remplir les champs suivants : 
    - Nom d’utilisateur 
    - Mot de passe
    - Confirmation du mot de passe
    - Prénom (nom de l'entreprise)
    - Nom de famille (nom de l'entreprise une deuxième fois)
    - Groupes : -> Selectionner l'option "Delivery Business" -> appuyer sur la fleche pour ajouter le groupe à l'utilisateur
    - 
</p>


Section tri par order de livraison 
-
<p>Le fichier de gestion d'ordre des tournées ce situe à la racine du module (application)</p>

> python3 manage shell

> from app14.auto_ordering_tour import ordering_tour

> ordering_tour() 

> Pour sortir de l'interpreteur python3 taper Crlt + d   OU    exit()

Section map :
-
Dans le cas d'un deploiement pour une seul entreprise 

1. Créer un compte pour l'entreprise (attribution pour le fichier auto_ordering_delivery)
2. Créer une clef de l'API mapBox pour chaque uilisateur afin de garder la gratuitée du service (division des requêtes)

Section Profile
-