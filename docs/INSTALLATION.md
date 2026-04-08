# Installation — Freebox Home pour Home Assistant

Intégration des équipements **Freebox Delta** (alarme, volets, caméras, capteurs) dans Home Assistant.

> **Compatibilité** : Freebox Delta uniquement (modèle avec le pack Home)

---

## Prérequis

- Home Assistant **2023.1 ou supérieur**
- Une **Freebox Delta** avec le pack Home activé
- [HACS](https://hacs.xyz) installé dans Home Assistant *(méthode recommandée)*

---

## Méthode 1 — Via HACS (recommandée)

### Étape 1 — Ajouter le dépôt personnalisé

1. Dans Home Assistant, aller dans **HACS** → **Intégrations**
2. Cliquer sur les **3 points** en haut à droite → **Dépôts personnalisés**
3. Renseigner :
   - **URL** : `https://github.com/absolusteph-corsica/freebox_home`
   - **Catégorie** : `Intégration`
4. Cliquer sur **Ajouter**

### Étape 2 — Installer l'intégration

1. Chercher **Freebox Home** dans la liste des intégrations HACS
2. Cliquer sur **Télécharger**
3. Confirmer le téléchargement

### Étape 3 — Redémarrer Home Assistant

**Paramètres** → **Système** → **Redémarrer**

### Étape 4 — Configurer l'intégration

Voir la section [Configuration](#configuration) ci-dessous.

---

## Méthode 2 — Installation manuelle

### Étape 1 — Télécharger les fichiers

```bash
cd /config/custom_components
git clone https://github.com/absolusteph-corsica/freebox_home tmp_fbx
cp -r tmp_fbx/custom_components/freebox_home ./freebox_home
rm -rf tmp_fbx
```

Ou télécharger le ZIP depuis la [page des releases](https://github.com/absolusteph-corsica/freebox_home/releases) et extraire le dossier `custom_components/freebox_home` dans `/config/custom_components/`.

### Étape 2 — Vérifier la structure

```
config/
└── custom_components/
    └── freebox_home/
        ├── __init__.py
        ├── alarm_control_panel.py
        ├── binary_sensor.py
        ├── camera.py
        ├── config_flow.py
        ├── const.py
        ├── cover.py
        ├── manifest.json
        ├── router.py
        ├── sensor.py
        ├── services.yaml
        ├── switch.py
        └── translations/
            ├── en.json
            └── fr.json
```

### Étape 3 — Redémarrer Home Assistant

**Paramètres** → **Système** → **Redémarrer**

### Étape 4 — Configurer l'intégration

Voir la section [Configuration](#configuration) ci-dessous.

---

## Configuration

### Étape 1 — Ajouter l'intégration

1. **Paramètres** → **Appareils et services** → **Ajouter une intégration**
2. Rechercher **Freebox Home**
3. Renseigner :
   - **Hôte** : l'adresse de votre Freebox (ex: `mafreebox.freebox.fr` ou l'IP locale)
   - **Port** : le port HTTPS de l'API (ex: `443` ou le port indiqué sur `http://mafreebox.freebox.fr/api_version`)

> Pour obtenir les valeurs exactes, ouvrir `http://mafreebox.freebox.fr/api_version` depuis votre réseau local et noter `api_domain` et `https_port`.

### Étape 2 — Autoriser l'application sur la Freebox

Lorsque la page vous le demande :

1. **Appuyer sur la flèche droite** du panneau de la Freebox (bouton physique)
2. Revenir dans Home Assistant et cliquer **Soumettre**

### Étape 3 — Accorder les permissions Home

1. Ouvrir [http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts](http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts)
2. Trouver l'entrée **Home Assistant**
3. Activer la permission : **Gestion de l'alarme et maison connectée**
4. Revenir dans HA et cliquer **Soumettre**

---

## Découverte automatique (Zeroconf)

Si votre Freebox Delta est sur le même réseau local que HA, l'intégration peut être découverte automatiquement via **Zeroconf**. Une notification apparaîtra dans HA pour proposer la configuration.

> Seule la **Freebox Delta** est supportée — les autres modèles (Freebox Pop, Révolution, etc.) seront ignorés.

---

## Entités créées

Selon les équipements associés à votre Freebox Delta :

| Catégorie | Type d'entité HA | Description |
|-----------|-----------------|-------------|
| Alarme | `alarm_control_panel` | Centrale d'alarme Freebox |
| Volet RTS/IO | `cover` | Volets roulants Somfy |
| Volet basic | `cover` | Volets sans retour de position |
| Caméra | `camera` | Caméra Freebox |
| PIR | `binary_sensor` | Capteur de mouvement |
| DWS | `binary_sensor` | Capteur d'ouverture de porte |
| Batterie | `sensor` | Niveau de batterie (%) |
| Couvercle capteur | `binary_sensor` | Détection d'ouverture du boîtier |
| Inversion volet | `switch` | Inverse le sens de commande d'un volet |

---

## Mise à jour

### Via HACS
1. **HACS** → **Intégrations** → **Freebox Home**
2. Si une mise à jour est disponible, cliquer **Mettre à jour**
3. Redémarrer HA

### Manuellement
```bash
cd /config/custom_components
git clone https://github.com/absolusteph-corsica/freebox_home tmp_fbx
cp -r tmp_fbx/custom_components/freebox_home ./freebox_home
rm -rf tmp_fbx
# Puis redémarrer HA
```

---

## Désinstallation

### Via HACS
1. **HACS** → **Intégrations** → **Freebox Home** → **Supprimer**
2. **Paramètres** → **Appareils et services** → **Freebox Home** → **Supprimer l'intégration**
3. Redémarrer HA

### Manuellement
```bash
rm -rf /config/custom_components/freebox_home
```
Puis supprimer l'intégration dans HA et redémarrer.

---

## Dépannage

### L'intégration ne trouve pas la Freebox
- Vérifier que l'hôte et le port sont corrects via `http://mafreebox.freebox.fr/api_version`
- S'assurer que HACS et HA sont sur le **même réseau** que la Freebox

### Erreur "Authorization" lors de la configuration
- La demande d'autorisation a expiré — recommencer la configuration
- Le fichier de token sera automatiquement réinitialisé

### Erreur "Insufficient Permissions" après configuration
- Retourner sur [la page des comptes Freebox](http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts)
- Vérifier que la permission **Gestion de l'alarme et maison connectée** est bien activée

### Aucune entité créée après configuration
- Vérifier que des équipements Home sont bien associés à votre Freebox Delta
- Consulter les logs HA : **Paramètres** → **Système** → **Journaux** et filtrer sur `freebox_home`

---

## Liens utiles

- [Dépôt GitHub](https://github.com/absolusteph-corsica/freebox_home)
- [Signaler un bug](https://github.com/absolusteph-corsica/freebox_home/issues)
- [API Freebox](http://mafreebox.freebox.fr/api_version)
- [Paramètres des comptes Freebox](http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts)
