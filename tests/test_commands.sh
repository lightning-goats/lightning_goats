#!/bin/bash

# Base URL
BASE_URL="http://localhost:8000"

# Test balance endpoint
echo "Testing balance endpoint..."
curl -X GET "${BASE_URL}/balance"

# Test CyberHerd spots
echo -e "\n\nTesting CyberHerd spots..."
curl -X GET "${BASE_URL}/cyberherd/spots_remaining"

# Test trigger amount
echo -e "\n\nTesting trigger amount..."
curl -X GET "${BASE_URL}/trigger_amount"

# Test payment creation
echo -e "\n\nTesting payment creation..."
curl -X POST "${BASE_URL}/payment" \
    -H "Content-Type: application/json" \
    -d '{"balance": 1000}'

# Test USD to sats conversion
echo -e "\n\nTesting USD to sats conversion..."
curl -X GET "${BASE_URL}/convert/1.0"

# Test feeder status
echo -e "\n\nTesting feeder status..."
curl -X GET "${BASE_URL}/feeder_status"

# Test CyberHerd list
echo -e "\n\nTesting CyberHerd list..."
curl -X GET "${BASE_URL}/get_cyber_herd"

# Test websocket connection (requires wscat)
echo -e "\n\nTo test WebSocket connection:"
echo "wscat -c ws://localhost:8000/ws/"
