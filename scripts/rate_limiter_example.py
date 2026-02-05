#!/usr/bin/env python3
"""Example usage of AdaptiveRateLimiter in Polymarket bot"""

import asyncio
from web3 import Web3
from rate_limiter import AdaptiveRateLimiter

# Initialize rate limiter
limiter = AdaptiveRateLimiter(db_path='rate_limits.db', provider='polygon-rpc')

# Example Web3 setup
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))


async def get_latest_block_safe():
    """Get latest block with rate limiting"""
    await limiter.acquire()  # Wait if needed
    return w3.eth.block_number


async def get_transaction_receipt_safe(tx_hash):
    """Get transaction receipt with rate limiting and error handling"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await limiter.acquire()  # Wait if needed
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            return receipt
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if 'Too many requests' in error_msg or 'rate limit' in error_msg.lower():
                # Extract retry time (default to 10s if not found)
                retry_seconds = 10
                if 'retry in' in error_msg:
                    # Parse "retry in 10s" or "retry in 10m0s"
                    import re
                    match = re.search(r'retry in (\d+)([ms])', error_msg)
                    if match:
                        value = int(match.group(1))
                        unit = match.group(2)
                        retry_seconds = value * 60 if unit == 'm' else value
                
                # Record the error for learning
                limiter.record_rate_limit_error(retry_seconds)
                
                # Wait before retrying
                print(f"Rate limited! Waiting {retry_seconds}s before retry...")
                await asyncio.sleep(retry_seconds)
                retry_count += 1
                
            else:
                # Some other error, re-raise
                raise
    
    raise Exception(f"Failed after {max_retries} retries due to rate limiting")


async def monitor_wallet_safe(wallet_address, from_block, to_block):
    """Monitor wallet activity with rate limiting"""
    # This would normally fetch logs - each call needs rate limiting
    
    # Get current block first
    await limiter.acquire()
    current_block = w3.eth.block_number
    
    print(f"Monitoring wallet {wallet_address} from block {from_block} to {to_block}")
    print(f"Current block: {current_block}")
    
    # Fetch logs with rate limiting
    chunk_size = 1000  # Process in chunks to avoid "block range too large" error
    
    for start in range(from_block, to_block, chunk_size):
        end = min(start + chunk_size - 1, to_block)
        
        # Rate limit BEFORE the call
        await limiter.acquire()
        
        print(f"Fetching logs for blocks {start} to {end}...")
        # logs = w3.eth.get_logs({...})  # Actual log fetching would go here
        
        # Add a small delay between chunks
        await asyncio.sleep(0.1)
    
    # Show stats
    stats = limiter.get_stats()
    print(f"\nRate limiter stats:")
    print(f"  Max calls/sec: {stats['max_calls_per_second']}")
    print(f"  Delay between calls: {stats['delay_ms']}ms")
    print(f"  Calls in last second: {stats['recent_calls']}")


async def main():
    """Example main function"""
    print("=== AdaptiveRateLimiter Example ===\n")
    
    # Example 1: Get latest block
    block_num = await get_latest_block_safe()
    print(f"Latest block: {block_num}\n")
    
    # Example 2: Monitor a wallet
    await monitor_wallet_safe(
        wallet_address="0x0000000000000000000000000000000000000000",
        from_block=block_num - 100,
        to_block=block_num
    )


if __name__ == '__main__':
    asyncio.run(main())
