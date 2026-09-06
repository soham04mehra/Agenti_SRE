from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.payment_service import PaymentService
from services.order_service import OrderService

app = FastAPI(title="Agentic SRE Microservices API")

payment_service = PaymentService()
order_service = OrderService(payment_service=payment_service)

class PaymentRequest(BaseModel):
    user_id: str
    amount: float
    currency: str = "USD"

class OrderRequest(BaseModel):
    user_id: str
    item_id: str
    amount: float

class FaultRequest(BaseModel):
    fault_type: str | None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agentic SRE Microservices API is running"}

@app.post("/payments/process")
def process_payment(req: PaymentRequest):
    success = payment_service.process_payment(
        user_id=req.user_id,
        amount=req.amount,
        currency=req.currency
    )
    if not success:
        raise HTTPException(status_code=400, detail="Payment processing failed")
    return {"status": "success", "user_id": req.user_id, "amount": req.amount}

@app.post("/orders/create")
def create_order(req: OrderRequest):
    result = order_service.create_order(
        user_id=req.user_id,
        item_id=req.item_id,
        amount=req.amount
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/admin/inject")
def inject_fault(req: FaultRequest):
    order_service.set_fault_mode(req.fault_type)
    return {"status": "success", "active_fault": req.fault_type}
