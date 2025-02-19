#!/bin/bash

echo "=== Balance & Payment Endpoints ==="
echo "Get wallet balance:"
curl -s http://localhost:8000/balance

echo -e "\n\nTest payment simulation (DEBUG mode):"
curl -s -X POST http://localhost:8000/debug/simulate_payment \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "memo": "test payment"}'

echo -e "\n\n=== Feeder Control Endpoints ==="
echo "Get feeder status:"
curl -s http://localhost:8000/status/feeder

echo -e "\n\nGet trigger amount:"
curl -s http://localhost:8000/status/trigger

echo -e "\n\n=== CyberHerd Endpoints ==="
echo "Get CyberHerd list:"
curl -s http://localhost:8000/cyberherd

echo -e "\n\nGet remaining spots:"
curl -s http://localhost:8000/cyberherd/spots_remaining

echo -e "\n\n=== Conversion Endpoints ==="
echo "Convert 1.0 USD to sats:"
curl -s http://localhost:8000/convert/1.0

echo -e "\n\n=== Debug Endpoints ==="
echo "Get debug feeder status:"
curl -s http://localhost:8000/debug/feeder_status

echo "Simulate CyberHerd zap:"
curl -s -X POST http://localhost:8000/debug/simulate_payment \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 21000,
    "memo": "test zap",
    "is_cyberherd": true,
    "pubkey": "dd9b879f25694204a76e53427e10dfe765fd4d0f27510a1b95542c28ad82c297",
    "event_id": "fa75c355e6c39adb41e2576af7c94eccf5e0d74ff1f5b3831baef5e7a6ac78c6"
  }'

echo -e "\n\n=== WebSocket Connection ==="
echo "To test WebSocket connection:"
echo "wscat -c ws://localhost:8000/ws/"
echo -e "\n"
