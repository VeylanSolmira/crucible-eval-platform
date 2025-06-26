# API Routes

This folder is reserved for route definitions when the API grows.

## Future Structure

```
routes/
├── evaluation.py    # Evaluation endpoints
├── monitoring.py    # Monitoring/metrics endpoints
├── admin.py        # Admin endpoints
└── health.py       # Health check endpoints
```

## Example Route Module

```python
from typing import List
from ..api import APIHandler, APIRequest, APIResponse

class EvaluationRoutes:
    def __init__(self, handler: APIHandler):
        self.handler = handler
    
    def get_routes(self) -> List[tuple]:
        return [
            ('POST', '/evaluate', self.handle_evaluate),
            ('GET', '/evaluate/{eval_id}', self.get_evaluation),
            ('GET', '/evaluations', self.list_evaluations),
        ]
    
    async def handle_evaluate(self, request: APIRequest) -> APIResponse:
        return await self.handler.handle_request(request)
```

Currently, all routes are defined in the main api.py file.
