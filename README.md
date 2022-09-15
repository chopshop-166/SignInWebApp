# ChopshopSignin

A tool to track your team's hours during the season, using barcodes or QR codes that can be quickly scanned as team members come and go.

It runs on a server using Docker or Python+Flask.

## Initialization

Make sure Docker is installed and you're connected to the internet.

Create a file called `.env` in this folder with the contents:

```
FLASK_SECRET_KEY=1234
```

Replace the key with a secret value.
It will be ignored via the `.gitignore` file, so no need to worry about not checking it in.

Remaining configuration is done via `appdata/cssignin.yaml`.
Copy the `appdata/cssignin.defaults.yaml` file to that name, then customize any variables found in it.

Then, run the following commands:

```sh
# Stop the running instance if one exists
docker-compose down
# Build the image/replace the image if one already exists
docker-compose build
# Initialize the database with the default settings
docker-compose run chopshop_signin ./init-db
# Start the docker container
docker-compose up -d
```

By default the admin credentials are `admin` and `1234`.
It's highly recommended that you change the password by logging in and using the `User>Change Password` or `Admin>Users` menu.

In addition, the `display` user has the same password that should be changed.
This user is intended to be used on a persistent display, for example in the workshop.

## Updating
Run the following commands:

```sh
# Stop the running instance if one exists
docker-compose down
# Update the repository
git pull
# Build the image/replace the image if one already exists
docker-compose build
# Start the docker container
docker-compose up -d
```

## Deployment with TLS
A separate docker-compose file has been provided to deploy the project running under gunicorn, with Caddy2 as a TLS terminating reverse proxy.

We are currently running this on a E2-Micro instance in GCP as Google provides one instance for free. The instance was based on the default Debian 11 image and had docker manually installed as this provides the most flexibility.

It's a simple matter of running docker compose. The compose file has restart set to always so the containers should be started automatically if they crash or the system reboots.

```sh
# Initialize the database
docker-compose run chopshop_signin ./init-db
# Start the containers
docker compose up -d
```