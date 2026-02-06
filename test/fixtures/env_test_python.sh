#!/bin/bash
if [[ "$PYTHON_TEST_VAR" == "test_value_123" ]]; then
    echo "SUCCESS"
    exit 0
else
    echo "FAILED" >&2
    exit 1
fi
