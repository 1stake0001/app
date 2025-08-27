import requests
import sys
import json
from datetime import datetime

class MobilePrivacyAPITester:
    def __init__(self, base_url="https://privacyscan-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    print(f"   Response: {response.text[:200]}...")
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        success, response = self.run_test("Dashboard Stats", "GET", "api/dashboard/stats", 200)
        if success and response:
            # Validate response structure
            required_fields = ['totalFlows', 'totalLeaks', 'recentFlows', 'privacyLeaks']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in response: {missing_fields}")
            else:
                print(f"   Total Flows: {response.get('totalFlows', 0)}")
                print(f"   Total Leaks: {response.get('totalLeaks', 0)}")
                print(f"   Recent Flows Count: {len(response.get('recentFlows', []))}")
                print(f"   Privacy Leaks Count: {len(response.get('privacyLeaks', []))}")
        return success, response

    def test_all_flows(self):
        """Test all flows endpoint"""
        success, response = self.run_test("All Flows", "GET", "api/dashboard/flows", 200)
        if success and isinstance(response, list):
            print(f"   Total flows returned: {len(response)}")
            if response:
                sample_flow = response[0]
                print(f"   Sample flow keys: {list(sample_flow.keys())}")
        return success, response

    def test_privacy_leaks(self):
        """Test privacy leaks endpoint"""
        success, response = self.run_test("Privacy Leaks", "GET", "api/dashboard/leaks", 200)
        if success and isinstance(response, list):
            print(f"   Total leaks returned: {len(response)}")
            if response:
                leak_types = [leak.get('leakType') for leak in response]
                unique_types = set(leak_types)
                print(f"   Leak types found: {list(unique_types)}")
        return success, response

    def test_generate_mock_data(self):
        """Test mock data generation"""
        success, response = self.run_test("Generate Mock Data", "POST", "api/test/generate-mock-data", 200)
        if success and response:
            print(f"   Response message: {response.get('message', 'No message')}")
        return success, response

    def test_privacy_leak_detection(self, stats_before, stats_after):
        """Test if privacy leak detection is working"""
        print(f"\n🔍 Testing Privacy Leak Detection Logic...")
        
        flows_before = stats_before.get('totalFlows', 0)
        leaks_before = stats_before.get('totalLeaks', 0)
        flows_after = stats_after.get('totalFlows', 0)
        leaks_after = stats_after.get('totalLeaks', 0)
        
        flows_added = flows_after - flows_before
        leaks_added = leaks_after - leaks_before
        
        print(f"   Flows added: {flows_added}")
        print(f"   Leaks added: {leaks_added}")
        
        if flows_added > 0:
            leak_rate = leaks_added / flows_added if flows_added > 0 else 0
            print(f"   Leak detection rate: {leak_rate:.2%}")
            
            if leak_rate > 0:
                print("✅ Privacy leak detection is working")
                return True
            else:
                print("⚠️  No leaks detected in new flows (might be normal)")
                return True
        else:
            print("⚠️  No new flows added")
            return False

def main():
    print("🚀 Starting Mobile Privacy Leakage Detector API Tests")
    print("=" * 60)
    
    tester = MobilePrivacyAPITester()
    
    # Test basic connectivity
    print("\n📡 Testing Basic Connectivity...")
    root_success, _ = tester.test_root_endpoint()
    if not root_success:
        print("❌ Cannot connect to backend. Stopping tests.")
        return 1

    # Test dashboard endpoints
    print("\n📊 Testing Dashboard Endpoints...")
    stats_success, stats_before = tester.test_dashboard_stats()
    flows_success, flows_data = tester.test_all_flows()
    leaks_success, leaks_data = tester.test_privacy_leaks()

    # Test mock data generation
    print("\n🎲 Testing Mock Data Generation...")
    mock_success, mock_response = tester.test_generate_mock_data()
    
    # Wait a moment for data to be processed
    import time
    time.sleep(2)
    
    # Test stats again to see if data was added
    print("\n🔄 Re-testing Dashboard Stats After Mock Data...")
    stats_success_after, stats_after = tester.test_dashboard_stats()
    
    # Test privacy leak detection logic
    if stats_success and stats_success_after:
        tester.test_privacy_leak_detection(stats_before, stats_after)

    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())