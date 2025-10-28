# InjectQ Performance Benchmarks - Quick Guide

## 🚀 Running Benchmarks

### Basic Benchmark Run
```bash
pytest tests/test_benchmarks.py --benchmark-only
```

### Verbose Output with Statistics
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-verbose
```

### Save Results for Historical Tracking
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave
```

### Compare Two Benchmark Runs
```bash
# Run first benchmark
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-name=baseline

# Make changes to code...

# Run second benchmark
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-name=optimized

# Compare results
pytest-benchmark compare baseline optimized
```

### Run Specific Benchmark
```bash
pytest tests/test_benchmarks.py::test_benchmark_container_creation --benchmark-only
```

### Run Regular Tests (Skip Benchmarks)
```bash
pytest tests/test_benchmarks.py  # Runs without detailed timing
```

---

## 📊 Performance Summary (TL;DR)

| Category | Performance | Use Case |
|----------|-------------|----------|
| **Basic Operations** | 270-780 ns | Container lookups, bindings |
| **Dependency Resolution** | 1-2 μs | Service instantiation |
| **Factory Functions** | 3-6 μs | Lazy initialization |
| **Load (100 services)** | 779 μs | Bulk registration |
| **Load (1000 gets)** | 739 μs | High-frequency access |
| **Web Request (10 svcs)** | 142 μs | Typical API request |
| **Thread-Safe Ops** | 24 μs | Concurrent access |

**Verdict:** ✅ Production-ready for high-performance applications

---

## 🎯 Benchmark Categories

### 1. Basic Container Operations
- `test_benchmark_container_creation` - Creating new containers
- `test_benchmark_bind_simple_class` - Binding classes
- `test_benchmark_bind_instance` - Binding instances
- `test_benchmark_bind_factory` - Binding factories
- `test_benchmark_container_clear` - Clearing container
- `test_benchmark_has_service` - Checking service existence
- `test_benchmark_container_getitem` - Accessing via `container[Type]`

### 2. Service Retrieval
- `test_benchmark_get_simple_service` - Basic service retrieval
- `test_benchmark_get_singleton` - Singleton scope retrieval
- `test_benchmark_get_transient` - Transient scope retrieval

### 3. Dependency Resolution
- `test_benchmark_resolve_simple_dependency` - Single dependency
- `test_benchmark_resolve_nested_dependencies` - 3-level nesting
- `test_benchmark_resolve_multiple_dependencies` - 3 dependencies
- `test_benchmark_resolve_deep_dependency_tree` - 5-level tree

### 4. Factory Functions
- `test_benchmark_factory_simple` - Simple factory
- `test_benchmark_factory_with_dependency` - Factory with deps

### 5. Scope Performance
- `test_benchmark_singleton_scope_cached` - Cached singleton
- `test_benchmark_transient_scope_creation` - New instance creation
- `test_benchmark_request_scope` - Request-scoped services

### 6. Load Testing
- `test_benchmark_load_many_services` - 100 service registrations
- `test_benchmark_load_repeated_gets` - 1,000 get operations
- `test_benchmark_load_transient_creation` - 1,000 transient instances
- `test_benchmark_load_complex_graph` - Complex dependency graph

### 7. Thread Safety
- `test_benchmark_thread_safe_container` - Thread-safe operations
- `test_benchmark_concurrent_gets` - 10 threads × 100 operations

### 8. Real-World Scenarios
- `test_benchmark_web_request_simulation` - Web request with 10 services
- `test_benchmark_api_service_stack` - 4-layer API stack
- `test_benchmark_override_context` - Context override patterns

### 9. Stress Tests
- `test_benchmark_stress_sequential_binds` - 500 sequential binds
- `test_benchmark_stress_resolution_mix` - 100 mixed operations

---

## 📈 Key Performance Metrics

### Ultra-Fast (< 1 μs)
```
has_service:        272 ns   ⚡ 3.67M ops/sec
bind_factory:       271 ns   ⚡ 3.68M ops/sec
bind_instance:      784 ns   ⚡ 1.28M ops/sec
```

### Fast (1-10 μs)
```
get_singleton:      1.02 μs  ⚡ 976K ops/sec
resolve_simple:     1.05 μs  ⚡ 955K ops/sec
resolve_nested:     1.01 μs  ⚡ 990K ops/sec
api_service_stack:  1.06 μs  ⚡ 944K ops/sec
```

### Moderate (10-100 μs)
```
container_creation: 24.3 μs  ⚡ 41.2K ops/sec
thread_safe_ops:    24.7 μs  ⚡ 40.5K ops/sec
```

### Load Operations (100+ μs)
```
web_request (10):    142 μs  ⚡ 7,037 ops/sec
100 services:        779 μs  ⚡ 1,283 ops/sec
1000 gets:           739 μs  ⚡ 1,352 ops/sec
1000 transients:    24.8 ms  ⚡ 40 ops/sec
```

---

## 🔬 Understanding the Results

### Time Units
- **ns** (nanosecond) = 0.000001 milliseconds
- **μs** (microsecond) = 0.001 milliseconds  
- **ms** (millisecond) = 0.001 seconds

### Operations Per Second (OPS)
- Higher is better
- Calculated as `1 / mean_time`
- Shows throughput capacity

### Outliers
- **1.5 IQR:** Moderate outliers (expected)
- **1 StdDev:** Significant outliers (investigate if many)

### Comparison Operators
- **(1.0)** = Baseline (fastest test)
- **(2.5)** = 2.5× slower than baseline
- **(>1000.0)** = More than 1000× slower

---

## 💡 Performance Tips

### ✅ DO
- Use **singleton scope** for shared services (1 μs cached)
- Use **factory bindings** for lazy init (271 ns)
- Batch **service registrations** at startup (779 μs for 100)
- Check with **has_service** before complex ops (272 ns)

### ⚠️ CONSIDER
- **Transient scope** adds overhead (4.7 μs vs 1 μs)
- **Thread-safe** container is 24× slower (still fast at 24.7 μs)
- **Deep dependency trees** perform well (1 μs for 5 levels)

### ❌ AVOID
- Creating containers in hot paths (24.3 μs each)
- Overusing transient scope for shared services
- Unnecessary thread-safe containers (use only when needed)

---

## 🎨 Visualizing Results

### Generate Histogram (requires optional dependency)
```bash
pip install pytest-benchmark[histogram]
pytest tests/test_benchmarks.py --benchmark-only --benchmark-histogram
```

### Compare Runs with Charts
```bash
pytest-benchmark compare 0001 0002 --histogram
```

### View Saved Results
```bash
ls -la .benchmarks/Darwin-CPython-3.13-64bit/
cat .benchmarks/Darwin-CPython-3.13-64bit/0001_*.json | jq
```

---

## 📁 Output Files

### Benchmark Data
- **Location:** `.benchmarks/Darwin-CPython-3.13-64bit/`
- **Format:** JSON with full statistics
- **Naming:** `XXXX_<commit_hash>_<timestamp>.json`

### Reports
- **BENCHMARK_REPORT.md** - Comprehensive analysis
- **BENCHMARK_QUICK_GUIDE.md** - This file
- **benchmark_results.json** - Latest run results

---

## 🧪 Testing Your Changes

### Before Optimization
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-name=before
```

### After Optimization
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-name=after
```

### Compare Results
```bash
pytest-benchmark compare before after
```

Look for:
- ✅ **Green** = Faster (good!)
- ❌ **Red** = Slower (regression)
- **Percentage change** = Performance delta

---

## 🎯 CI/CD Integration

### Fail on Regression
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-compare=0001 --benchmark-compare-fail=mean:10%
```

### Save Baseline
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-save=baseline
```

### Check Against Baseline
```bash
pytest tests/test_benchmarks.py --benchmark-only --benchmark-compare=baseline
```

---

## 🐛 Troubleshooting

### Benchmark Takes Too Long
```bash
# Reduce max time per benchmark
pytest tests/test_benchmarks.py --benchmark-only --benchmark-max-time=0.1
```

### High Variance in Results
```bash
# Increase rounds for stability
pytest tests/test_benchmarks.py --benchmark-only --benchmark-min-rounds=100
```

### Skip Slow Benchmarks
```bash
# Skip load tests
pytest tests/test_benchmarks.py --benchmark-only -k "not load"
```

---

## 📚 Resources

- **Full Report:** See `BENCHMARK_REPORT.md`
- **Test Code:** `tests/test_benchmarks.py`
- **pytest-benchmark docs:** https://pytest-benchmark.readthedocs.io/
- **InjectQ docs:** See `docs/` directory

---

**Quick Stats:** 30 benchmarks | ~56s runtime | All passing ✅
