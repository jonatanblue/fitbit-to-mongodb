# FitBit to MongoDB

Load FitBit data into MongoDB.

## Motivation

I wanted to get my FitBit data into a time series database, but the 150 requests/hour rate limit of the Personal Application API slowed me down. By first loading the data into MongoDB, I get a local cache that I can work off, without risking API throttling.

# How to use

## Requirements

* Python 3.6 or above
* Pip3

## Install

```
pip3 install -r requirements.txt
```


## Run

```
export FITBIT_ACCESS_TOKEN=redacted
export FITBIT_KEY=redacted
export FITBIT_REFRESH_TOKEN=redacted
export FITBIT_SECRET=redacted
./fitbit_to_mongodb.py --type heart --days 10
```

## Contribute

PRs are welcome!

## License

MIT.
