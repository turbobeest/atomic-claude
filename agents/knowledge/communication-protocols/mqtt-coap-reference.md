# IoT Protocol Reference: MQTT & CoAP

> **Sources**:
> - https://mqtt.org/mqtt-specification/
> - https://datatracker.ietf.org/doc/rfc7252/
> - https://www.oasis-open.org/committees/mqtt/
> **Extracted**: 2025-12-21
> **Refresh**: Annually (protocol specs are stable)

## MQTT (Message Queuing Telemetry Transport)

### Protocol Overview
- **Transport**: TCP/IP (port 1883, 8883 for TLS)
- **Pattern**: Publish/Subscribe
- **Current Version**: MQTT 5.0 (2019)

### QoS Levels

| Level | Name | Guarantee | Use Case |
|-------|------|-----------|----------|
| 0 | At most once | Fire and forget | Telemetry where loss acceptable |
| 1 | At least once | Acknowledged delivery | Most IoT scenarios |
| 2 | Exactly once | Four-step handshake | Financial, critical data |

### Message Structure
```
Fixed Header (2+ bytes)
├── Message Type (4 bits): CONNECT, PUBLISH, SUBSCRIBE, etc.
├── DUP Flag (1 bit): Duplicate delivery
├── QoS Level (2 bits): 0, 1, or 2
├── Retain Flag (1 bit): Broker stores last message
└── Remaining Length (1-4 bytes): Variable length encoding

Variable Header (depends on message type)
└── Packet Identifier, Topic Name, Properties (MQTT 5)

Payload (optional)
└── Application message data
```

### MQTT 5.0 Key Features
- **Reason Codes**: Detailed error information
- **Session Expiry**: Control session lifetime
- **Topic Aliases**: Reduce bandwidth
- **User Properties**: Custom key-value metadata
- **Shared Subscriptions**: Load balancing across clients

### Security Best Practices
1. Always use TLS (port 8883)
2. Implement client certificate authentication
3. Use ACLs for topic-level authorization
4. Enable username/password authentication
5. Set appropriate session expiry intervals

---

## CoAP (Constrained Application Protocol)

### Protocol Overview
- **Transport**: UDP (port 5683, 5684 for DTLS)
- **Pattern**: Request/Response (REST-like)
- **Specification**: RFC 7252

### Message Types

| Type | Code | Description |
|------|------|-------------|
| CON | 0 | Confirmable (requires ACK) |
| NON | 1 | Non-confirmable (no ACK) |
| ACK | 2 | Acknowledgment |
| RST | 3 | Reset (error response) |

### Method Codes

| Method | Code | HTTP Equivalent |
|--------|------|-----------------|
| GET | 0.01 | GET |
| POST | 0.02 | POST |
| PUT | 0.03 | PUT |
| DELETE | 0.04 | DELETE |

### Response Codes
```
2.xx Success
├── 2.01 Created
├── 2.02 Deleted
├── 2.03 Valid
├── 2.04 Changed
└── 2.05 Content

4.xx Client Error
├── 4.00 Bad Request
├── 4.01 Unauthorized
├── 4.04 Not Found
└── 4.05 Method Not Allowed

5.xx Server Error
├── 5.00 Internal Server Error
└── 5.03 Service Unavailable
```

### Observe Extension (RFC 7641)
- Subscribe to resource changes
- Server pushes updates to client
- Uses GET with Observe option

### Block-wise Transfers (RFC 7959)
- Transfer large payloads over UDP
- Configurable block sizes (16 to 1024 bytes)
- Supports both request and response blocking

---

## MQTT vs CoAP Comparison

| Aspect | MQTT | CoAP |
|--------|------|------|
| Transport | TCP | UDP |
| Header Size | 2+ bytes | 4 bytes |
| Message Pattern | Pub/Sub | Request/Response |
| NAT Traversal | Good (persistent conn) | Challenging |
| Battery Impact | Higher (TCP keepalive) | Lower |
| Reliability | Built-in (QoS) | Application layer |
| Best For | Event streaming, telemetry | Resource-constrained devices |

## When to Use Which

**Choose MQTT when:**
- Need reliable message delivery
- Many subscribers for same data
- Persistent connections acceptable
- Event-driven architecture

**Choose CoAP when:**
- Extremely constrained devices
- Request/response pattern needed
- UDP preferred (battery/bandwidth)
- RESTful interface required

---
*This excerpt was curated for agent knowledge grounding.*
