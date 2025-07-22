# Test Marker Audit Report

Total test files analyzed: 30

## ⚠️  Undefined Markers Being Used

- `skip` used in:
  - tests/integration/test_core_flows.py::test_evaluation_timeout
- `skipif` used in:
  - tests/integration/test_executor_imports.py::test_ml_libraries_available

## 📝 Suggested Missing Markers

### tests/integration/test_celery_cancellation.py

- **TestCeleryCancellation**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_pending_task**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_running_task_without_terminate**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_running_task_with_terminate**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_completed_task**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_already_revoked_task**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_with_celery_disabled**
  - Has: none
  - Suggested to add: celery, integration
- **test_cancel_with_exception**
  - Has: none
  - Suggested to add: celery, integration
- **test_get_task_info_success**
  - Has: none
  - Suggested to add: celery, integration
- **test_get_task_info_failed**
  - Has: none
  - Suggested to add: celery, integration

### tests/integration/test_celery_connection.py

- **TestCeleryConnection**
  - Has: celery, integration
  - Suggested to add: redis
- **test_redis_connection**
  - Has: none
  - Suggested to add: celery, integration, redis
- **test_celery_broker_connection**
  - Has: none
  - Suggested to add: celery, integration, redis
- **test_celery_configuration**
  - Has: none
  - Suggested to add: celery, integration, redis

### tests/integration/test_celery_integration.py

- **test_single_evaluation**
  - Has: api
  - Suggested to add: celery, concurrency, docker, integration, redis, slow
- **test_concurrent_evaluations**
  - Has: api
  - Suggested to add: celery, concurrency, docker, integration, redis, slow
- **test_executor_shortage**
  - Has: api
  - Suggested to add: celery, concurrency, docker, integration, redis, slow
- **test_task_cancellation**
  - Has: api
  - Suggested to add: celery, concurrency, docker, integration, redis, slow
- **test_high_load**
  - Has: api, slow
  - Suggested to add: celery, concurrency, docker, integration, redis

### tests/integration/test_celery_tasks.py

- **TestCeleryTasks**
  - Has: celery, integration
  - Suggested to add: slow
- **test_health_check_task**
  - Has: none
  - Suggested to add: celery, integration, slow
- **test_evaluate_code_task**
  - Has: none
  - Suggested to add: celery, integration, slow
- **test_multiple_tasks_sequential**
  - Has: none
  - Suggested to add: celery, integration, slow
- **test_task_state_tracking**
  - Has: none
  - Suggested to add: celery, integration, slow

### tests/integration/test_core_flows.py

- **test_health_check**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow
- **test_submit_evaluation**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow
- **test_evaluation_lifecycle**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow
- **test_error_handling**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow
- **test_concurrent_evaluations**
  - Has: api, integration, slow
  - Suggested to add: concurrency, docker
- **test_storage_retrieval**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow
- **test_evaluation_timeout**
  - Has: api, integration, skip
  - Suggested to add: concurrency, docker, slow
- **test_language_parameter**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow

### tests/integration/test_docker_event_diagnostics.py

- **test_diagnose_container_lifecycle_timing**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow
- **test_concurrent_fast_failures_event_handling**
  - Has: api, integration, slow
  - Suggested to add: concurrency, docker
- **test_container_removal_timing**
  - Has: api, integration
  - Suggested to add: concurrency, docker, slow

### tests/integration/test_executor_imports.py

- **TestExecutorImports**
  - Has: docker, executor, integration
  - Suggested to add: slow
- **test_import_error_captured**
  - Has: none
  - Suggested to add: docker, integration, slow
- **test_ml_libraries_available**
  - Has: skipif
  - Suggested to add: docker, integration, slow
- **test_standard_library_imports**
  - Has: none
  - Suggested to add: docker, integration, slow

### tests/integration/test_fast_failing_containers.py

- **test_fast_failing_container_logs_captured**
  - Has: api, integration
  - Suggested to add: docker, slow
- **test_mixed_stdout_stderr_fast_failure**
  - Has: api, integration
  - Suggested to add: docker, slow
- **test_multiple_fast_failures_no_stuck_evaluations**
  - Has: api, integration, slow
  - Suggested to add: docker
- **test_extremely_fast_exit**
  - Has: api, integration
  - Suggested to add: docker, slow

### tests/integration/test_priority_celery.py

- **test_celery_priority_queue_order**
  - Has: celery, integration
  - Suggested to add: slow
- **test_celery_multiple_priorities**
  - Has: celery, integration
  - Suggested to add: slow

### tests/integration/test_priority_queue.py

- **test_priority_queue_basic**
  - Has: api, integration
  - Suggested to add: slow
- **test_queue_status_accuracy**
  - Has: api, integration
  - Suggested to add: slow

### tests/integration/test_resilience.py

- **test_service_restart_recovery**
  - Has: destructive
  - Suggested to add: api, celery, docker, integration, slow
- **test_celery_worker_failure_recovery**
  - Has: destructive
  - Suggested to add: api, celery, docker, integration, slow
- **test_storage_service_failure_recovery**
  - Has: destructive
  - Suggested to add: api, celery, docker, integration, slow
- **test_network_partition_recovery**
  - Has: destructive
  - Suggested to add: api, celery, docker, integration, slow

### tests/manual/test_db_flow.py

- **test_normal_evaluation**
  - Has: none
  - Suggested to add: api, database, slow
- **test_large_output**
  - Has: none
  - Suggested to add: api, database, slow

### tests/manual/test_storage_direct.py

- **test_file_storage**
  - Has: none
  - Suggested to add: database
- **test_database_storage**
  - Has: none
  - Suggested to add: database

### tests/security/test_input_validation.py

- **test_code_size_limit**
  - Has: none
  - Suggested to add: api, security
- **test_malformed_json_rejected**
  - Has: none
  - Suggested to add: api, security
- **test_missing_required_fields**
  - Has: none
  - Suggested to add: api, security
- **test_invalid_language_rejected**
  - Has: none
  - Suggested to add: api, security
- **test_negative_timeout_rejected**
  - Has: none
  - Suggested to add: api, security
- **test_excessive_timeout_rejected**
  - Has: none
  - Suggested to add: api, security
- **test_null_byte_injection**
  - Has: none
  - Suggested to add: api, security
- **test_unicode_handling**
  - Has: none
  - Suggested to add: api, security

### tests/unit/api/test_evaluation_request.py

- **TestEvaluationRequest**
  - Has: none
  - Suggested to add: docker, slow, unit
- **test_valid_request_minimal**
  - Has: none
  - Suggested to add: docker, slow, unit
- **test_valid_request_all_fields**
  - Has: none
  - Suggested to add: docker, slow, unit
- **test_missing_required_code**
  - Has: none
  - Suggested to add: docker, slow, unit
- **test_empty_code_rejected**
  - Has: none
  - Suggested to add: docker, slow, unit
- **test_timeout_boundaries**
  - Has: none
  - Suggested to add: docker, slow, unit
- **test_invalid_types**
  - Has: none
  - Suggested to add: docker, slow, unit

### tests/unit/celery/test_retry_config.py

- **TestRetryConfig**
  - Has: none
  - Suggested to add: celery, unit
- **test_calculate_retry_delay**
  - Has: none
  - Suggested to add: celery, unit
- **test_get_retry_message**
  - Has: none
  - Suggested to add: celery, unit
- **test_retryable_http_codes**
  - Has: none
  - Suggested to add: celery, unit
- **test_calculate_retry_delay_with_policies**
  - Has: none
  - Suggested to add: celery, unit
- **test_should_retry_http_error**
  - Has: none
  - Suggested to add: celery, unit
- **test_retry_strategy_class**
  - Has: none
  - Suggested to add: celery, unit

### tests/unit/storage/base_storage_test.py

- **test_store_and_retrieve_evaluation**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_retrieve_nonexistent_evaluation**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_update_evaluation**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_store_and_retrieve_events**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_retrieve_events_nonexistent**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_store_and_retrieve_metadata**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_retrieve_metadata_nonexistent**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_list_evaluations**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_list_empty_storage**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_delete_evaluation**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_delete_nonexistent**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_data_isolation**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_data_immutability**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_concurrent_writes**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_concurrent_read_write**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_empty_data_storage**
  - Has: none
  - Suggested to add: concurrency, unit
- **test_large_data_storage**
  - Has: none
  - Suggested to add: concurrency, unit

### tests/unit/storage/test_database_backend.py

- **test_transaction_rollback**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_sql_injection_safety**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_metadata_json_storage**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_cascade_deletion**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_timestamp_handling**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_concurrent_database_access**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_query_performance_with_indexes**
  - Has: none
  - Suggested to add: concurrency, database, unit

### tests/unit/storage/test_file_backend.py

- **test_directory_creation**
  - Has: none
  - Suggested to add: unit
- **test_file_format**
  - Has: none
  - Suggested to add: unit
- **test_atomic_writes**
  - Has: none
  - Suggested to add: unit
- **test_corrupted_file_handling**
  - Has: none
  - Suggested to add: unit
- **test_file_permissions**
  - Has: none
  - Suggested to add: unit
- **test_persistence_across_instances**
  - Has: none
  - Suggested to add: unit
- **test_listing_order**
  - Has: none
  - Suggested to add: unit

### tests/unit/storage/test_flexible_manager.py

- **TestFlexibleStorageManager**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_create_evaluation**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_update_evaluation_status**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_cache_usage**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_fallback_on_primary_failure**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_large_output_handling**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_event_tracking**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_list_evaluations_with_filter**
  - Has: none
  - Suggested to add: concurrency, slow, unit
- **test_delete_evaluation**
  - Has: none
  - Suggested to add: concurrency, slow, unit

### tests/unit/storage/test_memory_backend.py

- **test_memory_isolation**
  - Has: none
  - Suggested to add: unit
- **test_no_persistence**
  - Has: none
  - Suggested to add: unit

### tests/unit/storage/test_postgresql_operations.py

- **TestPostgreSQLOperations**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_jsonb_field_operations**
  - Has: none
  - Suggested to add: concurrency, database, unit
- **test_concurrent_updates**
  - Has: none
  - Suggested to add: concurrency, database, unit

## 📊 Marker Usage Statistics

- `integration`: 25 uses ✅
- `api`: 24 uses ✅
- `slow`: 6 uses ✅
- `celery`: 5 uses ✅
- `destructive`: 4 uses ✅
- `security`: 1 uses ✅
- `docker`: 1 uses ✅
- `executor`: 1 uses ✅
- `skipif`: 1 uses ❌
- `skip`: 1 uses ❌

## 🔍 Defined But Unused Markers

- `benchmark`
- `concurrency`
- `critical`
- `database`
- `dual_write`
- `e2e`
- `flaky`
- `performance`
- `priority_queue`
- `redis`
- `resilience`
- `storage`
- `timeout`
- `unit`