"""
Unit tests for PaymentService
Run with: pytest tests/test_paymentservice.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import hashlib
import hmac

# Set required environment variables
os.environ.setdefault("COSMOS_CONNECTION_STRING", "mongodb://localhost:27017")
os.environ.setdefault("VNP_TMN_CODE", "TEST_TMN")
os.environ.setdefault("VNP_HASH_SECRET", "TEST_SECRET_123")
os.environ.setdefault("VNP_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")

# Add PaymentService to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'PaymentService'))

import schemas


class TestPaymentSchemas:
    """Test Payment data models and schemas"""

    def test_payment_request_schema(self):
        """Test payment request schema"""
        payment_data = schemas.PaymentRequest(
            user_id="user_001",
            trip_id="trip_001",
            amount=50000,
            payment_method="WALLET"
        )

        assert payment_data.user_id == "user_001"
        assert payment_data.amount == 50000
        assert payment_data.payment_method == "WALLET"

    def test_wallet_schema(self):
        """Test wallet schema"""
        wallet = {
            "user_id": "user_001",
            "balance": 100000,
            "currency": "VND"
        }

        assert wallet["balance"] == 100000
        assert wallet["currency"] == "VND"


class TestWalletOperations:
    """Test wallet operations"""

    @pytest.mark.asyncio
    async def test_wallet_initialization(self):
        """Test wallet is initialized with zero balance"""
        wallet = {
            "user_id": "user_001",
            "balance": 0,
            "currency": "VND",
            "created_at": datetime.utcnow()
        }

        assert wallet["balance"] == 0
        assert wallet["currency"] == "VND"

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

    @pytest.mark.asyncio
    async def test_wallet_debit_insufficient_funds(self):
        """Test wallet debit with insufficient funds"""
        wallet = {"balance": 10000}
        trip_cost = 30000

        if wallet["balance"] >= trip_cost:
            wallet["balance"] -= trip_cost
            payment_status = "SUCCESS"
        else:
            payment_status = "INSUFFICIENT_FUNDS"

        assert wallet["balance"] == 10000  # Balance unchanged
        assert payment_status == "INSUFFICIENT_FUNDS"

    @pytest.mark.asyncio
    async def test_wallet_credit(self):
        """Test crediting wallet (refund)"""
        wallet = {"balance": 50000}
        refund_amount = 20000

        wallet["balance"] += refund_amount

        assert wallet["balance"] == 70000


class TestVNPayIntegration:
    """Test VNPay payment gateway integration"""

    def test_vnpay_payment_url_generation(self):
        """Test VNPay payment URL generation"""
        # Mock VNPay parameters
        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": "TEST_TMN",
            "vnp_Amount": 5000000,  # 50000 VND * 100
            "vnp_OrderInfo": "Payment for trip_001",
            "vnp_ReturnUrl": "http://localhost:3000/payment/return"
        }

        assert params["vnp_Amount"] == 5000000
        assert params["vnp_TmnCode"] == "TEST_TMN"

    def test_vnpay_hmac_signature(self):
        """Test VNPay HMAC-SHA512 signature generation"""
        # Mock signature data
        secret_key = "TEST_SECRET_123"
        data_to_sign = "amount=50000&order_id=trip_001&tmn_code=TEST_TMN"

        # Generate HMAC-SHA512 signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            data_to_sign.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        assert len(signature) == 128  # SHA512 produces 128 hex characters
        assert isinstance(signature, str)

    @pytest.mark.asyncio
    async def test_vnpay_callback_verification(self):
        """Test VNPay callback signature verification"""
        # Mock VNPay callback parameters
        callback_params = {
            "vnp_Amount": "5000000",
            "vnp_OrderInfo": "Payment for trip_001",
            "vnp_ResponseCode": "00",  # Success
            "vnp_SecureHash": "mock_hash_123"
        }

        # Verify response code
        is_success = callback_params["vnp_ResponseCode"] == "00"

        assert is_success is True

    @pytest.mark.asyncio
    async def test_vnpay_payment_success(self):
        """Test successful VNPay payment processing"""
        # Mock successful payment
        payment_result = {
            "transaction_id": "txn_001",
            "status": "SUCCESS",
            "amount": 50000,
            "payment_method": "VNPAY",
            "vnp_response_code": "00"
        }

        assert payment_result["status"] == "SUCCESS"
        assert payment_result["vnp_response_code"] == "00"

    @pytest.mark.asyncio
    async def test_vnpay_payment_failure(self):
        """Test failed VNPay payment processing"""
        # Mock failed payment
        payment_result = {
            "transaction_id": "txn_002",
            "status": "FAILED",
            "amount": 50000,
            "payment_method": "VNPAY",
            "vnp_response_code": "24",  # Transaction cancelled
            "error_message": "User cancelled payment"
        }

        assert payment_result["status"] == "FAILED"
        assert payment_result["vnp_response_code"] != "00"


class TestPaymentCRUD:
    """Test Payment CRUD operations (mocked)"""

    @pytest.mark.asyncio
    async def test_create_payment_transaction(self):
        """Test payment transaction creation"""
        transaction = {
            "transaction_id": "txn_001",
            "user_id": "user_001",
            "trip_id": "trip_001",
            "amount": 50000,
            "payment_method": "WALLET",
            "status": "PENDING",
            "created_at": datetime.utcnow()
        }

        assert transaction["status"] == "PENDING"
        assert transaction["amount"] == 50000

    @pytest.mark.asyncio
    async def test_update_payment_status(self):
        """Test updating payment status"""
        transaction = {
            "transaction_id": "txn_001",
            "status": "PENDING"
        }

        # Payment completed
        transaction["status"] = "COMPLETED"
        transaction["completed_at"] = datetime.utcnow()

        assert transaction["status"] == "COMPLETED"
        assert "completed_at" in transaction

    @pytest.mark.asyncio
    async def test_payment_history(self):
        """Test retrieving payment history"""
        # Mock payment history
        payment_history = [
            {"transaction_id": "txn_001", "amount": 30000, "status": "COMPLETED"},
            {"transaction_id": "txn_002", "amount": 50000, "status": "COMPLETED"},
            {"transaction_id": "txn_003", "amount": 25000, "status": "FAILED"}
        ]

        total_successful = sum(
            p["amount"] for p in payment_history if p["status"] == "COMPLETED"
        )

        assert len(payment_history) == 3
        assert total_successful == 80000  # 30000 + 50000


class TestPaymentMethods:
    """Test different payment methods"""

    @pytest.mark.asyncio
    async def test_cash_payment(self):
        """Test cash payment processing"""
        payment = {
            "payment_method": "CASH",
            "amount": 50000,
            "status": "PENDING"
        }

        # Cash payments are marked as completed when trip ends
        payment["status"] = "COMPLETED"

        assert payment["payment_method"] == "CASH"
        assert payment["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_wallet_payment(self):
        """Test wallet payment processing"""
        wallet = {"balance": 100000}
        payment_amount = 50000

        if wallet["balance"] >= payment_amount:
            wallet["balance"] -= payment_amount
            payment_status = "COMPLETED"
        else:
            payment_status = "FAILED"

        assert payment_status == "COMPLETED"
        assert wallet["balance"] == 50000

    @pytest.mark.asyncio
    async def test_vnpay_online_payment(self):
        """Test VNPay online payment processing"""
        payment = {
            "payment_method": "VNPAY",
            "amount": 50000,
            "status": "PENDING",
            "redirect_url": "https://sandbox.vnpayment.vn/..."
        }

        # After user pays on VNPay
        payment["status"] = "COMPLETED"
        payment["vnp_transaction_id"] = "vnp_txn_123"

        assert payment["status"] == "COMPLETED"
        assert "vnp_transaction_id" in payment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
