#!/usr/bin/env python3
"""
Polymarket Arbitrage Detector
Finds arbitrage opportunities in binary markets

Run: python arbitrage_detector.py
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams
import time
from datetime import datetime

class ArbitrageDetector:
    def __init__(self):
        self.client = ClobClient("https://clob.polymarket.com")
        self.opportunities = []
    
    def check_binary_arbitrage(self, token_id_1, token_id_2, market_question):
        """
        In binary markets, YES + NO prices should sum to ~$1.00
        If they sum to less, there's an arbitrage opportunity
        """
        try:
            # Get prices for both outcomes
            yes_price = self.client.get_midpoint(token_id_1)
            no_price = self.client.get_midpoint(token_id_2)
            
            # Calculate price sum
            price_sum = yes_price + no_price
            
            # Arbitrage exists if sum < 1.00 (allowing for fees)
            # Using 0.98 threshold to account for transaction costs
            if price_sum < 0.98:
                profit_per_dollar = 1.0 - price_sum
                profit_percentage = profit_per_dollar * 100
                
                opportunity = {
                    'market': market_question,
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'price_sum': price_sum,
                    'profit_per_dollar': profit_per_dollar,
                    'profit_percentage': profit_percentage,
                    'timestamp': datetime.now()
                }
                
                return opportunity
        
        except Exception as e:
            # Skip markets with errors (might not have liquidity)
            pass
        
        return None
    
    def check_cross_market_arbitrage(self, markets):
        """
        Find arbitrage across different markets for the same event
        Example: "Trump wins election" vs "Biden wins election"
        """
        # This is more complex - would need to identify related markets
        # Left as an exercise for enhancement
        pass
    
    def scan_all_markets(self, limit=100):
        """Scan all markets for arbitrage opportunities"""
        print(f"🔍 Scanning {limit} markets for arbitrage opportunities...")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
        # Get markets
        markets_data = self.client.get_simplified_markets()
        markets = markets_data.get("data", [])[:limit]
        
        opportunities = []
        checked = 0
        
        for market in markets:
            # Only check active, non-closed markets
            if not market.get("active") or market.get("closed"):
                continue
            
            # Get token IDs
            token_ids_str = market.get("clobTokenIds", "")
            if not token_ids_str:
                continue
            
            token_ids = token_ids_str.split(",")
            
            # Only check binary markets (2 outcomes)
            if len(token_ids) != 2:
                continue
            
            checked += 1
            
            # Check for arbitrage
            opportunity = self.check_binary_arbitrage(
                token_ids[0], 
                token_ids[1], 
                market["question"]
            )
            
            if opportunity:
                opportunities.append(opportunity)
                self.print_opportunity(opportunity)
            
            # Progress indicator
            if checked % 10 == 0:
                print(f"Checked {checked} markets...", end='\r')
        
        print(f"\n{'-' * 80}")
        print(f"✅ Scan complete!")
        print(f"   Checked: {checked} binary markets")
        print(f"   Opportunities found: {len(opportunities)}")
        print(f"   Hit rate: {len(opportunities)/checked*100:.1f}%" if checked > 0 else "")
        
        return opportunities
    
    def print_opportunity(self, opp):
        """Print arbitrage opportunity details"""
        print(f"\n💰 ARBITRAGE OPPORTUNITY FOUND!")
        print(f"   Market: {opp['market'][:70]}")
        print(f"   YES price: ${opp['yes_price']:.4f}")
        print(f"   NO price:  ${opp['no_price']:.4f}")
        print(f"   Sum:       ${opp['price_sum']:.4f}")
        print(f"   ✨ Profit:  ${opp['profit_per_dollar']:.4f} per $1 invested ({opp['profit_percentage']:.2f}%)")
        print(f"   Time: {opp['timestamp'].strftime('%H:%M:%S')}")
        print("-" * 80)
    
    def monitor_continuous(self, interval=60):
        """Continuously monitor for arbitrage opportunities"""
        print("🔄 Starting continuous monitoring...")
        print(f"   Scanning every {interval} seconds")
        print(f"   Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                opportunities = self.scan_all_markets(limit=50)
                
                if opportunities:
                    print(f"\n📊 Summary: {len(opportunities)} opportunities found")
                    for opp in opportunities[:3]:  # Show top 3
                        print(f"   • {opp['market'][:60]} - {opp['profit_percentage']:.2f}% profit")
                
                print(f"\nNext scan in {interval}s...")
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped")

def calculate_optimal_bet(yes_price, no_price, total_investment=100):
    """
    Calculate optimal bet sizes for arbitrage
    
    Strategy: Buy both YES and NO at current prices
    One will pay $1, the other $0
    Profit = $1 - (yes_price + no_price)
    """
    cost = yes_price + no_price
    
    if cost >= 1.0:
        return None
    
    # Buy 1 share of each
    yes_cost = yes_price * 1
    no_cost = no_price * 1
    total_cost = yes_cost + no_cost
    
    # Payout is always $1 (one outcome wins)
    payout = 1.0
    profit = payout - total_cost
    profit_percentage = (profit / total_cost) * 100
    
    # Scale to desired investment
    num_contracts = total_investment / total_cost
    scaled_profit = profit * num_contracts
    
    return {
        'yes_cost': yes_cost,
        'no_cost': no_cost,
        'total_cost': total_cost,
        'payout': payout,
        'profit_per_contract': profit,
        'profit_percentage': profit_percentage,
        'contracts_for_investment': num_contracts,
        'scaled_profit': scaled_profit
    }

def main():
    detector = ArbitrageDetector()
    
    print("=" * 80)
    print("POLYMARKET ARBITRAGE DETECTOR")
    print("=" * 80)
    print()
    print("Options:")
    print("1. Single scan (check all markets once)")
    print("2. Continuous monitoring (scan every 60s)")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        opportunities = detector.scan_all_markets(limit=100)
        
        if opportunities:
            print("\n📈 BEST OPPORTUNITIES:")
            # Sort by profit percentage
            sorted_opps = sorted(opportunities, 
                                key=lambda x: x['profit_percentage'], 
                                reverse=True)
            
            for i, opp in enumerate(sorted_opps[:5], 1):
                print(f"\n{i}. {opp['market'][:70]}")
                print(f"   Profit: {opp['profit_percentage']:.2f}%")
                
                # Calculate optimal bet
                bet = calculate_optimal_bet(
                    opp['yes_price'], 
                    opp['no_price'], 
                    total_investment=100
                )
                
                if bet:
                    print(f"   Example: Invest $100 → Profit ${bet['scaled_profit']:.2f}")
        else:
            print("\n❌ No arbitrage opportunities found at this time")
            print("   Tip: Arbitrage in prediction markets is rare and quickly exploited")
    
    elif choice == "2":
        detector.monitor_continuous(interval=60)
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except ImportError:
        print("❌ ERROR: py-clob-client not installed")
        print()
        print("Install it with:")
        print("   pip install py-clob-client")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
