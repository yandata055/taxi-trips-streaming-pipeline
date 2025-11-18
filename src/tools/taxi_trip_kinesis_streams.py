#!/usr/bin/env python3
import json
import time
import random
import logging
from typing import List, Dict
import boto3
import pandas as pd
import base64
import argparse
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# Logging Configuration
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

MAX_RECORDS_PER_BATCH = 10
REGION_NAME = "us-east-1"


# ─────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────
def chunked(iterable, size):
    """Yield successive chunks from iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def df_to_kinesis_records(df: pd.DataFrame, partition_key_col: str = "trip_id") -> List[Dict]:
    """Convert a DataFrame into Kinesis PutRecords payloads."""
    records = []

    for _, row in df.iterrows():
        record = row.to_dict()

        # Handle nan values
        record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        partition_key = str(record.get(partition_key_col))

        if not partition_key:
            logger.error(f"Skipping row with missing partition key: {record}")
            continue

        records.append({
            "Data": json.dumps(record).encode("utf-8"),
            "PartitionKey": partition_key
        })

    return records


def send_batch_to_kinesis(kinesis_client, batch: List[Dict], stream_name: str) -> int:
    """Send one batch of records to Kinesis, retrying failed records once."""
    if not batch:
        logger.info(f"No records to send to {stream_name}.")
        return 0

    total_sent = 0

    try:
        response = kinesis_client.put_records(StreamName=stream_name, Records=batch)
        failed_count = response.get("FailedRecordCount", 0)
        success_count = len(batch) - failed_count

        total_sent += success_count
        logger.info(f"Sent {success_count}/{len(batch)} records to {stream_name}")

        # Retry failed records once
        if failed_count > 0:
            failed_records = []
            for record, result in zip(batch, response["Records"]):
                if "ErrorCode" in result:
                    failed_records.append(record)

            logger.warning(f"{len(failed_records)} records failed. Retrying once...")

            retry_resp = kinesis_client.put_records(
                StreamName=stream_name,
                Records=failed_records
            )
            retry_failures = retry_resp.get("FailedRecordCount", 0)
            retry_success = len(failed_records) - retry_failures

            total_sent += retry_success
            logger.info(f"Retry result: {retry_success}/{len(failed_records)} succeeded")

            if retry_failures > 0:
                logger.error(f"{retry_failures} records still failed after retry.")

    except Exception as e:
        logger.error(f"Error sending records to {stream_name}: {str(e)}", exc_info=True)

    return total_sent


# ─────────────────────────────────────────────────────────────
# Main Logic
# ─────────────────────────────────────────────────────────────
def main():

    logger.info("Loading trip start parquet")
    start_df = pd.read_parquet("data/start_taxi_trips.parquet")

    logger.info("Loading trip end parquet")
    end_df = pd.read_parquet("data/end_taxi_trips.parquet")
    print(end_df['trip_id'].to_list()[:15])

    start_records = df_to_kinesis_records(start_df)
    end_records = df_to_kinesis_records(end_df)
    print(end_records[0:1])

    
    logger.info("Initializing Kinesis client...")
    kinesis_client = boto3.client("kinesis", region_name=REGION_NAME)
    kinesis_start_trip_stream = 'start-trip-stream'
    kinesis_end_trip_stream = 'end-trip-stream'
    

    count_batch = 0
    idx_batch = 0
    # Stream events
    for start_batch in chunked(start_records, MAX_RECORDS_PER_BATCH):
        count_batch += 1

        logger.info("Sending start strip batch...")
        sent_start_trip_count = send_batch_to_kinesis(kinesis_client, start_batch, kinesis_start_trip_stream)
        logger.info(f"Sent {sent_start_trip_count} start strips in this batch.| {datetime.utcnow().isoformat()}")

        time.sleep(random.uniform(1, 2))

        logger.info(f"Sending end trip batch...")
        end_batch = end_records[idx_batch:idx_batch + MAX_RECORDS_PER_BATCH]

        sent_end_trip_count = send_batch_to_kinesis(kinesis_client, end_batch, kinesis_end_trip_stream)
        logger.info(f"Sent {sent_end_trip_count} end strips in this batch.| {datetime.utcnow().isoformat()}")

        idx_batch += MAX_RECORDS_PER_BATCH

        logger.info("Completed batch cycle. Waiting before next batch...")
        time.sleep(3)


    logger.info("Kinesis event simulation completed.")



if __name__ == "__main__":
    main()
