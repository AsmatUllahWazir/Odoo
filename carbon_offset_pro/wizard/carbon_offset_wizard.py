from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarbonOffsetWizard(models.TransientModel):
    _name = 'carbon.offset.wizard'
    _description = 'Carbon Offset Wizard'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    total_footprint_kg = fields.Float(string='Carbon Footprint (kg)', readonly=True)
    total_footprint_tons = fields.Float(string='Carbon Footprint (tons)', readonly=True)
    selected_project_id = fields.Many2one('carbon.offset.project', string='Offset Project', required=True,
                                          domain="[('is_active', '=', True), ('available_credits_tons', '>', 0)]")
    tons_to_offset = fields.Float(string='Tons to Offset', required=True)
    unit_price_usd = fields.Float(string='Unit Price (USD/ton)', compute='_compute_pricing', store=True)
    discount_percentage = fields.Float(string='Discount %', compute='_compute_pricing', store=True)
    subtotal_usd = fields.Float(string='Subtotal (USD)', compute='_compute_pricing', store=True)
    estimated_cost = fields.Monetary(string='Estimated Cost', compute='_compute_pricing', store=True)
    currency_id = fields.Many2one('res.currency', related='sale_order_id.currency_id')
    notes = fields.Text(string='Notes')

    @api.onchange('selected_project_id')
    def _onchange_project(self):
        if self.selected_project_id and self.total_footprint_tons:
            self.tons_to_offset = self.total_footprint_tons
            if self.tons_to_offset < self.selected_project_id.minimum_purchase_tons:
                self.tons_to_offset = self.selected_project_id.minimum_purchase_tons

    @api.depends('tons_to_offset', 'selected_project_id')
    def _compute_pricing(self):
        for wizard in self:
            if wizard.selected_project_id and wizard.tons_to_offset:
                wizard.unit_price_usd = wizard.selected_project_id.get_discounted_price(wizard.tons_to_offset)
                wizard.discount_percentage = ((wizard.selected_project_id.price_per_ton_usd - wizard.unit_price_usd) /
                                              wizard.selected_project_id.price_per_ton_usd * 100) if wizard.selected_project_id.price_per_ton_usd > 0 else 0
                wizard.subtotal_usd = wizard.tons_to_offset * wizard.unit_price_usd
                wizard.estimated_cost = wizard.sale_order_id.currency_id._convert(
                    wizard.subtotal_usd,
                    wizard.sale_order_id.company_id.currency_id,
                    wizard.sale_order_id.company_id,
                    fields.Date.today()
                )
            else:
                wizard.unit_price_usd = 0
                wizard.discount_percentage = 0
                wizard.subtotal_usd = 0
                wizard.estimated_cost = 0

    @api.constrains('tons_to_offset')
    def _check_tons(self):
        for wizard in self:
            if wizard.tons_to_offset <= 0:
                raise ValidationError(_("Tons to offset must be greater than 0."))
            if wizard.selected_project_id and wizard.tons_to_offset > wizard.selected_project_id.available_credits_tons:
                raise ValidationError(_("Not enough credits available. Maximum: %.2f tons") %
                                      wizard.selected_project_id.available_credits_tons)

    def action_purchase_offset(self):
        self.ensure_one()
        purchase = self.env['carbon.offset.purchase'].create({
            'sale_order_id': self.sale_order_id.id,
            'project_id': self.selected_project_id.id,
            'tons_offset': self.tons_to_offset,
            'notes': self.notes,
        })

        # Show success message
        message = _("Successfully purchased %.2f tons of carbon offset.\nCertificate: %s") % (
            purchase.tons_offset, purchase.certificate_number)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    