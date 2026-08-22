import httpx
from app.core.config import settings

class RazorpayService:
    def __init__(self):
        self.auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        self.base_url = "https://api.razorpay.com/v1"

    def create_payment_link(self, amount: int, customer_email: str, customer_phone: str):
        if not settings.RAZORPAY_KEY_ID:
            return {"id": "mock_link_123", "short_url": "https://rzp.io/mock123", "status": "created"}
        
        payload = {
            "amount": int(amount * 100),
            "currency": "INR",
            "customer": {
                "email": customer_email,
                "contact": customer_phone
            },
            "reference_id": "recoverai_ref_123"
        }
        try:
            response = httpx.post(f"{self.base_url}/payment_links", json=payload, auth=self.auth)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

razorpay_service = RazorpayService()
