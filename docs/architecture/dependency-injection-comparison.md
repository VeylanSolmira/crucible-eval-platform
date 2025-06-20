# Dependency Injection Architecture Comparison

## Current Architecture (Global State)

```mermaid
graph TD
    %% Current problematic approach
    subgraph "Current: Global State Pattern"
        A[app.py startup] -->|creates| B[APIService instance]
        A -->|imports| C[routes.py module]
        
        B -->|calls set_api_service| D[Global api_service variable]
        
        E[FastAPI app] -->|registers| C
        
        F[HTTP Request] --> G[Route Handler]
        G -->|checks if exists| D
        G -->|uses| H[api_service.evaluate_code]
        
        style D fill:#ffcccc,stroke:#ff6666,stroke-width:3px
        style B fill:#ffffcc,stroke:#333,stroke-width:1px
    end
    
    %% Problems annotated
    D -.->|"❌ Hidden dependency"| I[Testing is hard]
    D -.->|"❌ Must initialize in order"| J[Runtime errors possible]
    D -.->|"❌ Global mutable state"| K[Thread safety concerns]
```

### Current Code Flow:
```python
# 1. app.py creates service
api_service = create_api_service(platform)

# 2. routes.py has global
api_service: Optional[APIService] = None

# 3. app.py must remember to call
set_api_service(api_service)

# 4. Routes use global directly
if not api_service:
    raise HTTPException(503, "Not initialized")
api_service.evaluate_code(code)
```

## Preferred Architecture (Dependency Injection)

```mermaid
graph TD
    %% Preferred dependency injection approach
    subgraph "Preferred: Dependency Injection Pattern"
        A2[app.py startup] -->|creates| B2[APIService instance]
        A2 -->|stores in| C2[app.state.api_service]
        
        D2[HTTP Request] --> E2[FastAPI DI System]
        E2 -->|calls| F2[get_api_service dependency]
        F2 -->|retrieves from| C2
        F2 -->|injects into| G2[Route Handler]
        G2 -->|uses| H2[api.evaluate_code]
        
        style C2 fill:#ccffcc,stroke:#66ff66,stroke-width:3px
        style E2 fill:#ccccff,stroke:#6666ff,stroke-width:2px
        style F2 fill:#ffffcc,stroke:#333,stroke-width:1px
    end
    
    %% Benefits annotated
    C2 -.->|"✅ Explicit dependencies"| I2[Easy testing with mocks]
    E2 -.->|"✅ Automatic injection"| J2[No initialization errors]
    F2 -.->|"✅ Request-scoped"| K2[Thread safe by design]
```

### Preferred Code Flow:
```python
# 1. app.py stores in app state
app = FastAPI()
app.state.api_service = create_api_service(platform)

# 2. Dependency function
async def get_api_service(request: Request) -> APIService:
    return request.app.state.api_service

# 3. Routes declare dependencies
async def create_evaluation(
    request: EvaluationCreate,
    api: APIService = Depends(get_api_service),  # ✅ Explicit!
    db: AsyncSession = Depends(get_db)          # ✅ Consistent!
):
    result = await api.evaluate_code(request.code)
```

## Key Differences

| Aspect | Current (Global) | Preferred (DI) |
|--------|-----------------|----------------|
| **Dependencies** | Hidden in function body | Explicit in function signature |
| **Testing** | Must patch global | Pass mock as parameter |
| **Initialization** | Manual, order-dependent | Automatic by framework |
| **Error Handling** | Runtime check for None | Framework ensures it exists |
| **Code Clarity** | `if not api_service:` checks | Clean business logic |
| **Scalability** | Single global instance | Can be per-request if needed |

## Testing Example

### Current (Difficult):
```python
# Must patch the global
def test_create_evaluation():
    with patch('api.routes.api_service') as mock_api:
        mock_api.evaluate_code.return_value = {...}
        # Test code
```

### Preferred (Easy):
```python
# Just pass a mock
def test_create_evaluation():
    mock_api = Mock()
    mock_api.evaluate_code.return_value = {...}
    
    # Directly call with mock
    result = await create_evaluation(
        request=EvaluationCreate(code="test"),
        api=mock_api,  # ✅ Direct injection!
        db=mock_db
    )
```

## Migration Path

To move from current to preferred:

1. **Add app.state storage**:
   ```python
   # In app.py or server startup
   app.state.api_service = api_service
   ```

2. **Create dependency function**:
   ```python
   def get_api_service(request: Request) -> APIService:
       return request.app.state.api_service
   ```

3. **Update routes one by one**:
   ```python
   # Change from hidden global to explicit parameter
   api: APIService = Depends(get_api_service)
   ```

4. **Remove global and setter**:
   ```python
   # Delete these lines
   # api_service: Optional[APIService] = None
   # def set_api_service(service: APIService): ...
   ```

This makes the code more maintainable, testable, and follows FastAPI best practices!