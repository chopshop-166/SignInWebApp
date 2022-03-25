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