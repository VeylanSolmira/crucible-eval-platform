# Real-Time Updates: Technology Comparison

## Overview
When building systems that need to push updates to web clients, there are several approaches. This document compares the main options for the METR evaluation platform's monitoring needs.

## Technology Options

### 1. WebSocket
**What it is**: A protocol providing full-duplex communication channels over a single TCP connection.

**How it works**:
```
1. Client initiates HTTP request with "Upgrade: websocket" header
2. Server responds with HTTP 101 Switching Protocols
3. Connection upgrades from HTTP to WebSocket protocol
4. Both sides can send messages at any time
```

**Pros**:
- True bidirectional communication
- Low latency (no HTTP overhead after handshake)
- Well-supported in browsers and servers
- Can send binary data efficiently

**Cons**:
- More complex to implement than alternatives
- Requires special handling for proxies/load balancers
- Stateful connections (harder to scale horizontally)
- Overkill if you only need server→client updates

**When to use**: Chat apps, collaborative editing, multiplayer games, trading platforms

**Example use case for METR**: 
- Real-time log streaming from evaluations
- Interactive debugging sessions
- Two-way communication with running evaluations

### 2. Server-Sent Events (SSE)
**What it is**: A standard allowing servers to push data to web clients over HTTP.

**How it works**:
```
1. Client opens HTTP connection with Accept: text/event-stream
2. Server keeps connection open
3. Server sends events as text: "data: {json}\n\n"
4. Client receives events via EventSource API
```

**Pros**:
- Simpler than WebSocket
- Works over standard HTTP (firewall friendly)
- Automatic reconnection built-in
- Can work with HTTP/2 multiplexing

**Cons**:
- Unidirectional (server to client only)
- Text-only (binary requires encoding)
- Limited browser connections (6 per domain)
- Some proxies may timeout long connections

**When to use**: Live feeds, notifications, progress updates, dashboards

**Example use case for METR**:
- Status updates for evaluation progress
- Safety alerts and notifications
- Queue position updates

### 3. Long Polling
**What it is**: Client polls server, but server holds request open until data is available.

**How it works**:
```
1. Client sends HTTP request
2. Server holds request open (doesn't respond immediately)
3. When data available, server sends response
4. Client immediately sends new request
```

**Pros**:
- Works everywhere (just HTTP)
- Simple to implement
- No special infrastructure needed
- Good fallback option

**Cons**:
- Higher latency than WebSocket/SSE
- More resource intensive (connection churn)
- Complexity in handling timeouts
- Not truly real-time

**When to use**: Fallback for older browsers, simple notification systems

**Example use case for METR**:
- Fallback when WebSocket/SSE unavailable
- Simple status checking
- Low-frequency updates

### 4. Webhooks + Client Storage
**What it is**: Server calls client-provided endpoints when events occur.

**How it works**:
```
1. Client registers webhook URL with server
2. On event, server makes HTTP request to webhook
3. Client webhook updates local state
4. Web frontend reads from local state
```

**Pros**:
- Reliable delivery (can retry)
- Works at scale
- Client controls reception rate
- Good for integration with external systems

**Cons**:
- Client needs public endpoint
- Not real-time for web browsers
- Additional infrastructure complexity
- Security considerations (validating callbacks)

**When to use**: B2B integrations, mobile push notifications, email triggers

**Example use case for METR**:
- Sending results to external systems
- Triggering CI/CD pipelines on completion
- Integration with Slack/email notifications

### 5. GraphQL Subscriptions
**What it is**: Real-time updates using GraphQL's subscription type.

**How it works**:
```
1. Client subscribes to specific events via GraphQL
2. Usually implemented over WebSocket
3. Server pushes updates matching subscription
4. Built-in filtering and field selection
```

**Pros**:
- Integrated with GraphQL schema
- Client specifies exactly what data they want
- Type safety
- Good tooling support

**Cons**:
- Requires GraphQL setup
- Usually needs WebSocket underneath
- More complex than REST approaches
- Learning curve for teams

**When to use**: When already using GraphQL, complex subscription requirements

## Comparison Matrix

| Feature | WebSocket | SSE | Long Polling | Webhooks | GraphQL Sub |
|---------|-----------|-----|--------------|----------|-------------|
| Direction | Bidirectional | Server→Client | Server→Client | Server→Server | Bidirectional |
| Protocol | WS/WSS | HTTP | HTTP | HTTP | Usually WS |
| Complexity | High | Low | Medium | High | High |
| Browser Support | Excellent | Good | Universal | N/A | Good |
| Reconnection | Manual | Automatic | Manual | N/A | Depends |
| Firewall Friendly | Sometimes | Yes | Yes | Yes | Sometimes |
| Scalability | Hard | Medium | Easy | Easy | Hard |
| Use Case Fit | ★★★☆☆ | ★★★★★ | ★★☆☆☆ | ★★★☆☆ | ★★☆☆☆ |

## Recommendation for METR

For the METR evaluation platform, **Server-Sent Events (SSE)** appears to be the best fit:

1. **Monitoring is primarily server→client** (status updates, logs, alerts)
2. **Simpler to implement** than WebSocket
3. **Built-in reconnection** for reliability
4. **Works with existing HTTP infrastructure**
5. **Good browser support** for research users

WebSocket would be the choice if you need:
- Users to send commands to running evaluations
- Interactive debugging features
- Binary data streaming (e.g., live model outputs)

## Implementation Considerations

### For SSE:
```javascript
// Client
const events = new EventSource('/api/evaluations/123/events');
events.onmessage = (event) => {
  const update = JSON.parse(event.data);
  updateUI(update);
};

// Server (Python/FastAPI)
async def evaluation_events(eval_id: str):
    async def generate():
        while True:
            update = await get_next_update(eval_id)
            yield f"data: {json.dumps(update)}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### For WebSocket:
```javascript
// Client
const ws = new WebSocket('ws://localhost/ws/evaluations/123');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  updateUI(update);
};

// Server (Python/FastAPI)
@app.websocket("/ws/evaluations/{eval_id}")
async def websocket_endpoint(websocket: WebSocket, eval_id: str):
    await websocket.accept()
    while True:
        update = await get_next_update(eval_id)
        await websocket.send_json(update)
```

## Architecture Integration

At Level 3 (workflow), specify "real-time updates" without implementation details.
At Level 4 (tools), evaluate these options based on:
- Team expertise
- Infrastructure constraints  
- Specific feature requirements
- Scalability needs

At Level 5+ (implementation), commit to specific technology and patterns.

## When to Choose WebSocket over SSE + REST

### Heuristic: Switch to WebSocket when you have:

1. **Frequency threshold**: Client→Server messages > 1 per minute sustained
   - Example: User actively debugging, sending commands rapidly
   - REST overhead becomes noticeable

2. **Latency sensitivity**: Round-trip time matters (<100ms)
   - Example: Interactive model steering during evaluation
   - REST connection setup adds 20-50ms

3. **Message correlation**: Responses directly tied to requests
   - Example: "Set parameter X" → "Parameter X confirmed"
   - Easier to track in single connection

4. **Binary data**: Need efficient binary transfer
   - Example: Streaming model outputs, tensor data
   - SSE is text-only, REST has encoding overhead

5. **True interactivity**: Back-and-forth conversation
   - Example: Interactive debugging session, REPL-like experience

### The "3 REST calls" Rule
If a typical user session involves **3+ REST calls in quick succession**, consider WebSocket.

### Real-World Examples

**WebSocket Appropriate:**
- **Cursor IDE**: Every keystroke potentially triggers communication
- **Claude/ChatGPT Web**: Continuous conversation, interruptible responses
- **Collaborative Editing**: Google Docs, Figma
- **Trading Platforms**: Bidirectional order flow

**SSE + REST Appropriate:**
- **Monitoring Dashboards**: Mostly server→client updates
- **CI/CD Pipelines**: Status updates with occasional cancellation
- **News Feeds**: One-way content flow
- **METR Platform**: Monitoring with rare interventions

## Handling Objects and Binary Data with SSE

### Option 1: JSON over SSE (Recommended for <100KB)
```javascript
// Server sends JSON as text
event.data = JSON.stringify({
  type: "evaluation_complete",
  resultId: "abc123",
  summary: { score: 0.95, passed: true },
  artifactsUrl: "/api/results/abc123/artifacts"
});

// Client parses it
const update = JSON.parse(event.data);
```

### Option 2: SSE Notification + REST Fetch (Recommended for >1MB)
```javascript
// SSE sends minimal notification
event.data = JSON.stringify({
  type: "large_artifact_ready",
  artifactId: "xyz789"
});

// Client fetches full data
const response = await fetch(`/api/artifacts/${artifactId}`);
const artifact = await response.json();
```

### Option 3: Hybrid Approach (Best of Both)
```javascript
// SSE includes preview + fetch URL
event.data = JSON.stringify({
  type: "results_ready",
  preview: { score: 0.95, status: "complete" },  // Small subset
  fullResultsUrl: "/api/results/abc123"          // Full data if needed
});
```

### Binary Data Encoding

While possible to encode binary as text (Base64), consider the trade-offs:

**When Base64 makes sense:**
- Small images (<500KB): thumbnails, charts, icons
- Data URIs needed: inline images in reports
- Avoiding round trips: critical for UX

**When to use REST instead:**
- Large files (>1MB): 33% Base64 overhead adds up
- Streaming media: video, audio need proper protocols
- Memory concerns: encoding/decoding large data

**Example:**
```javascript
// Good: Small safety icon inline
event.data = JSON.stringify({
  type: "safety_alert",
  icon: "data:image/svg+xml;base64,..." // 2KB SVG
});

// Better: Large logs via URL
event.data = JSON.stringify({
  type: "logs_ready",
  logsUrl: "/api/evaluations/123/logs" // 50MB text file
});
```

## METR-Specific Recommendations

For METR's evaluation platform:
1. **Use SSE for all monitoring** (status, logs, metrics, alerts)
2. **Use REST for commands** (start, stop, modify evaluations)
3. **Send small objects (<100KB) directly in SSE as JSON**
4. **Send URLs for large artifacts via SSE, fetch with REST**
5. **Consider WebSocket only if adding:**
   - Interactive debugging features
   - Real-time parameter tuning
   - Collaborative monitoring sessions

## Further Reading
- [MDN: WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [MDN: Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [WebSocket vs SSE](https://ably.com/topic/websockets-vs-sse)
- [Real-time Web Technologies Guide](https://www.pubnub.com/guides/real-time-web-technologies/)