# Event bus — Kafka (Redpanda locally)

Local dev runs [Redpanda](https://redpanda.com) — Kafka-API-compatible,
single binary, no Zookeeper. Production runs real Kafka/MSK/Confluent;
nothing in the application code changes.

## Topic

| Topic | Producers | Consumer | Purpose |
|---|---|---|---|
| `aicg-pipeline-events` | attestation-gateway, poisoning-detector, unlearning-controller | event-relay (Go) | Every pipeline event, written to the Postgres audit log |

## Event shape

```json
{
  "event_type": "attested",
  "dataset_id": "training-batch-42",
  "detail": { "root_hash": "...", "chunk_count": 4 },
  "timestamp": "2026-07-17T10:00:00Z"
}
```

`event_type` is one of: `attested`, `poisoning_detected`, `unlearning_completed`.

## Local topic creation

```bash
docker exec -it aicg-kafka rpk topic create aicg-pipeline-events
```
