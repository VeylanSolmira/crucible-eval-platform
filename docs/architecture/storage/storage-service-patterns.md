# Storage Service Design Patterns

This document explains the design patterns planned for the storage service implementation.

## 1. Repository Pattern

The Repository pattern provides an abstraction layer between the domain logic and data access logic.

### Purpose
- Hide the details of data access from the business logic
- Make the code more testable by allowing mock implementations
- Centralize query logic
- Enable switching between different storage backends

### Example Implementation

```python
# Base repository interface
class IEvaluationRepository(ABC):
    @abstractmethod
    async def find_by_id(self, eval_id: str) -> Optional[Evaluation]:
        pass
    
    @abstractmethod
    async def save(self, evaluation: Evaluation) -> Evaluation:
        pass
    
    @abstractmethod
    async def find_all(self, filter: QueryFilter) -> List[Evaluation]:
        pass

# Concrete implementation for PostgreSQL
class PostgresEvaluationRepository(IEvaluationRepository):
    def __init__(self, db_session: AsyncSession):
        self.session = db_session
    
    async def find_by_id(self, eval_id: str) -> Optional[Evaluation]:
        result = await self.session.execute(
            select(EvaluationModel).where(EvaluationModel.id == eval_id)
        )
        return result.scalar_one_or_none()
    
    async def save(self, evaluation: Evaluation) -> Evaluation:
        self.session.add(evaluation)
        await self.session.commit()
        return evaluation

# Another implementation for MongoDB (future)
class MongoEvaluationRepository(IEvaluationRepository):
    def __init__(self, collection: Collection):
        self.collection = collection
    
    async def find_by_id(self, eval_id: str) -> Optional[Evaluation]:
        doc = await self.collection.find_one({"_id": eval_id})
        return Evaluation.from_dict(doc) if doc else None
```

### Benefits
- **Testability**: Easy to create in-memory implementations for testing
- **Flexibility**: Can switch databases without changing business logic
- **Consistency**: All data access follows the same pattern
- **Type Safety**: Clear interfaces with type hints

## 2. Unit of Work Pattern

The Unit of Work pattern maintains a list of objects affected by a business transaction and coordinates writing out changes.

### Purpose
- Manage database transactions consistently
- Ensure all changes in a business operation succeed or fail together
- Reduce database round trips by batching operations
- Provide a clear transaction boundary

### Example Implementation

```python
class IUnitOfWork(ABC):
    evaluations: IEvaluationRepository
    
    @abstractmethod
    async def __aenter__(self):
        pass
    
    @abstractmethod
    async def __aexit__(self, *args):
        pass
    
    @abstractmethod
    async def commit(self):
        pass
    
    @abstractmethod
    async def rollback(self):
        pass

class PostgresUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    async def __aenter__(self):
        self._session = self.session_factory()
        self.evaluations = PostgresEvaluationRepository(self._session)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self._session.close()
    
    async def commit(self):
        await self._session.commit()
    
    async def rollback(self):
        await self._session.rollback()

# Usage in service layer
async def create_evaluation_with_metadata(uow: IUnitOfWork, eval_data: dict):
    async with uow:
        # All operations within the same transaction
        evaluation = await uow.evaluations.save(
            Evaluation(data=eval_data)
        )
        await uow.metadata.save(
            Metadata(eval_id=evaluation.id, created_by="system")
        )
        await uow.audit_logs.save(
            AuditLog(action="evaluation_created", eval_id=evaluation.id)
        )
        # Commit all changes together
        await uow.commit()
```

### Benefits
- **Atomic Operations**: All changes succeed or fail together
- **Clear Boundaries**: Explicit transaction scope
- **Performance**: Batch multiple operations
- **Consistency**: Prevents partial updates

## 3. Query Objects Pattern

Query Objects encapsulate database queries as reusable, composable objects.

### Purpose
- Avoid string concatenation for complex queries
- Make queries testable and type-safe
- Enable query composition and reuse
- Separate query construction from execution

### Example Implementation

```python
@dataclass
class QueryFilter:
    """Base class for query filters"""
    pass

@dataclass
class EvaluationFilter(QueryFilter):
    status: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def apply_to_query(self, query: Select) -> Select:
        """Apply filters to SQLAlchemy query"""
        if self.status:
            query = query.where(EvaluationModel.status == self.status)
        if self.created_after:
            query = query.where(EvaluationModel.created_at >= self.created_after)
        if self.created_before:
            query = query.where(EvaluationModel.created_at <= self.created_before)
        if self.user_id:
            query = query.where(EvaluationModel.user_id == self.user_id)
        if self.tags:
            query = query.where(EvaluationModel.tags.contains(self.tags))
        return query

class EvaluationQueryBuilder:
    """Fluent interface for building queries"""
    def __init__(self):
        self._filter = EvaluationFilter()
    
    def with_status(self, status: str) -> 'EvaluationQueryBuilder':
        self._filter.status = status
        return self
    
    def created_between(self, start: datetime, end: datetime) -> 'EvaluationQueryBuilder':
        self._filter.created_after = start
        self._filter.created_before = end
        return self
    
    def for_user(self, user_id: str) -> 'EvaluationQueryBuilder':
        self._filter.user_id = user_id
        return self
    
    def build(self) -> EvaluationFilter:
        return self._filter

# Usage
query = (EvaluationQueryBuilder()
    .with_status("completed")
    .created_between(week_ago, today)
    .for_user(current_user_id)
    .build())

evaluations = await repository.find_all(query)
```

### Benefits
- **Reusability**: Common queries can be shared
- **Composability**: Build complex queries from simple parts
- **Type Safety**: Compile-time checking of query parameters
- **Testability**: Test query logic without database

## 4. Cursor-Based Pagination

Cursor-based pagination uses a pointer to a specific item in the dataset rather than offset/limit.

### Purpose
- Handle large datasets efficiently
- Provide stable pagination (no skipped/duplicate items)
- Better performance than offset/limit for large offsets
- Works well with real-time data

### Example Implementation

```python
@dataclass
class PageInfo:
    """Pagination metadata"""
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]

@dataclass
class PaginatedResult(Generic[T]):
    """Generic paginated result"""
    items: List[T]
    page_info: PageInfo
    total_count: Optional[int] = None

class CursorPagination:
    """Handles cursor-based pagination logic"""
    
    @staticmethod
    def encode_cursor(item_id: str, timestamp: datetime) -> str:
        """Create an opaque cursor from item data"""
        cursor_data = f"{timestamp.isoformat()}:{item_id}"
        return base64.b64encode(cursor_data.encode()).decode()
    
    @staticmethod
    def decode_cursor(cursor: str) -> Tuple[datetime, str]:
        """Extract timestamp and ID from cursor"""
        cursor_data = base64.b64decode(cursor.encode()).decode()
        timestamp_str, item_id = cursor_data.split(":")
        return datetime.fromisoformat(timestamp_str), item_id

class PaginatedEvaluationRepository(PostgresEvaluationRepository):
    async def find_paginated(
        self,
        filter: EvaluationFilter,
        first: Optional[int] = None,
        after: Optional[str] = None,
        last: Optional[int] = None,
        before: Optional[str] = None
    ) -> PaginatedResult[Evaluation]:
        query = select(EvaluationModel)
        query = filter.apply_to_query(query)
        
        # Apply cursor constraints
        if after:
            after_time, after_id = CursorPagination.decode_cursor(after)
            query = query.where(
                or_(
                    EvaluationModel.created_at > after_time,
                    and_(
                        EvaluationModel.created_at == after_time,
                        EvaluationModel.id > after_id
                    )
                )
            )
        
        if before:
            before_time, before_id = CursorPagination.decode_cursor(before)
            query = query.where(
                or_(
                    EvaluationModel.created_at < before_time,
                    and_(
                        EvaluationModel.created_at == before_time,
                        EvaluationModel.id < before_id
                    )
                )
            )
        
        # Apply limit
        limit = first or last or 20
        query = query.order_by(
            EvaluationModel.created_at.desc(),
            EvaluationModel.id.desc()
        ).limit(limit + 1)  # Fetch one extra to check for more
        
        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        # Check if there are more items
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
        
        # Create page info
        page_info = PageInfo(
            has_next_page=has_more if first else False,
            has_previous_page=bool(after) if first else bool(before),
            start_cursor=CursorPagination.encode_cursor(
                items[0].id, items[0].created_at
            ) if items else None,
            end_cursor=CursorPagination.encode_cursor(
                items[-1].id, items[-1].created_at
            ) if items else None
        )
        
        return PaginatedResult(
            items=items,
            page_info=page_info
        )

# Usage in API
@app.get("/evaluations")
async def list_evaluations(
    first: int = Query(20, le=100),
    after: Optional[str] = None,
    status: Optional[str] = None,
    uow: IUnitOfWork = Depends(get_unit_of_work)
):
    filter = EvaluationFilter(status=status)
    async with uow:
        result = await uow.evaluations.find_paginated(
            filter=filter,
            first=first,
            after=after
        )
    
    return {
        "data": [eval.to_dict() for eval in result.items],
        "pageInfo": {
            "hasNextPage": result.page_info.has_next_page,
            "endCursor": result.page_info.end_cursor
        }
    }
```

### Benefits
- **Performance**: O(1) pagination regardless of page number
- **Stability**: New items don't affect pagination
- **Scalability**: Works with millions of records
- **Real-time Compatible**: Handles concurrent insertions gracefully

## Summary

These patterns work together to create a robust storage service:

1. **Repository Pattern** provides the interface for data access
2. **Unit of Work** manages transactions across repositories
3. **Query Objects** enable complex, reusable queries
4. **Cursor Pagination** handles large result sets efficiently

This architecture makes the storage service:
- **Testable**: Easy to mock and test in isolation
- **Maintainable**: Clear separation of concerns
- **Scalable**: Efficient patterns for large datasets
- **Flexible**: Easy to add new storage backends or change implementations