#!/usr/bin/env python3

import argparse
import datetime as dt
import fitbit
import logging
import os
import sys
from pymongo import MongoClient
from pymongo.helpers import DuplicateKeyError

class Loader():
    """ Data loader for Fitbit into MongoDB """

    def __init__(self, verbose=None):
        """ Set up connection details """
        if not verbose:
            log_level = logging.INFO
        else:
            log_level = logging.DEBUG
        stdout_handler = logging.StreamHandler(sys.stdout)
        logging.basicConfig(
            level=log_level,
            handlers=[stdout_handler]
        )
        self.logger = logging.getLogger(name='fitbit-mongodb-loader')

        # Connect to FitBit
        key = os.environ["FITBIT_KEY"]
        secret = os.environ["FITBIT_SECRET"]
        access_token = os.environ["FITBIT_ACCESS_TOKEN"]
        refresh_token = os.environ["FITBIT_REFRESH_TOKEN"]
        self.fitbit_client = fitbit.Fitbit(
            key,
            secret,
            access_token=access_token,
            refresh_token=refresh_token
        )

        # Create MongoDB connectION
        mongodb_client = MongoClient()
        self.db = mongodb_client.fitbit

        # Empty vars -- need to be filled by child class
        self.collection_name = None
        self.document_key = None
        self.timestamp_key = None
        self.request_args = {}

    def configure_collection(self):
        """ Ensure that the collection is created and indexed """
        # Create collection if not exists
        if not self.collection_name in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)
        # Make sure unique index is created
        mongodb_index = "{}.0.{}".format(
            self.document_key,
            self.timestamp_key
        )
        collection = self.db.get_collection(self.collection_name)
        collection.create_index(mongodb_index, unique=True)

    def get_fitbit_data(self, request_args):
        """ Get FitBit data """
        return self.fitbit_client.time_series(**request_args)

    def load(self, days=None):
        """
        Load data for <days> full days into the past
        from FitBit into MongoDB
        """
        # First make sure MongoDB is set up properly
        self.configure_collection()

        if days is None or type(days) != int:
            raise TypeError("days must be an integer")
        today = dt.datetime.today()
        days_back = days
        all_dates = []
        while days_back > 0:
            date_text = dt.datetime.strftime(
                today - dt.timedelta(days=days_back),
                "%Y-%m-%d"
            )
            self.logger.debug("date_text: {}".format(date_text))
            all_dates.append(date_text)
            days_back -= 1
        self.logger.info("Preparing to load dates {}".format(all_dates))

        collection = self.db.get_collection(name=self.collection_name)

        for base_date in all_dates:
            self.request_args["base_date"] = base_date

            # Check that data doesn't already exist in MongoDB
            search_key = "{}.0.{}".format(
                self.document_key,
                self.timestamp_key
            )
            cursor = collection.find(
                {
                    search_key: base_date
                }
            )
            documents = [x for x in cursor]
            if len(documents) > 0:
                if len(documents) > 1:
                    raise RuntimeError(
                        "Duplicate entry detected, your database "
                        "is missing the uniqueness constrained index."
                    )
                # Exactly one match was found, so skip the whole loading bit
                self.logger.warning(
                    (
                        "Document already exists for this date, "
                        "skipping {}"
                    ).format(base_date)
                )
                continue

            # Get data from FitBit API
            self.logger.info("Connecting to FitBit API...")
            data_blob = self.get_fitbit_data(self.request_args)

            # Load data into MongoDB
            try:
                collection.insert_one(data_blob)
                self.logger.info(
                    "Successfully wrote record for {}".format(
                        base_date
                    )
                )
            except DuplicateKeyError:
                self.logger.warning(
                    (
                        "Entry already exists, "
                        "failed to write data for date {}"
                    ).format(
                        base_date
                    )
                )

class HeartLoader(Loader):
    """ Heart rate loader """
    def __init__(self, *args, **kwargs):
        super(HeartLoader, self).__init__(*args, **kwargs)
        self.collection_name = "heart"
        self.resource = "activities/heart"
        self.document_key = "activities-heart"
        self.timestamp_key = "dateTime"
        self.request_args = {
            "resource": self.resource,
            "detail_level": "1sec"
        }

    def get_fitbit_data(self, request_args):
        """ Override parent for heart rate """
        return self.fitbit_client.intraday_time_series(**request_args)

class SleepLoader(Loader):
    """ Sleep data loader """
    def __init__(self, *args, **kwargs):
        super(SleepLoader, self).__init__(*args, **kwargs)
        self.collection_name = "sleep"
        self.document_key = "sleep"
        self.timestamp_key = "dateOfSleep"
        self.request_args = {}

    def get_fitbit_data(self, request_args):
        """ Get sleep data """
        date = dt.datetime.strptime(
            request_args["base_date"],
            "%Y-%m-%d"
        )
        return self.fitbit_client.get_sleep(date)

def parse_args(args):
    """ Parse CLI arguments """
    parser = argparse.ArgumentParser(
        description="Load FitBit data into MongoDB"
    )
    parser.add_argument(
        '--type',
        required=True,
        choices=[
            'heart',
            'sleep',
            'steps',
            'floors',
            'distance',
            'activity',
            'calories'
        ]
    )
    parser.add_argument(
        '--days',
        type=int,
        required=True
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true'
    )
    parsed = parser.parse_args(args)
    if parsed.days < 1:
        parser.error("Minimum days is 1")
    return parsed

def main():
    parsed = parse_args(sys.argv[1:])

    if parsed.type == "heart":
        loader = HeartLoader(verbose=parsed.verbose)
    elif parsed.type == "sleep":
        loader = SleepLoader(verbose=parsed.verbose)

    loader.load(days=parsed.days)

if __name__ == "__main__":
    main()