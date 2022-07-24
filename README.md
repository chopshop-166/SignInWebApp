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
A separate docker-compose file has been provided to deploy the project running under gunicorn, with nginx as a TLS terminating reverse proxy. It will also run certbot to renew TLS certificates from Let's Encrypt automatically.

We are currently running this on a E2-Micro instance in GCP as Google provides one instance for free. The instance was based on the default Debian 11 image and had docker manually installed as this provides the most flexibility.

You'll need to boot strap the certificates when using this docker-compose file as nginx won't start without some form of certificate to load. This can be done with the [init-letsencrypt.sh](https://github.com/wmnnd/nginx-certbot/blob/master/init-letsencrypt.sh). Or the steps in this script can be run manually to have more control over the process.

From there it's a simple matter of running docker compose. The compose file has restart set to always so the containers should be started automatically if they crash or the system reboots.
```sh
# Initialize the database
docker-compose run chopshop_signin ./init-db
# Start the containers
docker compose up -d
```