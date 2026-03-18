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
            
            # ========================
            # 🧠 SMART LOT SIZE ENGINE
            # ========================
            smart_lots_enabled = signal.get("smart_lots_enabled", False)
            risk_percentage = signal.get("risk_percentage", 1.0)
            
            if smart_lots_enabled:
                lot_size = await self.calculate_smart_lot_size(
                    connection=connection,
                    entry_price=signal['entry_price'],
                    sl_price=signal['sl'],
                    risk_percentage=risk_percentage
                )
                logger.info(f"🧠 Smart Lots: {risk_percentage}% risk → {lot_size} lots")
            else:
                # Fallback to static default
                lot_size = float(os.getenv("DEFAULT_LOT_SIZE", "0.1"))
                logger.info(f"📐 Static Lots: {lot_size} lots (Smart Lots disabled)")
            
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

    async def calculate_smart_lot_size(
        self,
        connection,
        entry_price: float,
        sl_price: float,
        risk_percentage: float = 1.0
    ) -> float:
        """
        Computes a dynamically safe lot size based on actual account balance.
        
        Formula:
            Risk Amount  = Balance * (risk_percentage / 100)
            Trade Distance = abs(Entry - SL)
            For XAUUSD: $1 move = $100 per standard lot
            Lot Size = Risk Amount / (Trade Distance * 100)
        """
        try:
            account_info = await connection.get_account_information()
            balance = account_info.get('balance', 0)

            if balance <= 0:
                logger.warning("⚠️ Balance is zero or unavailable, defaulting to 0.01 lots.")
                return 0.01

            risk_amount = balance * (risk_percentage / 100.0)
            trade_distance = abs(entry_price - sl_price)

            if trade_distance == 0:
                logger.warning("⚠️ SL distance is zero, defaulting to 0.01 lots.")
                return 0.01

            # For XAU/USD (Gold Spot): $1 move × 1 standard lot = $100
            raw_lot = risk_amount / (trade_distance * 100.0)

            # Clamp: min 0.01 micro lot, max 100 lots (broker safety)
            clamped_lot = max(0.01, min(100.0, raw_lot))
            # Round down to 2 decimal places
            final_lot = round(clamped_lot - 0.005, 2)
            final_lot = max(0.01, final_lot)  # ensure we never go below minimum

            logger.info(
                f"💰 Smart Lot Calc | Balance: ${balance:.2f} | "
                f"Risk {risk_percentage}% = ${risk_amount:.2f} | "
                f"Distance: ${trade_distance:.2f} | "
                f"Raw lot: {raw_lot:.4f} | Final lot: {final_lot}"
            )
            return final_lot

        except Exception as e:
            logger.error(f"❌ Smart lot calculation failed: {e}. Defaulting to 0.01.")
            return 0.01


def sync_execute_trade(signal: Dict[str, Any]):
    """Bridge for synchronous main.py"""
    executor = MT5Executor()
    if not executor.enabled:
        return None
    return asyncio.run(executor.execute_trade(signal))
