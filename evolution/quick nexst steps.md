3. Async by Default

  Modern Python is async-first, and evaluation workloads are
  inherently async:

  # Current synchronous design
  class APIService:
      def handle_request(self, request: APIRequest) -> APIResponse:
          # Blocks until response ready
          return response

  # Better async-first design
  class AsyncAPIService:
      async def handle_request(self, request: APIRequest) -> 
  APIResponse:
          # Non-blocking, can handle many requests
          return response

      # Adapter for sync frameworks
      def handle_request_sync(self, request: APIRequest) -> 
  APIResponse:
          return asyncio.run(self.handle_request(request))

  Real-world benefits:

  class AsyncRESTfulAPI(AsyncAPIService):
      async def handle_evaluation(self, request: APIRequest) -> 
  APIResponse:
          # These can all run concurrently
          eval_task = self.platform.evaluate_async(code)

          # While evaluation runs, we can:
          await self.monitor.emit_event_async(eval_id, "submitted")
          await self.storage.store_metadata_async(eval_id, metadata)

          # Stream results as they come
          async for event in self.monitor.stream_events(eval_id):
              yield event  # Server-sent events

  Benefits:
  - Better resource utilization
  - Natural fit for streaming/websockets
  - Scales to more concurrent users
  - Works well with async platforms (FastAPI, aiohttp)

4. Event System (IMPLEMENTED)

  ✓ DONE in extreme_mvp_frontier_events.py using orchestration-based pattern
  
  We implemented EventBus but chose orchestration-based over component-based events:
  
  # What we built (orchestration-based):
  event_bus = EventBus()
  
  # Orchestrator handles wiring
  def handle_evaluation_completed(event):
      storage.store(event['data']['eval_id'], event['data']['result'])
  
  event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, handle_evaluation_completed)
  
  Benefits we achieved:
  - ✓ Components remain simple (no EventBus dependency)
  - ✓ Gradual migration possible
  - ✓ Event history and debugging (/events endpoint)
  - ✓ Loose coupling at orchestration layer
  - ✓ Easy to test components in isolation
  
  See /docs/EVENT_ARCHITECTURE_PATTERNS.md for detailed comparison of:
  - Orchestration-based events (what we chose)
  - Component-based events (full refactor approach)
  
  Future evolution path:
  - Current: Orchestrator handles events
  - Next: Components can optionally accept EventBus
  - Future: Full component-based if needed
  - External: Redis Pub/Sub or Kafka when scaling

  These patterns would make the system more:
  - Maintainable - Clear boundaries and contracts
  - Scalable - Async operations and loose coupling
  - Evolvable - Easy to swap implementations
  - Observable - Events provide natural monitoring points

## Future Improvements (Post-MVP)

### Real-Time Updates Enhancement
**Current**: 2-second HTTP polling (working fine for MVP)
**Future**: WebSockets or Server-Sent Events when scaling
**Trigger**: When polling load becomes issue or <1s latency needed
**Details**: See `docs/real-time-updates-evolution.md`