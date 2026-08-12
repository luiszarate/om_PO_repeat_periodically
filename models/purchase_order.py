import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    _PO_REPEAT_AUTOMATIC_FIELDS = {
        "id",
        "create_date",
        "create_uid",
        "write_date",
        "write_uid",
        "__last_update",
    }
    _PO_REPEAT_ORDER_EXCLUDED_FIELDS = _PO_REPEAT_AUTOMATIC_FIELDS | {
        "name",
        "state",
        "date_order",
        "date_approve",
        "order_line",
        "po_repeat_active",
        "po_repeat_interval",
        "po_repeat_unit",
        "po_repeat_next_date",
        "po_repeat_origin_id",
        "po_repeat_generated_ids",
        "po_repeat_generated_count",
        "po_repeat_is_generated",
    }
    _PO_REPEAT_LINE_EXCLUDED_FIELDS = _PO_REPEAT_AUTOMATIC_FIELDS | {
        "order_id",
        "state",
    }

    po_repeat_active = fields.Boolean(
        string="Repeat periodically",
        copy=False,
        tracking=True,
    )
    po_repeat_interval = fields.Integer(
        string="Repeat every",
        default=1,
        required=True,
        copy=False,
    )
    po_repeat_unit = fields.Selection(
        selection=[
            ("day", "Day(s)"),
            ("week", "Week(s)"),
            ("month", "Month(s)"),
            ("year", "Year(s)"),
        ],
        string="Period",
        default="month",
        required=True,
        copy=False,
    )
    po_repeat_next_date = fields.Date(
        string="Next creation date",
        copy=False,
        tracking=True,
        index=True,
    )
    po_repeat_origin_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Recurring source order",
        readonly=True,
        copy=False,
        index=True,
        ondelete="set null",
    )
    po_repeat_is_generated = fields.Boolean(
        string="Generated recurring instance",
        default=False,
        readonly=True,
        copy=False,
        index=True,
        help=(
            "Identifies orders created automatically or manually from a "
            "recurring source."
        ),
    )
    po_repeat_generated_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="po_repeat_origin_id",
        string="Generated orders",
        readonly=True,
    )
    po_repeat_generated_count = fields.Integer(
        string="Generated orders count",
        compute="_compute_po_repeat_generated_count",
    )

    @api.depends("po_repeat_generated_ids")
    def _compute_po_repeat_generated_count(self):
        grouped_data = self.env["purchase.order"].read_group(
            [("po_repeat_origin_id", "in", self.ids)],
            ["po_repeat_origin_id"],
            ["po_repeat_origin_id"],
        )
        counts = {
            item["po_repeat_origin_id"][0]: item["po_repeat_origin_id_count"]
            for item in grouped_data
        }
        for order in self:
            order.po_repeat_generated_count = counts.get(order.id, 0)

    @api.constrains(
        "po_repeat_active",
        "po_repeat_interval",
        "po_repeat_next_date",
        "po_repeat_origin_id",
        "po_repeat_is_generated",
    )
    def _check_po_repeat_configuration(self):
        for order in self:
            if order.po_repeat_interval <= 0:
                raise ValidationError(
                    _("The repetition interval must be greater than zero.")
                )
            if order.po_repeat_active and not order.po_repeat_next_date:
                raise ValidationError(
                    _("Set the next creation date before enabling repetition.")
                )
            if order.po_repeat_active and (
                order.po_repeat_is_generated or order.po_repeat_origin_id
            ):
                raise ValidationError(
                    _("An order generated from another order cannot be repeated again.")
                )

    def _po_repeat_get_next_date(self, current_date):
        self.ensure_one()
        interval = self.po_repeat_interval
        if self.po_repeat_unit == "day":
            return current_date + relativedelta(days=interval)
        if self.po_repeat_unit == "week":
            return current_date + relativedelta(weeks=interval)
        if self.po_repeat_unit == "month":
            return current_date + relativedelta(months=interval)
        return current_date + relativedelta(years=interval)

    @api.model
    def _po_repeat_get_required_fields(self, record, excluded_fields=None):
        """Return required, writable input fields, including fields from custom addons."""
        excluded_fields = set(excluded_fields or ())
        return {
            field_name
            for field_name, field in record._fields.items()
            if field.required
            and field_name not in excluded_fields
            and not field.compute
            and not field.related
        }

    @api.model
    def _po_repeat_convert_field_value(self, record, field_name):
        field = record._fields[field_name]
        value = record[field_name]
        if field.type == "many2one":
            return value.id
        if field.type == "many2many":
            return [(6, 0, value.ids)]
        if field.type == "one2many":
            commands = []
            child_excluded_fields = self._PO_REPEAT_AUTOMATIC_FIELDS | {
                field.inverse_name
            }
            for child in value:
                child_fields = self._po_repeat_get_required_fields(
                    child, child_excluded_fields
                )
                child_values = self._po_repeat_copy_existing_fields(
                    child, child_fields
                )
                commands.append((0, 0, child_values))
            return commands
        if field.type == "reference":
            return "%s,%s" % (value._name, value.id) if value else False
        return value

    @api.model
    def _po_repeat_copy_existing_fields(self, record, allowed_fields):
        """Serialize allow-listed fields that exist in the current Odoo database."""
        values = {}
        for field_name in allowed_fields:
            field = record._fields.get(field_name)
            if not field:
                continue
            values[field_name] = self._po_repeat_convert_field_value(
                record, field_name
            )
        return values

    def _po_repeat_prepare_order_values(self, scheduled_date):
        self.ensure_one()
        order_fields = {
            "priority",
            "company_id",
            "partner_id",
            "partner_ref",
            "currency_id",
            "user_id",
            "picking_type_id",
            "dest_address_id",
            "fiscal_position_id",
            "payment_term_id",
            "notes",
            "incoterm_id",
        }
        order_fields |= self._po_repeat_get_required_fields(
            self, self._PO_REPEAT_ORDER_EXCLUDED_FIELDS
        )
        line_fields = {
            "sequence",
            "display_type",
            "product_id",
            "name",
            "product_qty",
            "product_uom",
            "price_unit",
            "taxes_id",
            "account_analytic_id",
            "analytic_tag_ids",
        }

        values = self._po_repeat_copy_existing_fields(self, order_fields)
        values.update(
            {
                "date_order": fields.Datetime.to_datetime(scheduled_date),
                "origin": self.name,
                "po_repeat_origin_id": self.id,
                "po_repeat_is_generated": True,
                "po_repeat_active": False,
                "order_line": [],
            }
        )

        source_order_date = fields.Datetime.to_datetime(self.date_order)
        scheduled_datetime = fields.Datetime.to_datetime(scheduled_date)
        for line in self.order_line:
            fields_to_copy = line_fields | self._po_repeat_get_required_fields(
                line, self._PO_REPEAT_LINE_EXCLUDED_FIELDS
            )
            line_values = self._po_repeat_copy_existing_fields(
                line, fields_to_copy
            )
            if line.date_planned:
                planned_delta = (
                    fields.Datetime.to_datetime(line.date_planned)
                    - source_order_date
                )
                line_values["date_planned"] = scheduled_datetime + planned_delta
            values["order_line"].append((0, 0, line_values))
        return values

    def _po_repeat_create_order(self, scheduled_date):
        self.ensure_one()
        if self.po_repeat_is_generated or self.po_repeat_origin_id:
            raise UserError(
                _("An order generated from another order cannot be repeated again.")
            )
        if not self.order_line:
            raise UserError(
                _("A recurring purchase order must have at least one order line.")
            )
        values = self._po_repeat_prepare_order_values(scheduled_date)
        return (
            self.env["purchase.order"]
            .with_company(self.company_id)
            .with_context(po_repeat_generation=True)
            .create(values)
        )

    def action_po_repeat_generate_now(self):
        self.ensure_one()
        if self.state == "cancel":
            raise UserError(_("A cancelled purchase order cannot be repeated."))
        scheduled_date = fields.Date.context_today(self)
        new_order = self._po_repeat_create_order(scheduled_date)
        return {
            "type": "ir.actions.act_window",
            "name": _("Generated Purchase Order"),
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": new_order.id,
            "target": "current",
        }

    def action_po_repeat_view_generated(self):
        self.ensure_one()
        action = self.env.ref("purchase.purchase_rfq").read()[0]
        action["domain"] = [("po_repeat_origin_id", "=", self.id)]
        action["context"] = {
            "default_po_repeat_origin_id": self.id,
            "create": False,
        }
        return action

    @api.model
    def _cron_generate_recurring_purchase_orders(self):
        today = fields.Date.context_today(self)
        orders = self.search(
            [
                ("po_repeat_active", "=", True),
                ("po_repeat_is_generated", "=", False),
                ("po_repeat_origin_id", "=", False),
                ("po_repeat_next_date", "<=", today),
                ("state", "!=", "cancel"),
            ]
        )
        for order in orders:
            try:
                with self.env.cr.savepoint():
                    scheduled_date = order.po_repeat_next_date
                    order._po_repeat_create_order(scheduled_date)
                    order.po_repeat_next_date = order._po_repeat_get_next_date(
                        scheduled_date
                    )
            except Exception:
                _logger.exception(
                    "Could not generate the recurring purchase order for %s (ID %s)",
                    order.name,
                    order.id,
                )
