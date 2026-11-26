import os

import jwt
from flask import request

# Clé secrète partagée par les 4 services pour signer / vérifier les tokens
SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-me')


def get_connected_user():
    """Lit l'en-tête 'Authorization: Bearer <token>' de la requête.
    Renvoie le contenu du token, par ex. {'sub': 'chris_rivers', 'admin': False, ...},
    ou None si le token est absent, invalide ou expiré."""
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return None
    token = header[len('Bearer '):]
    try:
        return jwt.decode(token, SECRET, algorithms=['HS256'])
    except jwt.PyJWTError:
        return None
