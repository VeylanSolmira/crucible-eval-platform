`jq` is a lightweight command-line JSON processor - think of it as `sed`/`awk` for JSON data. It's incredibly useful for parsing API responses, config files, and any JSON data.

## Basic Examples

### **Simple Extraction**
```bash
# Get a field from JSON
echo '{"name": "crucible", "version": "1.0"}' | jq '.name'
# Output: "crucible"

# Remove quotes
echo '{"name": "crucible"}' | jq -r '.name'
# Output: crucible
```

### **Common Use Cases for CEP**

**1. Parse API Responses**
```bash
# Get model response from OpenAI API
curl -s https://api.openai.com/v1/models | jq '.data[0].id'

# Extract specific test results
cat test_results.json | jq '.tests[] | select(.status == "failed")'
```

**2. Format JSON**
```bash
# Pretty print ugly JSON
echo '{"test":"adversarial","score":0.85}' | jq '.'
# Output:
# {
#   "test": "adversarial",
#   "score": 0.85
# }
```

**3. Filter and Transform**
```bash
# Get all failed tests with scores below 0.5
jq '.results[] | select(.score < 0.5 and .status == "fail") | {test: .name, score}' results.json

# Count failures
jq '[.results[] | select(.status == "fail")] | length' results.json
```

## Advanced Examples

### **Working with Arrays**
```bash
# Get first element
jq '.[0]' array.json

# Map over array
jq '.models[] | {name: .id, size: .parameters}' models.json

# Get array length
jq '. | length' array.json
```

### **Complex Queries**
```bash
# Nested extraction
jq '.data.attributes.metrics.accuracy' response.json

# Multiple fields
jq '{model: .model_id, accuracy: .metrics.accuracy, f1: .metrics.f1}' eval.json

# Conditional logic
jq 'if .score > 0.8 then "PASS" else "FAIL" end' test.json
```

## Real CEP Examples

**Parse adversarial test results:**
```bash
# Extract failed prompts
jq -r '.test_runs[] | select(.attack_successful == true) | .prompt' results.json

# Get success rate
jq '.test_runs | map(select(.attack_successful == true)) | length / (.test_runs | length)' results.json

# Create CSV from JSON
jq -r '.results[] | [.test_name, .model, .score] | @csv' results.json > results.csv
```

**Config manipulation:**
```bash
# Update config value
jq '.models += ["llama-3.2"]' config.json > config_new.json

# Merge JSON files
jq -s '.[0] * .[1]' defaults.json overrides.json
```

## Installation

```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Or download binary
wget https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
chmod +x jq-linux64
```

## Why It's Essential

For CEP, you'll likely use jq for:
- Parsing model API responses
- Analyzing test results
- Extracting metrics from JSON logs
- Creating reports from structured data
- Debugging JSON configurations

It's basically grep for JSON - once you learn it, you'll use it everywhere!