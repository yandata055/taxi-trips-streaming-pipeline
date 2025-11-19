# 🚕 Taxi Trip Streaming Pipeline

This project provides a **fault‑tolerant, real‑time streaming pipeline** for taxi trip events.  
Built on **AWS**, it uses Kinesis + Lambda for event processing, DynamoDB for state storage, and SNS/SQS/Glue for error handling and recovery.

---

# Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [High-Level Architecture](#high-level-architecture)
- [Components](#components)
- [Data Flow Summary](#data-flow-summary)
- [Sequence Diagrams](#sequence-diagrams)
  - [Start-Trip Event Flow](#1️⃣-start-trip-event-flow)
  - [End-Trip Event Flow](#2️⃣-end-trip-event-flow)
  - [Glue Replay Recovery Flow](#3️⃣-glue-replay-recovery-flow)


# Features
- Real‑time ingestion of taxi trip events  
- Serverless processing with AWS Lambda  
- Reliable state management in DynamoDB  
- Robust error handling and recovery  

---

# Tech Stack
- **AWS Kinesis** – event streaming  
- **AWS Lambda** – serverless compute  
- **Amazon DynamoDB** – state storage  
- **Amazon SNS & SQS** – messaging and error handling  
- **AWS Glue** – data recovery and ETL  

---

# High-Level Architecture

```mermaid
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
```

---

# Components

### **1. Amazon Kinesis Streams**
Two dedicated streams:
- `start-trip-stream`
- `end-trip-stream`

These provide high-throughput ingestion and ordered delivery.

---

### **2. AWS Lambda Functions**

#### **start-taxi-trips**
- Validates start-trip events  
- Writes initial trip record to DynamoDB  
- Sends invalid events to SNS  

#### **end-taxi-trips**
- Processes end-trip events  
- Updates DynamoDB with completion details  
- On error → sends event to SQS (`failed-updated-trips`)

---

### **3. DynamoDB — `taxi_trip_details`**
Stores the authoritative record of every trip:

---

### **4. SQS — Failed Update Buffer**
`failed-updated-trips` queue stores events that the end-trip Lambda could not write to DynamoDB.

This ensures *no event is ever lost*.

---

### **5. AWS SNS — Invalid Data Notifications**
All malformed or inconsistent start-trip events are published to:
```
SNS Topic: Invalid-taxi-trips
```
An email subscription receives alerts for inspection.

---

### **6. AWS Glue Replay Job**
A Python job performing:

- Batch SQS reads  
- Idempotent DynamoDB updates  
- Guaranteed deletion of SQS messages only after success  

---

# Data Flow Summary

```
Start-trip → Kinesis → Lambda → DynamoDB
End-trip   → Kinesis → Lambda → DynamoDB (✓ success)
End-trip   → Kinesis → Lambda → SQS (✗ failure)
SQS → Glue Replay → DynamoDB (recovered)
```

This ensures:

- No data loss  
- Automatic recovery  
- Reliable end-to-end consistency  

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

---

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

---

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

---