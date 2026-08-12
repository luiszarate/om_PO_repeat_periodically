{
    "name": "Purchase Order Periodic Repetition",
    "summary": "Create draft purchase orders periodically from a source order",
    "version": "14.0.1.1.0",
    "category": "Purchases",
    "author": "Imago",
    "license": "LGPL-3",
    "depends": ["purchase"],
    "data": [
        "data/ir_cron.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
