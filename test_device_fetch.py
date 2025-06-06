#!/usr/bin/env python3
import asyncio
import aiohttp
import sys
import upnp_cli.discovery as discovery

async def test_device_fetch():
    print("Testing device description fetch...")
    
    url = 'http://192.168.4.152:1400/xml/device_description.xml'
    print(f"URL: {url}")
    
    async with aiohttp.ClientSession() as session:
        result = await discovery.fetch_device_description(session, url)
        
    print(f"Result type: {type(result)}")
    
    if result:
        print(f"Result keys: {list(result.keys())}")
        print(f"Manufacturer: {result.get('manufacturer', 'Not found')}")
        print(f"Model: {result.get('modelName', 'Not found')}")
        print(f"Services count: {len(result.get('services', []))}")
        print(f"IP: {result.get('ip', 'Not found')}")
        print(f"Port: {result.get('port', 'Not found')}")
    else:
        print("Result is None!")

if __name__ == "__main__":
    asyncio.run(test_device_fetch()) 