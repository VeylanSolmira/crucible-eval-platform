---
title: 'Performance & Scale'
duration: 2
tags: ['performance', 'benchmarks']
---

## Performance & Scale

### Current Benchmarks

| Operation       | Latency | Throughput | Bottleneck        |
| --------------- | ------- | ---------- | ----------------- |
| Simple eval     | 45ms    | 1,000/sec  | CPU               |
| Docker eval     | 890ms   | 100/sec    | Container startup |
| gVisor eval     | 1,250ms | 80/sec     | Kernel overhead   |
| Queue ops       | <1ms    | 10,000/sec | Memory            |
| Event streaming | <1ms    | 50,000/sec | Memory            |

### Scaling Strategy

1. **Immediate**: Container pre-warming
2. **Short-term**: Horizontal pod scaling
3. **Long-term**: Multi-region deployment
