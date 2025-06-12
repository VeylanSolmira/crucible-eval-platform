# Real-Time Updates Evolution Strategy

## Current Implementation (MVP)
- **Simple HTTP Polling**: Frontend polls every 2 seconds
- **Endpoints polled**:
  - `/api/status` - Platform health
  - `/api/queue-status` - Queue statistics  
  - `/api/eval-status/{id}` - Individual evaluation status
- **Good enough for**: Development, small teams, demo purposes
- **Trade-offs**: Simple to implement, some network overhead, 2-second latency

## Why This is Fine for Now
1. **Simplicity wins**: No additional infrastructure needed
2. **Focus on core**: Better to perfect evaluation engine than optimize updates
3. **Scale appropriate**: A few developers polling won't cause issues
4. **Easy to debug**: Can see requests in browser dev tools
5. **Progressive**: Can enhance without breaking changes

## Future Evolution Path

### Stage 2: Long Polling
- **When**: 10+ concurrent users
- **How**: Hold HTTP connection open until data changes
- **Benefits**: Reduced requests, lower latency
- **Complexity**: Moderate - need connection management

### Stage 3: WebSockets
- **When**: Need bidirectional communication or <1s latency
- **How**: Already stubbed in FastAPIFrontend
- **Benefits**: Real-time updates, bidirectional
- **Complexity**: Higher - need WebSocket server, reconnection logic
- **Code location**: `components/web_frontend.py:972` (FastAPIFrontend)

### Stage 4: Server-Sent Events (SSE)
- **When**: One-way updates sufficient
- **How**: HTTP streaming from server
- **Benefits**: Simpler than WebSockets, automatic reconnection
- **Complexity**: Moderate - good middle ground

### Stage 5: Production Microservices
- **When**: Full microservices architecture
- **Options**:
  - GraphQL subscriptions
  - gRPC streaming
  - Message queue (Redis pub/sub, RabbitMQ)
- **Benefits**: Scalable, decoupled
- **Complexity**: High - requires infrastructure

## Implementation Triggers
Consider upgrading when:
- [ ] Server logs show high polling load
- [ ] Users complain about update latency
- [ ] Battery usage becomes concern (mobile)
- [ ] Bandwidth costs increase
- [ ] Need real-time collaboration features
- [ ] Scaling beyond single server

## Migration Notes
- Current polling can coexist with new methods
- Frontend config already supports websocket URL
- API responses already event-ready
- No breaking changes needed

## References
- Current polling: `components/web_frontend.py:745`
- WebSocket stub: `components/web_frontend.py:972`
- Event bus ready: `components/events.py`