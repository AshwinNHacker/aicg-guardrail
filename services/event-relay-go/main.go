// AICG event relay
//
// The orchestration glue between the three Python services: listens on
// Kafka for pipeline events (dataset attested, poisoning detected,
// unlearning request completed), and writes every one to the Postgres
// compliance audit log — the durable record an auditor actually reviews,
// separate from whatever's in each service's own transient state.
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"log"
	"os"
	"time"

	_ "github.com/lib/pq"
	"github.com/segmentio/kafka-go"
)

type PipelineEvent struct {
	EventType string          `json:"event_type"` // "attested", "poisoning_detected", "unlearning_completed"
	DatasetID string          `json:"dataset_id,omitempty"`
	RequestID string          `json:"request_id,omitempty"`
	Detail    json.RawMessage `json:"detail"`
	Timestamp time.Time       `json:"timestamp"`
}

func writeAuditLog(db *sql.DB, evt PipelineEvent) error {
	_, err := db.Exec(
		`INSERT INTO audit_log (event_type, dataset_id, request_id, detail, occurred_at)
		 VALUES ($1, $2, $3, $4, $5)`,
		evt.EventType, evt.DatasetID, evt.RequestID, evt.Detail, evt.Timestamp,
	)
	return err
}

func consumeLoop(db *sql.DB, brokers, topic, groupID string) {
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{brokers},
		Topic:   topic,
		GroupID: groupID,
	})
	defer reader.Close()

	for {
		msg, err := reader.ReadMessage(context.Background())
		if err != nil {
			log.Printf("kafka read error: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		var evt PipelineEvent
		if err := json.Unmarshal(msg.Value, &evt); err != nil {
			log.Printf("failed to parse event: %v", err)
			continue
		}
		if evt.Timestamp.IsZero() {
			evt.Timestamp = time.Now().UTC()
		}

		if err := writeAuditLog(db, evt); err != nil {
			log.Printf("failed to write audit log for event %s: %v", evt.EventType, err)
			continue
		}
		log.Printf("audit log: %s dataset=%s request=%s", evt.EventType, evt.DatasetID, evt.RequestID)
	}
}

func main() {
	brokers := getenv("KAFKA_BROKERS", "kafka:9092")
	topic := getenv("KAFKA_TOPIC", "aicg-pipeline-events")
	dsn := getenv("POSTGRES_DSN", "postgres://aicg:aicg@postgres:5432/aicg?sslmode=disable")

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}
	defer db.Close()

	log.Printf("event-relay consuming %s from %s, writing audit log to postgres", topic, brokers)
	consumeLoop(db, brokers, topic, "aicg-event-relay")
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
