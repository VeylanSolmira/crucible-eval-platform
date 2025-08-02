#!/bin/bash
# Script to check if logs are making it to Loki

# Configuration
NAMESPACE="${NAMESPACE:-crucible}"
LOKI_URL="http://localhost:3100"
CURRENT_TIME=$(date +%s)
START_TIME=$((CURRENT_TIME - 3600))  # Look back 1 hour

echo "🔍 Checking Loki for logs..."
echo "   Namespace: $NAMESPACE"
echo "   Time range: Last hour"
echo ""

# Port forward to Loki if not already done
echo "📡 Setting up port-forward to Loki..."
kubectl port-forward -n $NAMESPACE svc/loki 3100:3100 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

# Function to query Loki
query_loki() {
    local query="$1"
    local description="$2"
    
    echo "🔎 Query: $description"
    echo "   LogQL: $query"
    
    # URL encode the query
    encoded_query=$(echo -n "$query" | jq -sRr @uri)
    
    # Query Loki
    response=$(curl -s -G \
        --data-urlencode "query=$query" \
        --data-urlencode "start=${START_TIME}000000000" \
        --data-urlencode "end=${CURRENT_TIME}000000000" \
        --data-urlencode "limit=100" \
        "${LOKI_URL}/loki/api/v1/query_range")
    
    # Check if we got results
    result_count=$(echo "$response" | jq -r '.data.result | length' 2>/dev/null || echo "0")
    
    if [ "$result_count" -gt 0 ]; then
        echo "   ✅ Found $result_count log streams"
        
        # Show sample entries
        echo "$response" | jq -r '.data.result[0].values[0:3][] | "   " + .[1]' 2>/dev/null | head -10
        echo ""
    else
        echo "   ❌ No logs found"
        echo ""
    fi
}

# Query 1: All pods in namespace
query_loki '{namespace="'$NAMESPACE'"}' "All pods in $NAMESPACE namespace"

# Query 2: Test coordinator pods
query_loki '{namespace="'$NAMESPACE'", pod_name=~"test-coordinator-.*"}' "Test coordinator pods"

# Query 3: Test runner pods
query_loki '{namespace="'$NAMESPACE'", pod_name=~".*-tests-.*"}' "Test runner pods"

# Query 4: Evaluation pods
query_loki '{namespace="'$NAMESPACE'", pod_name=~"evaluation-job-.*"}' "Evaluation job pods"

# Query 5: Failed pods (if container status is logged)
query_loki '{namespace="'$NAMESPACE'"} |~ "Failed|Error|Exception"' "Pods with failures"

# Clean up port-forward
kill $PF_PID 2>/dev/null

echo "📊 Summary of available labels:"
echo "   To see all available labels, query: ${LOKI_URL}/loki/api/v1/labels"