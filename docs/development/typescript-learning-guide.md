# TypeScript Learning Guide for METR Platform Engineering

## Overview

This guide outlines a practical learning path for TypeScript in the context of the METR platform engineering role. The focus is on building monitoring dashboards and internal tooling, not consumer-facing products.

## Role Context

### What You'll Build
- **Real-time Monitoring Dashboard**: Live evaluation progress, resource metrics
- **Safety Controls**: Emergency stop functionality, alert systems
- **Analytics Views**: Historical data, performance trends
- **Admin Interfaces**: User management, configuration panels

### TypeScript's Role in the Platform
```
┌─────────────────────────────┐
│   React/TypeScript Frontend │ ← You'll work here (20% of role)
│   (Monitoring & Control)    │
└──────────────┬──────────────┘
               │ REST/WebSocket
┌──────────────▼──────────────┐
│    Python/FastAPI Backend   │ ← Main focus (80% of role)
│   (Evaluation Orchestration)│
└─────────────────────────────┘
```

## Learning Phases

### Phase 1: TypeScript Fundamentals (Week 1)

#### Day 1-2: TypeScript Basics
**Goal**: Understand TypeScript's type system

**Topics**:
- Basic types (string, number, boolean, arrays)
- Interfaces vs Types
- Optional properties and union types
- Type inference

**Practice Project**: Type-safe utility functions
```typescript
interface EvaluationMetrics {
  cpuUsage: number;
  memoryUsage: number;
  runtime: number;
  status: 'running' | 'completed' | 'failed';
}

function calculateResourceEfficiency(metrics: EvaluationMetrics): number {
  // Implementation
}
```

**Resources**:
- [TypeScript Handbook - Basic Types](https://www.typescriptlang.org/docs/handbook/2/basic-types.html)
- [TypeScript in 5 minutes](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html)

#### Day 3-4: Functions and Classes
**Goal**: Type-safe functions and OOP patterns

**Topics**:
- Function type annotations
- Generic functions
- Classes with TypeScript
- Access modifiers

**Practice Project**: API client class
```typescript
class EvaluationAPIClient {
  private baseURL: string;
  
  async getEvaluation(id: string): Promise<Evaluation> {
    // Typed API calls
  }
}
```

#### Day 5-7: Advanced Types
**Goal**: Handle complex type scenarios

**Topics**:
- Generics in depth
- Utility types (Partial, Pick, Omit, Record)
- Type guards and narrowing
- Discriminated unions

**Practice Project**: WebSocket message handler
```typescript
type WSMessage = 
  | { type: 'evaluation.started'; payload: { id: string; timestamp: Date } }
  | { type: 'evaluation.progress'; payload: { id: string; progress: number } }
  | { type: 'evaluation.failed'; payload: { id: string; error: string } };

function handleMessage(message: WSMessage) {
  switch (message.type) {
    case 'evaluation.started':
      // Type-safe handling
  }
}
```

### Phase 2: React + TypeScript (Week 2)

#### Day 8-9: React Components with TypeScript
**Goal**: Build type-safe React components

**Topics**:
- Function components with props
- Children and event handlers
- useState and useEffect with types
- Custom hooks

**Practice Project**: Evaluation monitoring components
```typescript
interface EvaluationCardProps {
  evaluation: Evaluation;
  onStop: (id: string) => Promise<void>;
  onViewDetails: (id: string) => void;
}

const EvaluationCard: React.FC<EvaluationCardProps> = ({ 
  evaluation, 
  onStop, 
  onViewDetails 
}) => {
  const [isStopping, setIsStopping] = useState(false);
  
  const handleStop = async () => {
    setIsStopping(true);
    await onStop(evaluation.id);
    setIsStopping(false);
  };
  
  return (
    // JSX
  );
};
```

#### Day 10-11: State Management
**Goal**: Type-safe global state

**Topics**:
- Context API with TypeScript
- Redux Toolkit basics
- RTK Query for API calls
- Typed actions and selectors

**Practice Project**: Evaluation state management
```typescript
// Redux Toolkit slice
const evaluationsSlice = createSlice({
  name: 'evaluations',
  initialState: {
    items: [] as Evaluation[],
    isLoading: false,
    error: null as string | null,
  },
  reducers: {
    setEvaluations: (state, action: PayloadAction<Evaluation[]>) => {
      state.items = action.payload;
    },
  },
});
```

#### Day 12-14: Real-time Features
**Goal**: WebSocket integration for live updates

**Topics**:
- Socket.io client with TypeScript
- Real-time state updates
- Connection management
- Error handling

**Practice Project**: Live evaluation dashboard
```typescript
const useEvaluationUpdates = (evaluationId: string) => {
  const [updates, setUpdates] = useState<EvaluationUpdate[]>([]);
  
  useEffect(() => {
    const socket = io('/evaluations');
    
    socket.on(`evaluation:${evaluationId}:update`, (update: EvaluationUpdate) => {
      setUpdates(prev => [...prev, update]);
    });
    
    return () => {
      socket.disconnect();
    };
  }, [evaluationId]);
  
  return updates;
};
```

### Phase 3: Full Stack Integration (Week 3)

#### Day 15-16: API Integration
**Goal**: Type-safe frontend-backend communication

**Topics**:
- Shared types between frontend/backend
- API client generation
- Error handling patterns
- Loading states

**Practice Project**: Complete CRUD operations
```typescript
// Shared types (could be in a shared package)
interface CreateEvaluationRequest {
  modelId: string;
  testSuite: string;
  configuration: EvaluationConfig;
}

interface EvaluationResponse {
  id: string;
  status: EvaluationStatus;
  createdAt: string;
  metrics: EvaluationMetrics;
}

// API hooks
const useCreateEvaluation = () => {
  const [createEvaluation, { isLoading, error }] = useCreateEvaluationMutation();
  
  const handleCreate = async (request: CreateEvaluationRequest) => {
    try {
      const result = await createEvaluation(request).unwrap();
      return result;
    } catch (error) {
      // Typed error handling
    }
  };
  
  return { handleCreate, isLoading, error };
};
```

#### Day 17-18: Data Visualization
**Goal**: Type-safe charts and metrics

**Topics**:
- Chart libraries with TypeScript (Recharts, Chart.js)
- Data transformation
- Performance optimization
- Responsive design

**Practice Project**: Resource usage charts
```typescript
interface ResourceData {
  timestamp: Date;
  cpu: number;
  memory: number;
  gpu?: number;
}

const ResourceChart: React.FC<{ data: ResourceData[] }> = ({ data }) => {
  const chartData = useMemo(() => 
    data.map(d => ({
      time: d.timestamp.toISOString(),
      cpu: d.cpu,
      memory: d.memory,
    })),
    [data]
  );
  
  return (
    <LineChart data={chartData}>
      {/* Chart configuration */}
    </LineChart>
  );
};
```

#### Day 19-21: Testing and Best Practices
**Goal**: Maintainable TypeScript code

**Topics**:
- React Testing Library with TypeScript
- Component testing patterns
- Mocking typed dependencies
- Performance profiling

**Practice Project**: Test suite for dashboard
```typescript
describe('EvaluationCard', () => {
  it('should handle stop action', async () => {
    const mockOnStop = jest.fn().mockResolvedValue(undefined);
    const evaluation = createMockEvaluation();
    
    render(
      <EvaluationCard 
        evaluation={evaluation} 
        onStop={mockOnStop}
        onViewDetails={jest.fn()}
      />
    );
    
    await userEvent.click(screen.getByRole('button', { name: /stop/i }));
    
    expect(mockOnStop).toHaveBeenCalledWith(evaluation.id);
  });
});
```

## Project Milestones

### Milestone 1: Basic Dashboard (End of Week 1)
- Display list of evaluations
- Show basic status and metrics
- Type-safe component props

### Milestone 2: Interactive Features (End of Week 2)
- Start/stop evaluations
- Real-time status updates
- Resource usage graphs

### Milestone 3: Production-Ready (End of Week 3)
- Complete error handling
- Loading states
- Responsive design
- Test coverage

## Interview Preparation

### Key Talking Points

1. **Type Safety Benefits**
   - "I use TypeScript to catch integration errors between frontend and backend early"
   - "Type-safe API contracts reduce runtime errors in production"
   - "IntelliSense improves development velocity"

2. **Practical Experience**
   - "Built monitoring dashboards with real-time WebSocket updates"
   - "Implemented type-safe Redux state management for complex UI state"
   - "Created reusable component libraries with proper type definitions"

3. **Full Stack Integration**
   - "Shared TypeScript interfaces between frontend and backend"
   - "Used code generation for API clients from OpenAPI specs"
   - "Implemented end-to-end type safety from database to UI"

### Common Interview Questions

**Q: How do you handle API type safety?**
```typescript
// Show shared types approach
// api-types.ts (shared package)
export interface APIResponse<T> {
  data: T;
  error?: string;
  timestamp: string;
}

// Frontend usage
const { data } = await api.get<APIResponse<Evaluation>>('/evaluations/123');
```

**Q: How do you type Redux state?**
```typescript
// Show Redux Toolkit approach
interface RootState {
  evaluations: EvaluationsState;
  auth: AuthState;
  ui: UIState;
}

const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

**Q: How do you handle complex component props?**
```typescript
// Show composition and utility types
type BaseProps = {
  id: string;
  className?: string;
};

type EvaluationProps = BaseProps & {
  evaluation: Evaluation;
  actions?: {
    onStop?: (id: string) => void;
    onRestart?: (id: string) => void;
  };
};
```

## Resources for Continued Learning

### Official Documentation
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Redux Toolkit TypeScript Guide](https://redux-toolkit.js.org/usage/usage-with-typescript)

### Courses and Tutorials
- [Total TypeScript](https://www.totaltypescript.com/) - Matt Pocock's courses
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/) - Free online book
- [Effective TypeScript](https://effectivetypescript.com/) - 62 specific ways to improve

### Practice Projects
1. **Evaluation Dashboard**: Full monitoring interface
2. **Metrics Visualizer**: Real-time charts with WebSocket
3. **Admin Panel**: User management with role-based access
4. **Alert System**: Notification center with different alert types

### GitHub Repos to Study
- [Backstage](https://github.com/backstage/backstage) - Developer portal with TypeScript
- [Grafana](https://github.com/grafana/grafana) - Monitoring dashboard
- [Metabase](https://github.com/metabase/metabase) - Analytics platform

## Next Steps

1. **Week 1**: Complete TypeScript fundamentals
2. **Week 2**: Build a simple React dashboard
3. **Week 3**: Add real-time features and testing
4. **Ongoing**: Contribute to open source TypeScript projects

Remember: For this role, TypeScript is a tool to build internal monitoring systems, not the primary skill. Focus on demonstrating you can learn quickly and build practical solutions.