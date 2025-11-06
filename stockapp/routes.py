from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func
from .models import StockItem
from . import db
from datetime import datetime

main = Blueprint("main", __name__)

@main.route("/")
def dashboard():
    return render_template("dashboard.html")

@main.route("/api/dashboard-metrics")
def dashboard_metrics():
    """Compute live dashboard metrics from stock data."""
    items = StockItem.query.all()

    total_items = len(items)
    low_stock = 0
    critical_stock = 0
    normal_stock = 0
    total_value = 0.0

    for item in items:
        status = (item.alarm_status or "").strip().lower()
        total_value += float(item.inward_total_price or 0)

        if status == "low stock":
            low_stock += 1
        elif status == "critical":
            critical_stock += 1
        else:
            normal_stock += 1

    return jsonify({
        "total_items": int(total_items),
        "normal_stock": int(normal_stock),
        "low_stock": int(low_stock),
        "critical_stock": int(critical_stock),
        "total_value": round(total_value, 2)
    })


@main.route("/inventory")
def inventory_page():
    """Renders the interactive inventory management dashboard."""
    return render_template("inventory.html")


@main.route("/api/inventory")
def inventory_api():
    """Returns all inventory items with computed values."""
    items = StockItem.query.all()
    computed = [item.compute_fields() for item in items]
    return jsonify(computed)

@main.route("/api/item/<int:item_id>")
def get_single_item(item_id):
    """Return one inventory item for live updates"""
    item = StockItem.query.get_or_404(item_id)
    return jsonify(item.compute_fields())

@main.route("/api/add", methods=["POST"])
def add_item():
    data = request.get_json()

    # ✅ Case 1: Bulk insert (list of items)
    if isinstance(data, list):
        items = []
        for entry in data:
            new_item = StockItem(
                item_code=entry.get("item_code"),
                item_description=entry.get("item_description"),
                inward_invoice_no=entry.get("inward_invoice_no"),
                inward_date=datetime.strptime(entry.get("inward_date"), "%Y-%m-%d").date() if entry.get("inward_date") else None,
                uom=entry.get("uom"),
                inward_qty=float(entry.get("inward_qty", 0)),
                inward_unit_price=float(entry.get("inward_unit_price", 0)),
                outward_qty=float(entry.get("outward_qty", 0)),
                outward_unit_price=float(entry.get("outward_unit_price", 0)),
                outward_invoice_no=entry.get("outward_invoice_no"),
                outward_date=datetime.strptime(entry.get("outward_date"), "%Y-%m-%d").date() if entry.get("outward_date") else None,
                eway_bill_number=entry.get("eway_bill_number"),
                vehicle_number=entry.get("vehicle_number"),
                po_number=entry.get("po_number"),
            )
            new_item.compute_fields()
            db.session.add(new_item)
            items.append(new_item)

        db.session.commit()
        return jsonify({"message": f"{len(items)} items added successfully"}), 201

    # ✅ Case 2: Single item
    elif isinstance(data, dict):
        new_item = StockItem(
            item_code=data.get("item_code"),
            item_description=data.get("item_description"),
            inward_invoice_no=data.get("inward_invoice_no"),
            inward_date=datetime.strptime(data.get("inward_date"), "%Y-%m-%d").date() if data.get("inward_date") else None,
            uom=data.get("uom"),
            inward_qty=float(data.get("inward_qty", 0)),
            inward_unit_price=float(data.get("inward_unit_price", 0)),
            outward_qty=float(data.get("outward_qty", 0)),
            outward_unit_price=float(data.get("outward_unit_price", 0)),
            outward_invoice_no=data.get("outward_invoice_no"),
            outward_date=datetime.strptime(data.get("outward_date"), "%Y-%m-%d").date() if data.get("outward_date") else None,
            eway_bill_number=data.get("eway_bill_number"),
            vehicle_number=data.get("vehicle_number"),
            po_number=data.get("po_number"),
        )

        new_item.compute_fields()
        db.session.add(new_item)
        db.session.commit()

        return jsonify({"message": "Item added successfully"}), 201

    # 🚫 Invalid format
    else:
        return jsonify({"error": "Invalid data format. Expected dict or list."}), 400


@main.route("/api/update/<int:item_id>", methods=["PUT", "PATCH"])
def update_item(item_id):
    """Update an existing stock item."""
    item = StockItem.query.get_or_404(item_id)
    data = request.json

    # Update fields
    item.item_code = data.get("item_code", item.item_code)
    item.item_description = data.get("item_description", item.item_description)
    item.inward_qty = float(data.get("inward_qty", item.inward_qty))
    item.inward_unit_price = float(data.get("inward_unit_price", item.inward_unit_price))
    item.outward_qty = float(data.get("outward_qty", item.outward_qty))
    item.outward_unit_price = float(data.get("outward_unit_price", item.outward_unit_price))
    item.uom = data.get("uom", item.uom)
    item.inward_date = datetime.strptime(data.get("inward_date"), "%Y-%m-%d").date() if data.get("inward_date") else item.inward_date
    item.outward_date = datetime.strptime(data.get("outward_date"), "%Y-%m-%d").date() if data.get("outward_date") else item.outward_date
    item.eway_bill_number = data.get("eway_bill_number", item.eway_bill_number)
    item.vehicle_number = data.get("vehicle_number", item.vehicle_number)
    item.po_number = data.get("po_number", item.po_number)

    # Recompute
    item.compute_fields()
    db.session.commit()

    return jsonify({"message": f"Item '{item.item_code}' updated successfully"}), 200


@main.route("/api/delete/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """Delete a stock item."""
    item = StockItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": f"Item '{item.item_code}' deleted successfully"}), 200