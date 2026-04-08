# Plan d'implémentation — Corrections et améliorations Freebox Home

> Issu de l'audit complet du code réalisé le 06/04/2026.

## Objectif

Corriger les bugs critiques (crashs, logique inversée), moderniser l'intégration pour les APIs Home Assistant actuelles, supprimer le code mort, et améliorer la sécurité et la maintenabilité.

Le plan est découpé en **5 phases** indépendamment vérifiables, ordonnées par priorité.

## Dépendances entre les phases

```
Phase 1 (P0 — Bugs critiques)
    │
    ▼
Phase 2 (P1 — Bugs importants)
    │
    ├──► Phase 3 (P2 — Modernisation HA)   ─┐
    ├──► Phase 4 (P2-P3 — Nettoyage)        ├── parallélisables
    └──► Phase 5 (P2-P3 — Sécurité)        ─┘
```

---

## Phase 1 — Bugs critiques (P0)

### 1.1 Corriger les erreurs de syntaxe dans `alarm_state`

- **Fichier** : `alarm_control_panel.py`, propriété `alarm_state`
- **Bug A (ligne ~157)** : `SAlarmControlPanelState.ARMING` → typo, `S` en trop → `NameError`
- **Bug B (ligne ~163)** : `returnAlarmControlPanelState.TRIGGERED` → espace manquant → `NameError`
- **Correction** :
  ```python
  # Bug A
  - return SAlarmControlPanelState.ARMING
  + return AlarmControlPanelState.ARMING

  # Bug B
  - returnAlarmControlPanelState.TRIGGERED
  + return AlarmControlPanelState.TRIGGERED
  ```

### 1.2 Corriger la logique inversée du capteur PIR

- **Fichier** : `binary_sensor.py`, méthode `FreeboxPir.async_update_pir()`
- **Bug** : La condition `==` devrait être `!=`, et la valeur assignée est inversée
- **Impact** : Affecte aussi `FreeboxDws` (héritage)
- **Correction** :
  ```python
  - if( self._detection == detection ):
  -     self._detection = not detection
  + if self._detection != detection:
  +     self._detection = detection
  ```

### 1.3 Protéger `fbx.close()` dans le config flow

- **Fichier** : `config_flow.py`, méthode `async_step_permission()`
- **Bug** : Si `get_api()` lève une exception, `fbx` n'est pas défini mais le `finally` tente `await fbx.close()` → `UnboundLocalError`
- **Correction** :
  ```python
  + fbx = None
    try:
        fbx = await get_api(self.hass, self._host, self._port)
        ...
    finally:
  -     await fbx.close()
  +     if fbx is not None:
  +         await fbx.close()
  ```

### ✅ Vérification Phase 1

- [ ] Charger l'intégration → aucune `NameError` / `UnboundLocalError` dans les logs
- [ ] Tester le changement d'état de l'alarme vers `alarm2_arming` et `alarm2_alert_timer`
- [ ] Vérifier que les capteurs PIR et DWS reflètent correctement l'état détecté/non-détecté
- [ ] Simuler une erreur de connexion dans le config flow → le `finally` ne crashe pas

---

## Phase 2 — Bugs importants (P1)

> Dépend de la validation de la Phase 1.

### 2.1 Remplacer `time.sleep()` par `asyncio.sleep()`

- **Fichier** : `alarm_control_panel.py`
- **Méthodes** : `async_alarm_disarm()`, `async_alarm_arm_away()`, `async_alarm_arm_night()`
- **Problème** : `time.sleep(1)` bloque toute la boucle asyncio de HA pendant 1 seconde
- **Correction** :
  ```python
  + import asyncio
  - import time

  - time.sleep(1)
  + await asyncio.sleep(1)
  ```

### 2.2 Corriger le doublon timeout3/timeout2

- **Fichier** : `alarm_control_panel.py`, méthode `update_parameters()`
- **Bug** : `timeout2` n'est jamais lu, `timeout3` est testé deux fois (2ème branche = code mort)
- **Correction** :
  ```python
  - elif( endpoint["name"] == "timeout3" ):
  -     self._timeout2 = endpoint["value"]
  + elif( endpoint["name"] == "timeout2" ):
  +     self._timeout2 = endpoint["value"]
  ```

### 2.3 Initialiser tous les attributs dans `FreeboxCamera.__init__`

- **Fichier** : `camera.py`, méthode `FreeboxCamera.__init__()`
- **Problème** : Les attributs (`_flip`, `_motion_threshold`, etc.) ne sont jamais initialisés. Si `update_parameters()` ne trouve pas l'endpoint correspondant, les `@property` lèvent un `AttributeError`.
- **Correction** : Ajouter avant l'appel à `update_parameters()` :
  ```python
  self._motion_detection_enabled = False
  self._activation_with_alarm = False
  self._high_quality_video = False
  self._motion_sensitivity = 0
  self._motion_threshold = 0
  self._flip = False
  self._timestamp = None
  self._volume_micro = 0
  self._sound_detection = False
  self._sound_trigger = False
  self._rtsp = None
  self._disk = None
  ```

### 2.4 Protéger `os.remove()` dans `remove_config`

- **Fichier** : `router.py`, fonction `remove_config()`
- **Bug** : `os.remove(token_file)` lève `FileNotFoundError` si le fichier n'existe pas
- **Correction** :
  ```python
  - os.remove(token_file)
  + try:
  +     os.remove(token_file)
  + except FileNotFoundError:
  +     _LOGGER.warning("Token file not found: %s", token_file)
  ```

### ✅ Vérification Phase 2

- [ ] L'armement/désarmement de l'alarme ne bloque plus l'interface
- [ ] Dans les logs : `timeout1`, `timeout2`, `timeout3` sont correctement lus
- [ ] Accéder aux attributs d'une caméra juste après sa création (avant le premier update) → aucun `AttributeError`
- [ ] `remove_config` avec fichier absent → pas de crash

---

## Phase 3 — Modernisation Home Assistant (P2)

> Parallélisable avec les Phases 4 et 5.

### 3.1 Migrer `FreeboxBatterySensor` vers `SensorEntity`

- **Fichier** : `sensor.py`
- Importer `SensorEntity` depuis `homeassistant.components.sensor`
- Changer l'héritage : `class FreeboxBatterySensor(FreeboxBaseClass, SensorEntity)`
- Remplacer les propriétés :
  - `state` → `native_value`
  - `unit_of_measurement` → `native_unit_of_measurement`

### 3.2 Migrer `device_info` vers `DeviceInfo`

- **Fichier** : `base_class.py`
- Importer `DeviceInfo` depuis `homeassistant.helpers.device_registry`
- Modifier la property `device_info` pour retourner un objet `DeviceInfo(...)` au lieu d'un dict brut :
  ```python
  return DeviceInfo(
      identifiers={(DOMAIN, self._id)},
      name=self._device_name,
      manufacturer=self._manufacturer,
      model=self._model,
      sw_version=self._firmware,
  )
  ```

### 3.3 Migrer `state_attributes` → `extra_state_attributes`

- **Fichier** : `camera.py`
- Renommer la property `state_attributes` en `extra_state_attributes`
- Ne pas appeler `super().state_attributes` — retourner un dict indépendant

### 3.4 Moderniser `async_unload_entry`

- **Fichier** : `__init__.py`
- Remplacer le pattern `asyncio.gather` par :
  ```python
  unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
  ```
- Supprimer `import asyncio`

### 3.5 Corriger la signature de `async_set_cover_position`

- **Fichier** : `cover.py`, classe `FreeboxShutter`
- Changer la signature :
  ```python
  - async def async_set_cover_position(self, position, **kwargs):
  + async def async_set_cover_position(self, **kwargs):
  +     position = kwargs.get("position")
  ```

### 3.6 Supprimer `CONNECTION_CLASS` deprecated

- **Fichier** : `config_flow.py`
- Supprimer la ligne `CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL`

### ✅ Vérification Phase 3

- [ ] Capteur batterie affiché correctement avec unité %
- [ ] Devices dans le registre avec manufacturer, model, sw_version corrects
- [ ] Attributs supplémentaires de la caméra visibles dans les détails de l'entité
- [ ] Unload/reload de l'intégration sans erreur
- [ ] Position volet via slider HA fonctionnelle

---

## Phase 4 — Nettoyage du code (P2-P3)

> Parallélisable avec les Phases 3 et 5.

### 4.1 Supprimer le code mort

| Fichier | Code à supprimer |
|---------|-----------------|
| `alarm_control_panel.py` | Bloc commenté `set_state()` (~lignes 139-155) |
| `camera.py` | Ancien `async_setup_entry` + `add_entities` commentés (~lignes 55-80) |
| `binary_sensor.py` | Classe `FreeboxDws` commentée (~lignes 93-130) |
| `cover.py` | Commentaires de debug liés à `DUMMY` |

### 4.2 Supprimer les imports inutilisés

| Fichier | Imports à supprimer |
|---------|-------------------|
| `camera.py` | `json`, `aiohttp`, `async_timeout`, `collections`, `asyncio`, `callback`, `async_dispatcher_connect`, constantes HTTP/auth non utilisées (`CONF_AUTHENTICATION`, `CONF_PASSWORD`, `CONF_USERNAME`, `CONF_VERIFY_SSL`, `HTTP_BASIC_AUTHENTICATION`, `HTTP_DIGEST_AUTHENTICATION`), constantes generic non utilisées (`CONF_CONTENT_TYPE`, `CONF_LIMIT_REFETCH_TO_URL_CHANGE`, `CONF_STILL_IMAGE_URL`, `CONF_FRAMERATE`) |
| `__init__.py` | `vol`, `discovery`, `asyncio` (après Phase 3.4) |
| `cover.py` | `json`, `callback`, `async_dispatcher_connect`, `STATE_CLOSING`, `STATE_OPENING` |
| `alarm_control_panel.py` | `json`, `async_timeout`, `time` (après Phase 2.1) |

### 4.3 Corriger les type hints

- Partout : `Dict[str, any]` → `Dict[str, Any]` (majuscule sur `Any`)
- Fichiers impactés : `base_class.py`, `alarm_control_panel.py`, `binary_sensor.py`

### 4.4 Nettoyer le style (optionnel)

- Supprimer les parenthèses inutiles dans les `if(...)` → `if ...:`
- Supprimer les points-virgules en fin de ligne
- Harmoniser les espaces autour des `=`
- Peut être fait via un formatter (`ruff format`, `black`)

### ✅ Vérification Phase 4

- [ ] `ruff check` ou `pylint` sans warning d'import inutilisé
- [ ] L'intégration charge toujours correctement après le nettoyage
- [ ] Aucune régression fonctionnelle

---

## Phase 5 — Sécurité et robustesse (P2-P3)

> Parallélisable avec les Phases 3 et 4.

### 5.1 Ne pas stocker/exposer le code PIN

- **Fichier** : `alarm_control_panel.py`
- Supprimer `self._pin = endpoint["value"]` ou masquer la valeur (`****`) dans tout log ou attribut exposé
- Le PIN ne doit jamais apparaître dans les logs, même en mode debug

### 5.2 Réduire la fréquence de polling des capteurs PIR/DWS

- **Fichier** : `binary_sensor.py`
- `FreeboxPir` : `timedelta(seconds=1)` → `timedelta(seconds=5)`
- `FreeboxDws` : hérite la même modification
- `FreeboxSensorCover` : conserver `timedelta(seconds=3)` (acceptable)
- **Impact** : Réduit significativement la charge CPU et réseau (~5× moins de requêtes API)

### 5.3 Valider le path dans `remove_config`

- **Fichier** : `router.py`
- Vérifier que `token_file` est bien un enfant de `freebox_path` avant de le supprimer :
  ```python
  token_file = Path(f"{freebox_path}/{slugify(host)}.conf")
  if not token_file.resolve().is_relative_to(Path(freebox_path).resolve()):
      _LOGGER.error("Invalid token file path: %s", token_file)
      return
  ```

### 5.4 Envisager la migration du stockage d'inversion (optionnel)

- **Fichier** : `switch.py`
- Remplacer `path.write_text('1')` / `path.read_text()` par `Store` de HA pour un stockage JSON plus robuste
- OU conserver le mécanisme actuel mais ajouter un `try/except` autour de l'écriture

### ✅ Vérification Phase 5

- [ ] Le PIN n'apparaît nulle part dans les logs ni les attributs d'entité
- [ ] Charge CPU/réseau réduite (observable dans les logs avec le niveau DEBUG)
- [ ] Tenter `remove_config` avec un host contenant des caractères spéciaux → pas de suppression inattendue


---

## Récapitulatif des fichiers impactés

| Fichier | Phases |
|---------|--------|
| `alarm_control_panel.py` | 1.1, 2.1, 2.2, 4.1, 4.2, 5.1 |
| `binary_sensor.py` | 1.2, 4.1, 4.3, 5.2 |
| `config_flow.py` | 1.3, 3.6 |
| `camera.py` | 2.3, 3.3, 4.1, 4.2 |
| `router.py` | 2.4, 5.3 |
| `__init__.py` | 3.4, 4.2 |
| `base_class.py` | 3.2, 4.3 |
| `sensor.py` | 3.1 |
| `cover.py` | 3.5, 4.2, 4.3 |
| `switch.py` | 5.4 |

## Décisions architecturales

- Les phases 1 et 2 sont **séquentielles** (la 2 dépend de la validation de la 1)
- Les phases 3, 4 et 5 sont **parallélisables** entre elles
- Le code `DUMMY` (`const.py` + `router.py` JSON hardcodé) est conservé mais marqué pour suppression future
- **Aucun nouveau fichier de code** n'est créé — uniquement des modifications de fichiers existants

## Hors périmètre

Ces éléments sont recommandés mais constituent des chantiers séparés :

- **Tests unitaires** : Aucune couverture de test actuellement. À traiter dans un projet dédié.
- **Migration vers `CoordinatorEntity`** : Pattern moderne HA pour centraliser le polling. Changement architectural majeur.
- **Refactoring du polling vers push/webhook** : Remplacement de l'intervalle de polling par des notifications push de la Freebox (si l'API le supporte).
