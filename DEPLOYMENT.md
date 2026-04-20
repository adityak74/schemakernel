# Deployment Guide

This document describes how to deploy SchemaKernel in production environments using Docker and Kubernetes (Helm).

## Docker

SchemaKernel provides a multi-stage Dockerfile optimized for production.

### Building the Image

```bash
docker build -t schemakernel:latest .
```

### Running the Container

The container requires API keys for the LLM providers you intend to use.

```bash
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=your_key \
  -e APP_PORT=8080 \
  schemakernel:latest
```

## Kubernetes (Helm)

A Helm chart is provided in `deployment/helm/schemakernel`.

### Prerequisites

- Helm v3+
- A Kubernetes cluster
- API keys for LLM providers

### Installation

```bash
helm install my-schemakernel ./deployment/helm/schemakernel \
  --set env.ANTHROPIC_API_KEY=your_key
```

### Configuration

You can customize the deployment by creating a `my-values.yaml` file.

#### Example `my-values.yaml`

```yaml
replicaCount: 3

image:
  repository: my-registry/schemakernel
  tag: "1.0.0"

service:
  type: LoadBalancer
  port: 80

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

env:
  ANTHROPIC_API_KEY: "sk-ant-..."
  DATABASE_URL: "postgresql://user:pass@postgres-host:5432/schemakernel"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
  PRESIDIO_ENTITIES: "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,LOCATION"
  APP_PORT: "8080"
```

Apply the configuration:

```bash
helm upgrade --install my-schemakernel ./deployment/helm/schemakernel -f my-values.yaml
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | (Required if using Anthropic) |
| `OPENAI_API_KEY` | API key for OpenAI | (Required if using OpenAI) |
| `DATABASE_URL` | SQLAlchemy connection string for SQL storage | None |
| `DYNAMODB_TABLE` | DynamoDB table name for session storage | None |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint for telemetry | None |
| `PRESIDIO_ENTITIES` | Comma-separated list of entities for PII redaction | `PERSON,EMAIL_ADDRESS` |
| `APP_PORT` | Port the application listens on | `8080` |

## Security Best Practices

1. **Non-Root User**: The Docker image is configured to run as a non-root user (UID 1000).
2. **Secrets Management**: Do not pass API keys in plain text. Use Kubernetes Secrets and reference them in your deployment or use a secrets provider like HashiCorp Vault.
3. **Network Policies**: If deploying to Kubernetes, implement Network Policies to restrict traffic to the SchemaKernel pods.
4. **Minimal Image**: We use `python:3.11-slim` as the base image to minimize the attack surface.
