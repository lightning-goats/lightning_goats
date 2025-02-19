#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Testing Core Endpoints ==="
echo "1. Get Balance:"
curl -s "${BASE_URL}/balance" | jq .

echo -e "\n2. Get Trigger Amount:"
curl -s "${BASE_URL}/status/trigger" | jq .

echo -e "\n3. Get Feeder Status:"
curl -s "${BASE_URL}/status/feeder" | jq .

echo -e "\n=== Testing CyberHerd Endpoints ==="
echo "4. Get CyberHerd Members:"
curl -s "${BASE_URL}/cyberherd" | jq .

echo -e "\n5. Get Remaining Spots:"
curl -s "${BASE_URL}/cyberherd/spots_remaining" | jq .

echo -e "\n=== Testing Payment Endpoints ==="
echo "6. Create Regular Payment:"
curl -s -X POST "${BASE_URL}/debug/simulate_payment" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "memo": "test payment"}' | jq .

echo -e "\n7. Convert USD to Sats:"
curl -s "${BASE_URL}/convert/1.0" | jq .

echo -e "\n=== Testing Debug Endpoints ==="
echo "8. Simulate CyberHerd Payment:"
curl -s -X POST "${BASE_URL}/debug/simulate_payment" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 21000,
    "memo": "test cyberherd payment",
    "is_cyberherd": true,
    "pubkey": "dd9b879f25694204a76e53427e10dfe765fd4d0f27510a1b95542c28ad82c297",
    "event_id": "fa75c355e6c39adb41e2576af7c94eccf5e0d74ff1f5b3831baef5e7a6ac78c6"
  }' | jq .

echo -e "\n9. Get Debug Feeder Status:"
curl -s "${BASE_URL}/debug/feeder_status" | jq .

echo -e "\n=== Testing CyberHerd Management ==="
echo "10. Add CyberHerd Member:"
curl -s -X POST "${BASE_URL}/cyberherd" \
  -H "Content-Type: application/json" \
  -d '[{
    "pubkey": "dd9b879f25694204a76e53427e10dfe765fd4d0f27510a1b95542c28ad82c297",
    "display_name": "Test User",
    "event_id": "fa75c355e6c39adb41e2576af7c94eccf5e0d74ff1f5b3831baef5e7a6ac78c6",
    "note": "2193354a620577e6fa92082f873440125660debb380b2c95afd94a5e91c3757a",
    "kinds": "9734",
    "nprofile": "nprofile1qqstest...",
    "lud16": "testuser@getalby.com",
    "payouts": 0.3,
    "amount": 21,
    "picture": "https://example.com/avatar.jpg"
  }]' | jq .

echo -e "\n11. Get Current CyberHerd Members:"
curl -s "${BASE_URL}/cyberherd" | jq .

echo -e "\n12. Delete CyberHerd Member:"
curl -s -X DELETE "${BASE_URL}/cyberherd/delete/testuser@getalby.com" | jq .

echo -e "\n13. Update CyberHerd Member (Add Special Kind):"
curl -s -X POST "${BASE_URL}/cyberherd" \
  -H "Content-Type: application/json" \
  -d '[{
    "pubkey": "dd9b879f25694204a76e53427e10dfe765fd4d0f27510a1b95542c28ad82c297",
    "display_name": "Test User",
    "event_id": "new_event_id_here",
    "note": "new_note_here",
    "kinds": "6,9734",
    "nprofile": "nprofile1qqstest...",
    "lud16": "testuser@getalby.com",
    "payouts": 0.5,
    "amount": 0,
    "picture": "https://example.com/avatar.jpg"
  }]' | jq .

echo -e "\n=== WebSocket Test Info ==="
echo "To test WebSocket connection:"
echo "wscat -c ws://localhost:8000/ws/"
