# UE-AD-A1-MIXTE

## Authentification

La connexion se fait auprès du service **User** et renvoie un **JWT** (HS256, valable 1 h) :

```bash
curl -X POST http://localhost:3203/login -H "Content-Type: application/json" \
     -d '{"id": "michael_scott", "password": "michael123"}'
# -> {"token": "eyJhbGciOi..."}
```

Le token est ensuite envoyé à **n'importe quel service** dans l'en-tête :

```
Authorization: Bearer <token>
```

Les 4 services vérifient le token avec le même secret (`JWT_SECRET`, défini dans le fichier `.env`, lu automatiquement par `docker compose`).
Les mots de passe sont stockés **hachés** (werkzeug, scrypt) dans `user/data/users.json`, jamais en clair.

### Comptes de test

| id | mot de passe | admin |
|---|---|---|
| michael_scott | michael123 | **oui** |
| chris_rivers | chris123 | non |
| peter_curley | peter123 | non |
| garret_heaton | garret123 | non |
| jim_halpert | jim123 | non |
| pam_beesly | pam123 | non |
| dwight_schrute | dwight123 | non |

### Droits

| Service | Public | Utilisateur concerné ou admin | Admin seulement |
|---|---|---|---|
| User | `POST /login`, `POST /users/{id}` (inscription, `admin` forcé à false) | `GET`/`DELETE /users/{id}`, `PUT /users/{id}/{last_active}`, toutes les routes `/users/{id}/bookings...` | `GET /users` |
| Booking | — | `booking_by_user`, `add_booking`, `delete_booking`, `delete_booking_movie` | `bookings` |
| Movie | toutes les queries | — | `add_movie`, `update_movie_rate`, `delete_movie` |
| Schedule | `GET /schedule`, `GET /schedule/{date}` | — | `POST`, `DELETE /schedule/{date}` |

Codes renvoyés : **401** sans token valide (absent, falsifié ou expiré), **403** si les droits sont insuffisants.
Côté GraphQL, les erreurs portent `extensions.code` = `UNAUTHENTICATED` ou `FORBIDDEN`.
