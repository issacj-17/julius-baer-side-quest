#!/usr/bin/env python3
"""Example: Async client with connection pooling and batch transfers."""
import asyncio
import time
from transfer_client import AsyncBankingClient, Config


async def main():
    """Demo async batch transfers with connection pooling."""
    print("\n🏦 Async Banking Client - Batch Transfer Demo\n")

    config = Config()
    transfers = [
        ("ACC1020", "ACC1021", 10.00),
        ("ACC1022", "ACC1023", 15.00),
        ("ACC1024", "ACC1025", 20.00),
        ("ACC1026", "ACC1027", 25.00),
        ("ACC1028", "ACC1029", 30.00),
    ]

    print(f"🚀 Executing {len(transfers)} concurrent transfers...")
    start_time = time.time()

    async with AsyncBankingClient(config) as client:
        results = await client.transfer_batch(transfers)

    elapsed = time.time() - start_time
    successful = sum(1 for r in results if r and r.get("status") == "SUCCESS")

    print(f"\n✅ Results:")
    print(f"   Successful: {successful}/{len(transfers)}")
    print(f"   Time: {elapsed:.2f}s ({elapsed/len(transfers):.3f}s per transfer)")
    print(f"\n✨ Connection pooling enables concurrent operations!\n")


if __name__ == "__main__":
    asyncio.run(main())
