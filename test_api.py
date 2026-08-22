"""
Simple test script to verify backend API endpoints
"""

import httpx
import asyncio
from typing import Optional

BASE_URL = "http://localhost:8000"


async def test_health_check():
    """Test health check endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Health Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_list_sources():
    """Test list sources endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/sources")
        print(f"\nList Sources: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} sources")
            return True
        else:
            print(f"Error: {response.text}")
            return False


async def test_list_stories():
    """Test list stories endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/stories")
        print(f"\nList Stories: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} stories")
            return True
        else:
            print(f"Error: {response.text}")
            return False


async def test_dashboard_stats():
    """Test dashboard stats endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/stories/stats/dashboard")
        print(f"\nDashboard Stats: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Stats: {data}")
            return True
        else:
            print(f"Error: {response.text}")
            return False


async def main():
    """Run all tests"""
    print("=" * 50)
    print("Testing Flobstar News Intelligence Backend API")
    print("=" * 50)

    tests = [
        ("Health Check", test_health_check),
        ("List Sources", test_list_sources),
        ("List Stories", test_list_stories),
        ("Dashboard Stats", test_dashboard_stats),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{name}: ERROR - {str(e)}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
