# FitBit to MongoDB

Load FitBit data into MongoDB.

## Motivation

I wanted to get my FitBit data into a time series database, but the 150 requests/hour rate limit of the Personal Application API slowed me down. By first loading the data into MongoDB, I get a local cache that I can work off, without risking API throttling.

# How to use

## Requirements

* Python 3.6 or above
* Pip3

## (Optional) Set up MongoDB database

In case you don't have a spare MongoDB cluster running somewhere already, you can use the included Docker Compose file to run a local MongoDB instance. Just make sure you protect it from unauthorized access.

```
docker-compose up -d
```

## Register with the FitBit API

### Create Application

1. Log in to [FitBit dev portal](https://dev.fitbit.com/apps/new)
1. On the **Create new app** page fill in all required fields. Set **OAuth 2.0 Application Type** to `Personal` and make sure **Callback URL** is filled in exactly like this (including trailing slash): `http://127.0.0.1:8080/`

   Select `Read-Only` for **Default Access Type** and for all other URLs just enter anything. They are required in the form, but for personal applications not actually needed or used.

1. Click Save. You can now view your application details under [Manage my apps](https://dev.fitbit.com/apps).

   Set `FITBIT_KEY` to the OAuth 2.0 Client ID and `FITBIT_SECRET` to the Client Secret in the Run step below.

## Install

Recommended: [set up virtualenv](https://packaging.python.org/guides/installing-using-pip-and-virtualenv/)

```
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
```


## Run

Set secrets as environment variables:

```
$ export FITBIT_KEY=redacted
$ export FITBIT_SECRET=redacted
$ . ./generate_access_token  # This will set the variables
                             # FITBIT_ACCESS_TOKEN and FITBIT_REFRESH_TOKEN
```

Load the past two days of data into MongoDB:

```
$ ./fitbit_to_mongodb.py --type heart --days 2
INFO:fitbit-mongodb-loader:Preparing to load dates ['2019-02-01', '2019-02-02']
INFO:fitbit-mongodb-loader:Connecting to FitBit API...
INFO:fitbit-mongodb-loader:Successfully wrote record for 2019-02-01
INFO:fitbit-mongodb-loader:Connecting to FitBit API...
INFO:fitbit-mongodb-loader:Successfully wrote record for 2019-02-02
```

Loading the same range again will not result in any requests to the FitBit API:

```
$ ./fitbit_to_mongodb.py --type heart --days 2
INFO:fitbit-mongodb-loader:Preparing to load dates ['2019-02-01', '2019-02-02']
WARNING:fitbit-mongodb-loader:Document already exists for this date, skipping 2019-02-01
WARNING:fitbit-mongodb-loader:Document already exists for this date, skipping 2019-02-02
```

## Contribute

PRs are welcome!

## License

MIT.
