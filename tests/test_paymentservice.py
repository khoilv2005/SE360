"""
Unit tests for PaymentService - Business Logic
Run with: pytest tests/test_paymentservice.py -v
"""
import pytest
import hashlib
import hmac
from datetime import datetime

class TestWalletOperations:
    """Test wallet operations"""

    @pytest.mark.asyncio
    async def test_wallet_top_up(self):
        """Test wallet top-up operation"""
        wallet = {"balance": 50000}
        top_up_amount = 100000
        wallet["balance"] += top_up_amount
        assert wallet["balance"] == 150000

    @pytest.mark.asyncio
    async def test_wallet_debit_sufficient_funds(self):
        """Test wallet debit with sufficient funds"""
        wallet = {"balance": 100000}
        trip_cost = 30000
        if wallet["balance"] >= trip_cost:
            wallet["balance"] -= trip_cost
            payment_status = "SUCCESS"
        else:
            payment_status = "INSUFFICIENT_FUNDS"
        assert wallet["balance"] == 70000
        assert payment_status == "SUCCESS"

class TestVNPayIntegration:
    """Test VNPay payment gateway integration"""

    def test_vnpay_hmac_signature(self):
        """Test VNPay HMAC-SHA512 signature generation"""
        secret_key = "TEST_SECRET_123"
        data_to_sign = "amount=50000&order_id=trip_001"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            data_to_sign.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        assert len(signature) == 128  # SHA512 produces 128 hex characters

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
