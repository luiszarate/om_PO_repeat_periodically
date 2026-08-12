def migrate(cr, version):
    """Identify replicas created before the explicit marker was introduced."""
    cr.execute(
        """
        UPDATE purchase_order
           SET po_repeat_is_generated = TRUE
         WHERE po_repeat_origin_id IS NOT NULL
        """
    )
