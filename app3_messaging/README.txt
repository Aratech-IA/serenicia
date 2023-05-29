NOTE:
à l'intérieure des templates:
    - "¤" est utilisé pour signifier des informations customisables,
            via champ libre, valable pour tous les récipients du mail.
            Un en-tête doit être présent, pour savoir quelles
            informations doivent être intégrées. Cet en-tête est la
            chaîne de caractères non-interrompue entre deux "¤", et ce soit par
            des caractères spéciaux, soit par un espace.
            exemple:
                -La chaîne "blabla ¤nom blabla" n'as pas de variables valides
                -La chaîne "blabla ¤nom¤ blabla" as une variable valide, dont l'en-tête est "nom"
                -La chaîne "blabla ¤mon nom¤ blabla" n'as pas de variables valides
                -La chaîne "blabla ¤mon-nom¤ blabla" n'as pas de variables valides
                -La chaîne "blabla ¤mon_nom¤ blabla" as une variable valide, dont l'en-tête est "mon_nom"
                -La chaîne "blabla ¤¤ blabla" n'as pas de variables valides

        
    - "%%" est utilisé pour signifier l'emplacement de variables django.
            Ces variables django doivent, comme pour les "¤", avoir un en-tête,
            avec les mêmes règles que pour les "¤". Cet en-tête est la
            chaîne de caractères non-interrompue entre deux "%%", et ce soit par
            des caractères spéciaux(sauf le "_"), soit par un espace.
            les options pour ces variables sont limitées, et prédéterminées.
            valeures possibles :
               -"nom": le nom de la personne
               -"prénom": le prénom de la personne
               -"email": l'email de la personne
               -"groups": les groupes de la personnes (NOTE: à tester)
               --d'autres options sont à venir.
   - |_| est utilisé à un seul emplacement: dans un lien vers le logo serenicia.
   - [[ domain ]] est le STATIC_URL afin de pouvoir maitre des images, il as pour forme : "https://nomdedomaine/static/"


Pour rajouter une variable django, il est nécessaire de:
IMPORTANT: Il est nécessaire que les variables puissent être liées à un utilisateur.
(NOTE: Les mots en toute majuscule sont bien entendu à remplacer par les valeures appropriées)
    -dans textprocess.py:
        -importer les models utilisés
        -dans create_context_get_user, ajouter
            NOM = NOM_MODEL.objects.get(email__exact=recipient)
            context = {"NOM": NOM}
            NOTE:email__exact=recipient est un filtre pour ne prendre que les personnes ayant cette adresse mail exactement.
                 Si votre model n'as pas d'email individuel, vous devez utiliser un autre filtre pour permettre au contenu
                 de la variable de correctement cibler le(s) destinataire(s) du mail.

        -dans possivardjango, ajouter une clée avec votre nom de variable django et sa representation de type django en contenu.
            Le NOM du contenu doit être le même que celui défini dans create_context_get_user.
            exemple: "NOM_VAR": "{{ NOM.NOM_DU_FIELD/CHAMPS }}", 1)
        -EXEMPLE:
        def create_context_get_user(recipient, clef):
            user = User.objects.get(email__exact=recipient)
            context = {"user": user}
            return context
        def possivardjango():
            dicovardjango = {"nom": "{{ user.last_name}}", "prénom": "{{ user.first_name }}", "email": "{{ user.email }}",
                             "groups": "{{ user.groups.all }}", "identifiant": "{{ user.get_username }}"}
            return dicovardjango