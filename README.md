# 🚕 Taxi Trip Streaming Pipeline - AWS Architecture

This project provides a **fault‑tolerant, real‑time streaming pipeline** for taxi trip events. Built on AWS, it uses Kinesis + Lambda for event processing, DynamoDB for state storage, and SNS/SQS/Glue for error handling and recovery.

---

# Table of Contents

- [Tech Stack With AWS](#tech-stack-wiith-aws)
- [Architecture Overview](#architecture-overview)
- [Components](#components)
- [Data Source](#data-source)
- [Data Flow Summary](#data-flow-summary)
- [Sequence Diagrams](#sequence-diagrams)
  - [Start-Trip Event Flow](#1️⃣-start-trip-event-flow)
  - [End-Trip Event Flow](#2️⃣-end-trip-event-flow)
  - [Glue Replay Recovery Flow](#3️⃣-glue-replay-recovery-flow)

---

# Tech Stack With AWS
- **Kinesis** – real-time ingestion of taxi start/end events
- **Lambda** – serverless compute for validating and upserting trips  
- **DynamoDB** – low-latency store for taxi trip details 
- **SQS** – buffer for failed updates (replay queue) 
- **SNS** – notifications for invalid taxi trips 
- **Glue** – batch replay of failed events from SQS 
- **S3** – landing bucket for sample data & artifacts 
- **IAM** - resource access control 
- **CloudFormation** - keep the environment reproducible via IaC

---

# Architecture Overview

```mermaid
flowchart LR
    subgraph Ingestion Layer
        A1[Start-Trip<br/>Producers] --> KS1[Kinesis Stream<br/>start-trip-stream]
        A2[End-Trip<br/>Producers] --> KS2[Kinesis Stream<br/>end-trip-stream]
    end

    subgraph Processing Layer
        KS1 --> L1[Lambda<br/>start-taxi-trips]
        KS2 --> L2[Lambda<br/>end-taxi-trips]
    end

    subgraph Storage & State
        DDB[(DynamoDB<br/>taxi_trip_details)]
    end

    subgraph Error Handling
        SNS[(SNS Topic<br/>Invalid-taxi-trips)]
        SQS[(SQS Queue<br/>failed-updated-trips)]
    end

    subgraph Recovery Layer
        Glue[Glue Job<br/>Replay Failed Trips]
    end

    L1 -->|Valid start event| DDB
    L1 -->|Invalid event| SNS

    L2 -->|Valid end event| DDB
    L2 -->|DynamoDB Write Error| SQS

    SQS -->|Batch Read| Glue -->|Replay Updates| DDB
    Glue -->|Delete on Success| SQS
```

---

# Components

### **1. Amazon Kinesis Streams**
Two dedicated streams:
- `start-trip-stream`
- `end-trip-stream`

Consume start-trip and end-trip events independently.

### **2. AWS Lambda Functions**

#### **start-taxi-trips**
- Validates start-trip events  
- Writes initial trip record to DynamoDB  
- Sends invalid events to SNS  

#### **end-taxi-trips**
- Processes end-trip events  
- Updates DynamoDB with completion details  
- On error → sends event to SQS (`failed-updated-trips`)

### **3. Amazon DynamoDB — `taxi-trip-details`**
Persist trip states and attributes (trip_id as PK).

### **4. AWS SQS — Failed Update Buffer**
`failed-updated-trips` queue stores events that the end-trip Lambda could not write to DynamoDB.

This ensures no event is ever lost.

### **5. AWS SNS — Invalid Data Notifications**
All malformed or inconsistent start-trip events are published to:
```
SNS Topic: Invalid-taxi-trips
```
An email subscription receives alerts for inspection.

### **6. AWS Glue Job**
A Python job performing:

Batch-process SQS failures, reapply DynamoDB updates, delete SQS messages only after successful replay.

---

# Data Source
This project uses data sampled from San Francisco taxi trip datasets, published through the city’s open data platform. The dataset is modeled as a continuous stream of start‑trip and end‑trip events to simulate real‑time taxi operations. [Here describes attributes of taxi trip events](data/taxi-trip-event-attributes.md).

---

# Data Flow Summary

```
Start-trip → Kinesis → Lambda → DynamoDB
End-trip   → Kinesis → Lambda → DynamoDB (✓ success)
End-trip   → Kinesis → Lambda → SQS (✗ failure)
SQS → Glue Replay → DynamoDB (recovered)
```

---

# Sequence Diagrams

---

## 1️⃣ Start-Trip Event Flow

```mermaid
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
```


## 2️⃣ End-Trip Event Flow

```mermaid
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
```

## 3️⃣ Glue Replay Recovery Flow

```mermaid
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
```