import os
import asyncio
import logging
from metaapi_cloud_sdk import MetaApi
from typing import Dict, Any, Optional

logger = logging.getLogger("MT5_Execution")

class MT5Executor:
    def __init__(self):
        self.token = os.getenv("META_API_TOKEN")
        self.account_id = os.getenv("META_API_ACCOUNT_ID")
        self.enabled = os.getenv("TRADING_ENABLED", "false").lower() == "true"
        
        if not self.token or not self.account_id:
            logger.warning("⚠️ MetaApi credentials missing. Trading execution disabled.")
            self.enabled = False
            
        self.api = MetaApi(self.token) if self.token else None

    async def execute_trade(self, signal: Dict[str, Any]):
        """
        Sends a trade to MT5 via MetaApi.
        """
        if not self.enabled:
            logger.info("🚫 Trading is disabled in settings. Skipping execution.")
            return None

        if not self.api:
            logger.error("❌ MetaApi not initialized.")
            return None

        try:
            account = await self.api.metatrader_account_api.get_account(self.account_id)
            initial_state = account.state
            
            # Wait for account to be connected and synchronized
            if initial_state != 'DEPLOYED':
                logger.warning(f"⚠️ MT5 Account state is {initial_state}. Attempting to proceed anyway...")

            connection = account.get_rpc_connection()
            await connection.connect()
            await connection.wait_synchronization()

            symbol = "XAUUSD" # Gold on XM (Check if your broker uses XAUUSD or GOLD)
            
            # Convert direction
            action = 'ORDER_TYPE_BUY' if signal['direction'] == 'BUY' else 'ORDER_TYPE_SELL'
            
            # Risk Management: Lot Size (Demo default: 0.1)
            # You can later make this dynamic based on balance
            lot_size = float(os.getenv("DEFAULT_LOT_SIZE", "0.1"))
            
            logger.info(f"📤 Sending {signal['direction']} order to MT5: {lot_size} lots at {signal['entry_price']}")

            result = await connection.create_market_order(
                symbol, 
                action, 
                lot_size, 
                signal['sl'], 
                signal['tp'], 
                {'comment': 'GoldSignalBot-AI'}
            )

            logger.info(f"✅ Trade Executed Successfully! Ticket: {result.get('orderId')}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to execute trade on MT5: {e}")
            return None

def sync_execute_trade(signal: Dict[str, Any]):
    """Bridge for synchronous main.py"""
    executor = MT5Executor()
    if not executor.enabled:
        return None
    return asyncio.run(executor.execute_trade(signal))
