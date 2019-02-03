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
        key = os.environ["FITBIT_KEY"]
        secret = os.environ["FITBIT_SECRET"]
        access_token = os.environ["FITBIT_ACCESS_TOKEN"]
        refresh_token = os.environ["FITBIT_REFRESH_TOKEN"]
        self.client = fitbit.Fitbit(
            key,
            secret,
            access_token=access_token,
            refresh_token=refresh_token
        )

class HeartLoader(Loader):
    """ Heart rate loader """
    def __init__(self, *args, **kwargs):
        super(HeartLoader, self).__init__(*args, **kwargs)

    def load(self, days=None):
        """
        Load data for <days> full days into the past
        from FitBit into MongoDB
        """
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

        # Create MongoDB connectION
        client = MongoClient()
        db = client.fitbit
        heart_collection = db.heart

        for base_date in all_dates:
            # Check that data doesn't already exist in MongoDB
            cursor = heart_collection.find(
                {
                    "activities-heart.0.dateTime": base_date
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
            data_blob = self.client.intraday_time_series(
                "activities/heart",
                base_date=base_date,
                detail_level="1sec"
            )
            actual_date = data_blob["activities-heart"][0]["dateTime"]

            # Load data into MongoDB
            try:
                heart_collection.insert_one(data_blob)
                self.logger.info(
                    "Successfully wrote record for {}".format(
                        actual_date
                    )
                )
            except DuplicateKeyError:
                self.logger.warning(
                    (
                        "Entry already exists, "
                        "failed to write data for date {}"
                    ).format(
                        actual_date
                    )
                )

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

    if parsed.type == 'heart':
        heart_loader = HeartLoader(verbose=parsed.verbose)
        heart_loader.load(days=parsed.days)

if __name__ == "__main__":
    main()