# UE-AD-A1-MIXTE

## Authentification

L'authentification utilise la librairie **flask-jwt-extended**.
La connexion se fait auprès du service **User** et renvoie un **JWT** (HS256, valable 1 h),
à la fois dans la réponse JSON **et** dans un cookie (`access_token_cookie`) :

```bash
curl -X POST http://localhost:3203/login -H "Content-Type: application/json" \
     -d '{"id": "michael_scott", "password": "michael123"}'
# -> {"token": "eyJhbGciOi..."}  + en-têtes Set-Cookie
```

Le token est ensuite envoyé à **n'importe quel service**, au choix :

- dans l'en-tête `Authorization: Bearer <token>` ;
- ou via le cookie reçu au login (Insomnia / le navigateur le renvoie tout seul).
  Pour les requêtes `POST`, `PUT` et `DELETE` faites **uniquement avec le cookie**, flask-jwt-extended
  exige en plus l'en-tête `X-CSRF-TOKEN` contenant la valeur du cookie `csrf_access_token` (protection CSRF).

Le token contient l'identité de l'utilisateur (`sub`) et un claim supplémentaire `admin`
(un utilisateur sans champ `admin` n'est pas administrateur).
Quand User appelle Booking, il retransmet le token reçu (en-tête ou cookie) dans l'en-tête `Authorization`.

Les 4 services vérifient le token avec le même secret (`JWT_SECRET`, défini dans le fichier `.env`, lu automatiquement par `docker compose`).
Les mots de passe sont stockés **hachés** (werkzeug, scrypt) dans la base MongoDB, jamais en clair.

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
| User | `POST /login`, `POST /users/{id}` (inscription, `admin` forcé à false) | `GET`/`DELETE /users/{id}`, `PUT /users/{id}` (corps `{"last_active": <timestamp>}`), toutes les routes `/users/{id}/bookings...` | `GET /users` |
| Booking | — | `booking_by_user`, `add_booking`, `delete_booking`, `delete_booking_movie` | `bookings` |
| Movie | toutes les queries | — | `add_movie`, `update_movie_rate`, `delete_movie` |
| Schedule | `GET /schedule`, `GET /schedule/{date}` | — | `POST`, `DELETE /schedule/{date}` |

Codes renvoyés par les routes REST (réponses par défaut de flask-jwt-extended, au format `{"msg": "..."}`) :
**401** si le token est absent ou expiré (ou si le jeton CSRF manque), **422** si le token est mal formé ou falsifié,
**403** si les droits sont insuffisants.
Côté GraphQL, les erreurs portent `extensions.code` = `UNAUTHENTICATED` ou `FORBIDDEN`.

## Base de données MongoDB (service User)

Les utilisateurs sont stockés dans **MongoDB** (librairie `pymongo`), et non plus dans un fichier JSON.
`docker compose up --build` démarre aussi deux conteneurs :

| Conteneur | Adresse | Rôle |
|---|---|---|
| `mongo` | `localhost:27017` (utilisateur `root`, mot de passe `example`) | la base |
| `mongo-express` | http://localhost:8081 | interface web pour consulter la base |

- Base `users`, collection `users`.
- Au premier démarrage, si la collection est vide, le service User y insère le contenu de
  `user/data/users.json` (`insert_many`). Ce fichier n'est ensuite plus modifié.
- Les réponses qui renvoient des utilisateurs sont sérialisées avec `bson.json_util.dumps` :
  elles contiennent le champ Mongo `_id`, au format `{"$oid": "..."}`.
- Hors Docker, le service se connecte à `mongodb://root:example@localhost:27017/` (variable `MONGO_URL`).
