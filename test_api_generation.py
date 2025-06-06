#!/usr/bin/env python3
"""
Test API Generation Demo

This script demonstrates how to convert enhanced UPnP profiles into REST APIs.
"""

import sys
import asyncio
import json
from pathlib import Path

# Add upnp_cli to path
sys.path.append('/Users/pentester/Tools/upnp-cli')

from upnp_cli.api_generator.profile_to_api import generate_profile_api
from upnp_cli.cli.output import ColoredOutput

async def main():
    """Demo the API generator on the Sonos profile."""
    
    print("🚀 Testing API Generator on Enhanced Sonos Profile")
    print("=" * 60)
    
    # Path to the enhanced Sonos profile
    profile_file = Path('enhanced_profiles/enhanced_profiles_20250605_200735_individual/Sonos,_Inc._Sonos_Port_147actions.json')
    
    if not profile_file.exists():
        print(f"❌ Profile file not found: {profile_file}")
        return
    
    # Output directory for generated API
    output_dir = Path('generated_apis')
    
    try:
        print(f"📁 Input: {profile_file}")
        print(f"📁 Output: {output_dir}")
        print()
        
        # Generate the API
        result = await generate_profile_api(profile_file, output_dir)
        
        print("✅ API Generation Complete!")
        print(f"Generated APIs: {len(result.get('generated_apis', []))}")
        
        for api in result.get('generated_apis', []):
            if 'error' not in api:
                print(f"  🎯 {api['device_name']}: {api['total_actions']} actions")
                print(f"     API: {api['api_file']}")
                print(f"     Docs: {api['doc_file']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 