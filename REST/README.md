# UE-AD-A1-REST

Pour la première partie ne vous souciez pas des fichiers Docker, cela sera abordé par la suite en séance 4.

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


