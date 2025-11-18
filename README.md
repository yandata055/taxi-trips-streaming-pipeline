🚕 Taxi Trip Streaming Pipeline — Real-Time AWS Architecture

This project implements a fault-tolerant, real-time taxi-trip event processing pipeline using AWS services.
It reliably processes start-trip and end-trip events, maintains trip state in DynamoDB, and ensures guaranteed replay of failed updates using SQS + AWS Glue.

This repository includes:

AWS CloudFormation template (infrastructure as code)

AWS Glue replay job (Python)

Architecture & sequence diagrams

End-to-end workflow documentation

📚 Table of Contents

Overview

High-Level Architecture

Components

Sequence Diagrams

Start-Trip Event Flow

End-Trip Event Flow

Glue Replay Recovery Flow

Glue Replay Job

Data Flow Summary

Repository Structure

Future Enhancements

⚡ Overview

The system ingests streaming trip events, processes them in real time with AWS Lambda, persists trip state in DynamoDB, and recovers from write failures using an AWS Glue batch job.

The pipeline guarantees:

Real-time processing of trip events

Fault tolerance with full replay support

Exactly-once–like outcomes for DynamoDB updates

Eventual consistency even under write failures

🏗️ High-Level Architecture
flowchart LR
    subgraph Ingestion Layer
        A1[Start-Trip\nProducers] --> KS1[Kinesis Stream\nstart-trip-stream]
        A2[End-Trip\nProducers] --> KS2[Kinesis Stream\nend-trip-stream]
    end

    subgraph Processing Layer
        KS1 --> L1[Lambda\nstart-taxi-trips]
        KS2 --> L2[Lambda\nend-taxi-trips]
    end

    subgraph Storage & State
        DDB[(DynamoDB\n taxi_trip_details)]
    end

    subgraph Error Handling
        SNS[(SNS Topic\nInvalid-taxi-trips)]
        SQS[(SQS Queue\nfailed-updated-trips)]
    end

    subgraph Recovery Layer
        Glue[Glue Job\nReplay Failed Trips]
    end

    %% start trip flow
    L1 -->|Valid start event| DDB
    L1 -->|Invalid event| SNS

    %% end trip flow
    L2 -->|Valid end event| DDB
    L2 -->|DynamoDB Write Error| SQS

    %% glue recovery flow
    SQS -->|Batch Read| Glue -->|Replay Updates| DDB
    Glue -->|Delete on Success| SQS

🧩 Components
1. Amazon Kinesis Streams

Two independent streams:

start-trip-stream

end-trip-stream

Provide scalable ingestion with ordered, real-time event delivery.

2. AWS Lambda Functions

start-taxi-trips

Validates start-trip events

Writes initial trip record to DynamoDB

Sends invalid data alerts to SNS

end-taxi-trips

Validates end-trip events

Writes completion data to DynamoDB

On DynamoDB write failure → sends event to the SQS retry queue

3. DynamoDB — taxi_trip_details

Holds the authoritative trip record:

trip_id (primary key)

start/end timestamps

locations

fare

trip status

4. SQS — failed-updated-trips

Buffer for events that Lambda could not write to DynamoDB.

Glue consumes this queue during recovery.

5. AWS Glue Replay Job

A Python job that:

Reads messages in batches

Idempotently replays trip updates into DynamoDB

Removes messages only after success

Ensures durable recovery and no lost end-trip events.

🧵 Sequence Diagrams
1️⃣ Start-Trip Event Flow
sequenceDiagram
    autonumber

    participant Producer as Trip Source
    participant Kinesis as start-trip-stream
    participant Lambda as start-taxi-trips Lambda
    participant DDB as DynamoDB<br>taxi_trip_details
    participant SNS as SNS Topic<br>Invalid-taxi-trips

    Producer ->> Kinesis: PutRecord(start-trip event)
    Kinesis ->> Lambda: Trigger event batch
    Lambda ->> Lambda: Validate start-trip payload

    alt Valid start-trip
        Lambda ->> DDB: PutItem / UpdateItem<br>status="STARTED"
    else Invalid event
        Lambda ->> SNS: Publish notification
    end

2️⃣ End-Trip Event Flow
sequenceDiagram
    autonumber

    participant Producer as Trip Source
    participant Kinesis as end-trip-stream
    participant Lambda as end-taxi-trips Lambda
    participant DDB as DynamoDB<br>taxi_trip_details
    participant SQS as SQS Queue<br>failed-updated-trips

    Producer ->> Kinesis: PutRecord(end-trip event)
    Kinesis ->> Lambda: Trigger event batch
    Lambda ->> Lambda: Validate end-trip event

    alt DynamoDB update succeeds
        Lambda ->> DDB: UpdateItem<br>status="ENDED", fare, timestamps
    else DynamoDB update fails
        Lambda ->> SQS: SendMessage(original event)
    end

3️⃣ Glue Replay Recovery Flow
sequenceDiagram
    autonumber

    participant Glue as Glue Job<br>replay_failed_trips()
    participant SQS as SQS Queue<br>failed-updated-trips
    participant DDB as DynamoDB<br>taxi_trip_details

    loop Until SQS empty
        Glue ->> SQS: ReceiveMessage(max 10)
        SQS -->> Glue: Messages(batch)

        alt No messages returned
            Glue ->> Glue: Exit loop<br>(Queue empty)
        end

        loop For each message
            Glue ->> Glue: Parse record JSON
            Glue ->> DDB: UpdateItem<br>(idempotent update)

            alt Update successful
                Glue ->> SQS: DeleteMessage
            else Update failed
                Glue ->> Glue: Log failure<br>(message reappears later)
            end
        end
    end

🔁 Glue Replay Job

The replay job (taxi_trip_glue_replay.py) performs:

Precision-safe JSON parsing (Decimals for DynamoDB)

Validation: ensures trip_id exists

Safely constructs DynamoDB UpdateExpression

Retries in batch until queue is empty

Deletes messages only on success

This ensures eventual consistency and zero data loss.

🔄 Data Flow Summary
Start-trip → Kinesis → Lambda → DynamoDB
End-trip   → Kinesis → Lambda → DynamoDB (success)
End-trip   → Kinesis → Lambda → SQS (on failure)
SQS → Glue Replay → DynamoDB (retry)

📁 Repository Structure
.
├── TaxiTripResourcesAWS-template.yaml     # Full AWS infrastructure stack
├── taxi_trip_glue_replay.py               # Glue replay job (batch recovery)
├── README.md                              # Project documentation
└── diagrams/                              # Optional rendered PNG/SVG outputs