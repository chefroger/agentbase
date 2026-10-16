"""订单 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException

from trade import order as order_module
from trade.api.deps import require_company
from trade.api.models import OrderCreate, OrderUpdate

router = APIRouter(tags=["orders"])


@router.get("/orders")
def list_orders(cid: int = Depends(require_company)):
    """列出当前公司的所有订单。"""
    return order_module.list_by_company(cid)


@router.get("/customers/{customer_id}/orders")
def list_customer_orders(customer_id: int, cid: int = Depends(require_company)):
    """列出指定客户的所有订单。"""
    from trade import customer as cust_module
    c = cust_module.get(customer_id, company_id=cid)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return order_module.list_by_customer(customer_id, company_id=cid)


@router.post("/orders")
def create_order(payload: OrderCreate, cid: int = Depends(require_company)):
    """创建订单。"""
    from trade import customer as cust_module
    c = cust_module.get(payload.customer_id, company_id=cid)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return order_module.create(
        company_id=cid,
        customer_id=payload.customer_id,
        product_name=payload.product_name,
        order_no=payload.order_no or "",
        quantity=payload.quantity or 0,
        unit=payload.unit or "",
        unit_price=payload.unit_price or 0,
        currency=payload.currency or "USD",
        total_amount=payload.total_amount or 0,
        status=payload.status or "报价中",
        delivery_date=payload.delivery_date or "",
        payment_terms=payload.payment_terms or "",
        notes=payload.notes or "",
    )


@router.get("/orders/{order_id}")
def get_order(order_id: int, cid: int = Depends(require_company)):
    """获取订单详情。"""
    o = order_module.get(order_id, company_id=cid)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return o


@router.put("/orders/{order_id}")
def update_order(order_id: int, payload: OrderUpdate, cid: int = Depends(require_company)):
    """更新订单。"""
    result = order_module.update(order_id, company_id=cid, **payload.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    return result


@router.delete("/orders/{order_id}")
def delete_order(order_id: int, cid: int = Depends(require_company)):
    """删除订单。"""
    if not order_module.delete(order_id, company_id=cid):
        raise HTTPException(status_code=404, detail="Order not found")
    return {"ok": True}


@router.post("/orders/{order_id}/libraries/{library_id}")
def link_order_library(order_id: int, library_id: int, cid: int = Depends(require_company)):
    """关联文档库到订单。"""
    if not order_module.link_library(order_id, library_id, company_id=cid):
        raise HTTPException(status_code=404, detail="Order or library not found")
    return {"ok": True}


@router.delete("/orders/{order_id}/libraries/{library_id}")
def unlink_order_library(order_id: int, library_id: int, cid: int = Depends(require_company)):
    """取消订单的文档库关联。"""
    if not order_module.unlink_library(order_id, library_id, company_id=cid):
        raise HTTPException(status_code=404, detail="Association not found")
    return {"ok": True}
