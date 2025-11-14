from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func
from .models import StockItem
from . import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, cast, String

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
    """
    Return inventory items with optional:
    - status filter
    - Full-table dynamic search
    - pagination (page + limit)

    New Usage:
      /api/inventory?page=1&limit=50
      /api/inventory?status=low&page=2
      /api/inventory?search=bolt
    """

    # -------------------------------
    # Read & Normalize Query Params
    # -------------------------------
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))

    requested_status = (request.args.get("status") or "").strip().lower()
    search = (request.args.get("search") or "").strip().lower()

    # -------------------------------
    # Map allowed status filters
    # -------------------------------
    status_map = {
        "normal": "Normal",
        "low": "Low Stock",
        "critical": "Critical"
    }

    try:
        # -------------------------------
        # Start base query
        # -------------------------------
        query = StockItem.query

        # -------------------------------
        # Apply status filter (old behavior)
        # -------------------------------
        if requested_status:
            if requested_status not in status_map:
                return jsonify({
                    "error": "Invalid status filter. Use 'normal', 'low', or 'critical'."
                }), 400

            query = query.filter(
                StockItem.alarm_status == status_map[requested_status]
            )

        # ------------------------------------
        # FULL-TABLE SEARCH (all columns)
        # ------------------------------------
        if search:
            search_filter = or_(
                StockItem.item_code.ilike(f"%{search}%"),
                StockItem.item_description.ilike(f"%{search}%"),

                StockItem.inward_invoice_no.ilike(f"%{search}%"),
                StockItem.inward_date.ilike(f"%{search}%"),
                StockItem.uom.ilike(f"%{search}%"),
                cast(StockItem.inward_qty, String).ilike(f"%{search}%"),
                cast(StockItem.inward_unit_price, String).ilike(f"%{search}%"),
                cast(StockItem.inward_total_price, String).ilike(f"%{search}%"),

                cast(StockItem.outward_qty, String).ilike(f"%{search}%"),
                cast(StockItem.balance_stock_qty, String).ilike(f"%{search}%"),

                StockItem.alarm_status.ilike(f"%{search}%"),

                StockItem.outward_invoice_no.ilike(f"%{search}%"),
                StockItem.outward_date.ilike(f"%{search}%"),
                cast(StockItem.outward_unit_price, String).ilike(f"%{search}%"),
                cast(StockItem.outward_total_price, String).ilike(f"%{search}%"),

                StockItem.eway_bill_number.ilike(f"%{search}%"),
                StockItem.vehicle_number.ilike(f"%{search}%"),
                StockItem.po_number.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # -------------------------------
        # Count BEFORE pagination
        # -------------------------------
        total_items = query.count()

        # -------------------------------
        # Apply pagination
        # -------------------------------
        items = (
            query.order_by(StockItem.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        # -------------------------------
        # Compute all item fields (existing feature)
        # -------------------------------
        computed_items = [item.compute_fields() for item in items]

        # -------------------------------
        # Final paginated response
        # -------------------------------
        return jsonify({
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": (total_items + limit - 1) // limit,
            "items": computed_items
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to fetch inventory.",
            "detail": str(e)
        }), 500


@main.route("/api/item/<int:item_id>")
def get_single_item(item_id):
    """Return one inventory item for live updates"""
    item = StockItem.query.get_or_404(item_id)
    return jsonify(item.compute_fields())

# ✅ Improved Add Item route
@main.route("/api/add", methods=["POST"])
def add_item():
    """Add one or more new inventory items safely."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload."}), 400

    # Helper to safely parse date strings
    def parse_date(val):
        if not val:
            return None
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except Exception:
            return None

    def create_item(entry):
        """Create a StockItem from dict, computing all values."""
        return StockItem(
            item_code=(entry.get("item_code") or "").strip(),
            item_description=entry.get("item_description"),
            inward_invoice_no=entry.get("inward_invoice_no"),
            inward_date=parse_date(entry.get("inward_date")),
            uom=entry.get("uom"),
            inward_qty=float(entry.get("inward_qty") or 0),
            inward_unit_price=float(entry.get("inward_unit_price") or 0),
            outward_qty=float(entry.get("outward_qty") or 0),
            outward_unit_price=float(entry.get("outward_unit_price") or 0),
            outward_invoice_no=entry.get("outward_invoice_no"),
            outward_date=parse_date(entry.get("outward_date")),
            eway_bill_number=entry.get("eway_bill_number"),
            vehicle_number=entry.get("vehicle_number"),
            po_number=entry.get("po_number"),
        )

    try:
        # ✅ Bulk insert
        if isinstance(data, list):
            if not data:
                return jsonify({"error": "Empty list provided."}), 400

            items = []
            for entry in data:
                if not entry.get("item_code"):
                    return jsonify({"error": "Each entry must have an 'item_code'."}), 400
                item = create_item(entry)
                item.compute_fields()
                db.session.add(item)
                items.append(item)
            db.session.commit()
            return jsonify({"message": f"{len(items)} items added successfully."}), 201

        # ✅ Single insert
        elif isinstance(data, dict):
            if not data.get("item_code"):
                return jsonify({"error": "Field 'item_code' is required."}), 400
            new_item = create_item(data)
            new_item.compute_fields()
            db.session.add(new_item)
            db.session.commit()
            return jsonify({
                "message": "Item added successfully.",
                "item": new_item.compute_fields()
            }), 201

        else:
            return jsonify({"error": "Invalid data format. Expected dict or list."}), 400

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate item_code. Must be unique."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add item.", "detail": str(e)}), 500


# ✅ Improved Update Item route
@main.route("/api/update/<int:item_id>", methods=["PUT", "PATCH"])
def update_item(item_id):
    """Update an existing stock item safely."""
    item = StockItem.query.get_or_404(item_id)
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Invalid JSON payload."}), 400

    def parse_date(val):
        if not val:
            return None
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except Exception:
            return None

    try:
        # ✅ Update only allowed fields if provided
        for field in [
            "item_code", "item_description", "inward_invoice_no", "uom",
            "eway_bill_number", "vehicle_number", "po_number",
            "outward_invoice_no"
        ]:
            if field in data:
                setattr(item, field, data.get(field))

        if "inward_qty" in data:
            item.inward_qty = float(data.get("inward_qty") or 0)
        if "inward_unit_price" in data:
            item.inward_unit_price = float(data.get("inward_unit_price") or 0)
        if "outward_qty" in data:
            item.outward_qty = float(data.get("outward_qty") or 0)
        if "outward_unit_price" in data:
            item.outward_unit_price = float(data.get("outward_unit_price") or 0)
        if "inward_date" in data:
            item.inward_date = parse_date(data.get("inward_date"))
        if "outward_date" in data:
            item.outward_date = parse_date(data.get("outward_date"))

        item.compute_fields()
        db.session.commit()

        return jsonify({
            "message": f"Item '{item.item_code}' updated successfully.",
            "item": item.compute_fields()
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate item_code. Must be unique."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update item.", "detail": str(e)}), 500

@main.route("/api/delete/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """Delete a stock item."""
    item = StockItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": f"Item '{item.item_code}' deleted successfully"}), 200