#!/bin/bash

echo "Testing balance endpoint..."
curl -s http://localhost:8000/balance

echo -e "\n\nTesting CyberHerd spots..."
curl -s http://localhost:8000/cyberherd/spots_remaining

echo -e "\n\nTesting trigger amount..."
curl -s http://localhost:8000/debug/status/trigger_amount

echo -e "\n\nTesting payment creation..."
curl -s -X POST http://localhost:8000/debug/simulate_payment \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "memo": "test payment"}'

echo -e "\n\nTesting USD to sats conversion..."
curl -s http://localhost:8000/convert/1.0

echo -e "\n\nTesting feeder status..."
curl -s http://localhost:8000/debug/feeder_status

echo -e "\n\nTesting CyberHerd list..."
curl -s http://localhost:8000/cyberherd

echo -e "\n\nTo test WebSocket connection:"
echo "wscat -c ws://localhost:8000/ws/"
echo -e "\n"
