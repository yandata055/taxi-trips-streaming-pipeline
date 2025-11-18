# Real-Time Taxi Trips Streaming Pipeline (AWS Data Engineering Project)

**Tech:** AWS Kinesis · Lambda · DynamoDB · Glue · S3 · SNS · SQS · CloudFormation · Python 3.10 · Pandas

This project builds a **real-time streaming pipeline** around San Francisco’s official **Taxi Trips** open dataset. It ingests trip events, validates them, updates a DynamoDB table in near real time, and replays failures via an AWS Glue job.

I use this repository as a **portfolio project for data engineering interviews**.  
It’s designed so that a hiring manager can quickly understand:

- **What problem I solved**
- **Which AWS services and data engineering skills I used**
- **How I think about reliability, data quality, and scalability**

---

## 1. Problem & Dataset

San Francisco publishes detailed records of taxi trips, including pickup location, dropoff, and fare information, through the DataSF portal. The data is transmitted in real time from taxi companies to SFMTA’s Taxi API, and the dataset is updated regularly. :contentReference[oaicite:0]{index=0}  

The goal of this project is to **treat these trip events as a real-time stream**, and:

- Ingest start and end events for taxi trips
- Perform basic validation and enrichment
- Persist a **single source of truth** for trip details
- Route invalid or failed events to **alerting and replay** mechanisms

Use cases for this kind of pipeline include:

- Monitoring taxi activity across the city
- Analyzing the impact of pricing pilots on driver income
- Powering dashboards that show trip counts, average fares, and trip distances in near real time :contentReference[oaicite:1]{index=1}  

---

## 2. High-Level Architecture

At a glance:

- **Data source** – SF Taxi Trips open data (streamed as events)
- **Ingestion** – Python producer that sends events to **two Kinesis streams** (start vs end trips)
- **Processing** – Two **AWS Lambda** functions that validate and write to **DynamoDB**
- **Reliability** – Invalid records go to **SNS**, failed writes go to **SQS**
- **Replay** – An **AWS Glue** job reads from SQS and retries failed updates
- **Infrastructure-as-Code** – Everything provisioned via **CloudFormation**

The `infra/TaxiTripResourcesAWS-template.yaml` template provisions:

- S3 bucket for project data
- Two Kinesis streams (`start-trip-stream`, `end-trip-stream`)
- Two Lambda functions (`start-taxi-trips`, `end-taxi-trips`)
- DynamoDB table `taxi_trip_details`
- SQS queue `failed-updated-trips`
- SNS topic `Invalid-taxi-trips`
- IAM role and policies for the Lambdas :contentReference[oaicite:2]{index=2}  

---

## 3. Architecture Diagram

You can place this in `docs/architecture.md` and/or embed it in this README.  
GitHub renders Mermaid diagrams natively:

```mermaid
flowchart LR
    subgraph Source
        A[SF Taxi Trips Dataset<br/>(DataSF)]
        B[Sample Parquet Files<br/>start/end_taxi_trips]
    end

    B --> C[Producer Script<br/>taxi_trip_kinesis_streams.py]

    subgraph Streaming
        C --> D[(Kinesis<br/>start-trip-stream)]
        C --> E[(Kinesis<br/>end-trip-stream)]
    end

    subgraph Processing
        D --> F[Lambda<br/>start-taxi-trips]
        E --> G[Lambda<br/>end-taxi-trips]
    end

    subgraph Storage
        F --> H[(DynamoDB<br/>taxi_trip_details)]
        G --> H
    end

    F --> I[(SNS<br/>Invalid-taxi-trips)]
    G --> J[(SQS<br/>failed-updated-trips)]

    subgraph Replay
        J --> K[AWS Glue Job<br/>process-failed-trips<br/>taxi_trip_glue_replay.py]
        K --> H
    end
