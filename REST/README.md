# UE-AD-A1-REST

Pour la première partie ne vous souciez pas des fichiers Docker, cela sera abordé par la suite en séance 4.

## Lancement avec Docker Compose

Depuis le dossier `REST` :

```bash
docker compose up --build
```

Le fichier `.env` configure les ports exposés sur la machine hôte. Avec les valeurs par défaut, Movie répond sur le port 3200, Booking sur 3201, Schedule sur 3202 et User sur 3203. Les URL interservices utilisent les noms Docker `movie` et `schedule` et leurs ports internes.

Pour vérifier les appels interservices après le démarrage :

```bash
curl http://localhost:3202/schedule/20151201/details
curl http://localhost:3201/bookings/chris_rivers/details
```

Les fichiers JSON sont stockés dans les conteneurs. Les modifications effectuées via les API sont perdues si les conteneurs sont recréés.

## Environnement virtuel Python

Depuis le dossier `REST`, sous Linux ou WSL :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Si la création échoue parce que `ensurepip` manque, installer le paquet
correspondant à la version de Python (ici, `sudo apt install python3.14-venv`),
puis relancer les commandes ci-dessus.

Pour quitter l'environnement :

```bash
deactivate
```


