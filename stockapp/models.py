from . import db
from datetime import date

class StockItem(db.Model):
    __tablename__ = "stock_items"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(50), nullable=False)
    item_description = db.Column(db.String(255))
    inward_invoice_no = db.Column(db.String(100))
    inward_date = db.Column(db.Date, default=date.today)
    uom = db.Column(db.String(10))
    inward_qty = db.Column(db.Float, default=0)
    inward_unit_price = db.Column(db.Float, default=0)
    inward_total_price = db.Column(db.Float, default=0)
    outward_qty = db.Column(db.Float, default=0)
    balance_stock_qty = db.Column(db.Float, default=0)
    alarm_status = db.Column(db.String(20))
    outward_invoice_no = db.Column(db.String(100))
    outward_date = db.Column(db.Date)
    outward_unit_price = db.Column(db.Float, default=0)
    outward_total_price = db.Column(db.Float, default=0)
    eway_bill_number = db.Column(db.String(100))
    vehicle_number = db.Column(db.String(50))
    po_number = db.Column(db.String(100))

    def compute_fields(self):
        self.inward_total_price = (self.inward_qty or 0) * (self.inward_unit_price or 0)
        self.outward_total_price = (self.outward_qty or 0) * (self.outward_unit_price or 0)
        self.balance_stock_qty = (self.inward_qty or 0) - (self.outward_qty or 0)

        # Stock alarm logic
        if self.balance_stock_qty < (self.inward_qty * 0.6):
            self.alarm_status = "Critical"
        elif self.balance_stock_qty < (self.inward_qty * 0.8):
            self.alarm_status = "Low Stock"
        else:
            self.alarm_status = "Normal"

        return {
            "id": self.id,
            "item_code": self.item_code,
            "item_description": self.item_description,
            "inward_invoice_no": self.inward_invoice_no,
            "inward_date": self.inward_date,
            "uom": self.uom,
            "inward_qty": self.inward_qty,
            "inward_unit_price": self.inward_unit_price,
            "inward_total_price": self.inward_total_price,
            "outward_qty": self.outward_qty,
            "balance_stock_qty": self.balance_stock_qty,
            "alarm_status": self.alarm_status,
            "outward_invoice_no": self.outward_invoice_no,
            "outward_date": self.outward_date,
            "outward_unit_price": self.outward_unit_price,
            "outward_total_price": self.outward_total_price,
            "eway_bill_number": self.eway_bill_number,
            "vehicle_number": self.vehicle_number,
            "po_number": self.po_number,
        }
