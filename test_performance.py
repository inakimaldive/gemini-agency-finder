#!/usr/bin/env python3
"""
Performance testing script for Gemini Agency Finder improvements
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemini_agency_finder import GeminiAgencyFinder

def test_performance_improvements():
    """Test the performance improvements made to the agency finder"""
    print("🧪 Testing Gemini Agency Finder Performance Improvements")
    print("=" * 60)

    finder = GeminiAgencyFinder()

    # Test 1: Calculate agencies per call
    print("\n📊 TEST 1: Agencies per API call calculation")
    print("-" * 40)
    metrics = finder.calculate_agencies_per_call()

    if metrics:
        print("✅ Performance metrics calculated successfully")
        print(f"   📈 Agencies per call: {metrics['agencies_per_call']}")
        print(f"   🎯 Daily potential: {metrics['daily_agency_potential']} agencies")
        print(f"   💰 Token efficiency: {metrics['total_tokens']} tokens/call")
    else:
        print("❌ Failed to calculate performance metrics")

    # Test 2: Test prompt optimization
    print("\n🤖 TEST 2: Prompt optimization validation")
    print("-" * 40)

    test_prompt = """Find up to 15 real estate agencies in Warsaw, Poland that specialize in Costa del Sol, Marbella, or international properties.

Focus on agencies with Polish connections to Marbella/Costa del Sol area. Include details about their Polish-Marbella connections in descriptions.

Return ONLY a JSON array with this exact format:
[{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in Warsaw", "description": "Polish agency specializing in Marbella properties"}]

If no agencies are found, return an empty array []. Do not include explanations or additional text."""

    print(f"📝 Testing optimized prompt ({len(test_prompt)} chars)...")
    response = finder.run_gemini_prompt(test_prompt)

    if response:
        print("✅ Optimized prompt working")
        agencies = finder.parse_agency_data(response, "Warsaw")
        print(f"   📊 Parsed {len(agencies)} agencies from response")

        if agencies:
            print("   🔍 Sample agency data:")
            for i, agency in enumerate(agencies[:2]):  # Show first 2
                print(f"      {i+1}. {agency['name']}")
                print(f"         📞 {agency.get('phone', 'No phone')}")
                print(f"         🌐 {agency.get('website', 'No website')}")
                print(f"         📝 {agency.get('description', 'No description')[:50]}...")
    else:
        print("❌ Optimized prompt failed")

    # Test 3: Polish connection details
    print("\n🇵🇱 TEST 3: Polish-Marbella connection details")
    print("-" * 40)

    if response and agencies:
        marbella_connections = 0
        for agency in agencies:
            desc = agency.get('description', '').lower()
            if any(term in desc for term in ['marbella', 'costa del sol', 'polish', 'spanish', 'international']):
                marbella_connections += 1

        print(f"✅ Agencies with Polish-Marbella connections: {marbella_connections}/{len(agencies)}")
        print("   📋 Connection details captured in descriptions")
    else:
        print("⚠️ No agencies to test connection details")

    print("\n🎉 Performance testing complete!")
    print("=" * 60)

if __name__ == '__main__':
    test_performance_improvements()
