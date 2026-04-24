import requests
import json
import time

BASE_URL = "http://localhost:8001/api/v1"
TEST_USER = {
    "email": f"tester_{int(time.time())}@example.com",
    "username": f"tester_{int(time.time())}",
    "password": "securepassword123"
}

def log(msg):
    print(f"\n>>> {msg}")

def test_flow():
    # 1. Register
    log("1. Testing Registration...")
    resp = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
    print(f"Status: {resp.status_code}")
    assert resp.status_code in [200, 201]
    
    # 2. Login
    log("2. Testing Login...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER["email"],
        "password": TEST_USER["password"]
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200
    tokens = resp.json()
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 3. Test Protected Endpoint without Token
    log("3. Testing Security (Unauthorized access)...")
    resp = requests.get(f"{BASE_URL}/videos")
    print(f"Status (Expected 401): {resp.status_code}")
    assert resp.status_code == 401

    # 4. List Videos
    log("4. Testing List Videos...")
    resp = requests.get(f"{BASE_URL}/videos", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200
    videos = resp.json().get("videos", [])
    print(f"Found {len(videos)} videos.")
    
    video_id = None
    if videos:
        # Trong service, key có thể là 'video_id' hoặc 'id' tùy vào metadata
        video_id = videos[0].get("video_id") or videos[0].get("id")
        print(f"Using video_id: {video_id}")

    # 5. Video Summary
    if video_id:
        log("5. Testing Video Summary...")
        resp = requests.post(f"{BASE_URL}/videos/summary", 
                             json={"video_id": video_id}, 
                             headers=headers)
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200
        print(f"Summary preview: {resp.json().get('summary')[:100]}...")

    # 6. Chat Stream (First time - Cache MISS)
    log("6. Testing Chat Stream (First time - Workflow execution)...")
    chat_payload = {"message": "Naive Bayes là gì?", "stream": True}
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/chat/stream", json=chat_payload, headers=headers, stream=True)
    
    full_text = ""
    for line in resp.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data = json.loads(decoded[6:])
                if data["type"] == "token":
                    full_text += data["content"]
                elif data["type"] == "metadata":
                    print("\nMetadata received.")
    
    print(f"Chat Response: {full_text[:100]}...")
    print(f"Time taken: {time.time() - start_time:.2f}s")

    # 7. Chat Stream (Second time - Cache HIT)
    log("7. Testing Semantic Cache (Second time - Expecting FAST response)...")
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/chat/stream", json=chat_payload, headers=headers, stream=True)
    
    cache_hit = False
    for line in resp.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data = json.loads(decoded[6:])
                if data["type"] == "status" and "bộ nhớ đệm" in data["status"]:
                    cache_hit = True
    
    print(f"Cache HIT detected: {cache_hit}")
    print(f"Time taken: {time.time() - start_time:.2f}s")
    assert cache_hit is True

if __name__ == "__main__":
    try:
        test_flow()
        log("PASSED: ALL TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        log(f"FAILED: TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
