# Project Configuration Baseline - v0.100

This document records the project's technical decisions for iteration tracking.

## Confirmed Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Frontend | React + TypeScript (Vite) | Modern, type-safe, fast HMR |
| Gateway | Golang (chi router) | High performance, WebSocket/SSE support |
| GameServer | Python + grpcio | AI/LLM ecosystem, pure internal gRPC |
| Frontend ↔ Gateway | WebSocket + SSE | Bidirectional + streaming |
| Gateway ↔ GameServer | gRPC (server streaming) | Type-safe, streaming, multi-language |
| Database | PostgreSQL + Redis | Relational + cache (future) |
| Container | Docker Compose | Local orchestration |
| Python PM | uv | Fast, lockfile, modern |
| Observability | Deferred | Interfaces reserved |
| LLM Default | DeepSeek (deepseek-chat) | OpenAI-compatible API |

## DeepSeek API

- Base URL: `https://api.deepseek.com`
- Models: `deepseek-chat`, `deepseek-reasoner`
- Auth: `Authorization: Bearer ${DEEPSEEK_API_KEY}`
- Endpoint: `/chat/completions` (OpenAI compatible)
- Streaming: `"stream": true`

## Design Patterns

- **Strategy Pattern**: LLM providers (OpenAI/Anthropic/DeepSeek)
- **Factory Pattern**: LLMProviderFactory for provider creation
- **Configuration-driven**: All settings from YAML + env vars

## Security

- All secrets in `.env` (gitignored)
- Environment variable references in config (`${DEEPSEEK_API_KEY}`)
- Input validation at all boundaries
- gRPC parameter boundary checks
- Gateway rate limiting

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v0.100 | 2026-04-06 | Initial project skeleton, architecture decisions |
