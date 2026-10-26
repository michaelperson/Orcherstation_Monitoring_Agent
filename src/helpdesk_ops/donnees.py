"""Données fictives de NordTech SA (en vrai : une CMDB, un outil de ticketing, une base de connaissances).

Aucune donnée réelle. La KB complète, ingérée dans Qdrant, arrive en J3 (data/).
"""

CATEGORIES = ["reseau", "materiel", "logiciel", "acces", "autre"]

INVENTAIRE = {
    "srv-mail-01": "en ligne",
    "srv-erp-02": "hors ligne",
    "srv-vpn-01": "en ligne",
    "srv-fichiers-03": "dégradé (disque à 92 %)",
}

TICKETS_OUVERTS = {"N1": 14, "N2-infra": 6, "N2-applicatif": 3}

KB = [
    {"id": "KB-001", "titre": "Configurer le client VPN NordTech Connect",
     "contenu": "Installer NordTech Connect depuis le Centre logiciel, serveur vpn.nordtech.example, "
                "se connecter avec son compte et valider la notification MFA sur le téléphone."},
    {"id": "KB-002", "titre": "Réinitialiser son mot de passe",
     "contenu": "Aller sur le portail self-service, répondre aux questions de sécurité, "
                "choisir un mot de passe de 14 caractères minimum. Le help-desk ne demande jamais votre mot de passe."},
    {"id": "KB-003", "titre": "Imprimante bloquée ou file d'impression figée",
     "contenu": "Éteindre l'imprimante 30 secondes, vider la file d'impression depuis Paramètres > Imprimantes, "
                "puis relancer l'impression."},
    {"id": "KB-004", "titre": "Outlook plante à l'ouverture d'une pièce jointe",
     "contenu": "Lancer Outlook en mode sans échec (outlook.exe /safe), désactiver les compléments, "
                "puis rouvrir la pièce jointe."},
    {"id": "KB-005", "titre": "Wi-Fi des salles de réunion",
     "contenu": "Se connecter au réseau NordTech-Meet. En cas de coupures répétées, oublier le réseau "
                "puis s'y reconnecter ; si le problème persiste, ouvrir un ticket réseau."},
]
