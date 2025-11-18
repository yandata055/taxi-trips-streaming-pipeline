# Architecture Overview

 ┌───────────────────────────────────────────────────────────┐
 │                       CloudFormation Stack                 │
 ├───────────────────────────────────────────────────────────┤
 │ 1. Kinesis Streams                                         │
 │    - trip_start_stream                                     │
 │    - trip_end_stream                                       │
 │                                                            │
 │ 2. DynamoDB (Trips Table)                                  │
 │                                                            │
 │ 3. Lambda Functions                                        │
 │    - trip_start_lambda                                     │
 │    - trip_end_lambda                                       │
 │    - Event Source Mapping (Kinesis -> Lambda)              │
 │                                                            │
 │ 4. Glue Job                                                │
 │    - Glue Script in S3                                     │
 │    - IAM Role                                              │
 │                                                            │
 │ 5. IAM Roles & Policies                                    │
 │    - LambdaRoleStart                                       │
 │    - LambdaRoleEnd (with Glue trigger permissions)         │
 │    - GlueJobRole                                           │
 │                                                            │
 │ 6. S3 Buckets                                              │
 │    - glue scripts                                          │
 │    - output curated data                                   │
 └───────────────────────────────────────────────────────────┘
