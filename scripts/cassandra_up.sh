#!/usr/bin/env bash
set -euo pipefail
echo "Subindo o Cassandrinha"
until docker exec n1 cqlsh -e "describe cluster" > /dev/null 2>&1; do
  sleep 5
done
docker exec n1 cqlsh -e "CREATE KEYSPACE IF NOT EXISTS lab WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};"
docker exec n1 cqlsh -e "CREATE TABLE IF NOT EXISTS lab.kv (k text PRIMARY KEY, v blob);"
echo "KeySpace e Table do Cassandra criados!"