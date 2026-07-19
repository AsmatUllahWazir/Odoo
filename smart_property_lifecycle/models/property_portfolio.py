# -*- coding: utf-8 -*-
"""
Property Portfolio Report - Analytics and dashboard
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyPortfolioReport(models.TransientModel):
    """
    Portfolio Report - Analytics for property portfolio
    """
    _name = 'property.portfolio.report'
    _description = 'Property Portfolio Report'
    _rec_name = 'display_name'

    # ==========================================================================
    # Report Fields
    # ==========================================================================

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name'
    )

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )

    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    property_type = fields.Selection([
        ('all', 'All Types'),
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('land', 'Land'),
        ('mixed_use', 'Mixed Use'),
        ('condo', 'Condo'),
        ('multi_unit', 'Multi-Unit'),
    ], string='Property Type', default='all')

    status = fields.Selection([
        ('all', 'All Statuses'),
        ('listed', 'Listed'),
        ('under_offer', 'Under Offer'),
        ('leased', 'Leased'),
        ('sold', 'Sold'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='all')

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('date_from', 'date_to', 'property_type', 'status')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            record.display_name = f"Portfolio Report - {record.date_from} to {record.date_to}"

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_generate_report(self):
        """Generate portfolio report"""
        self.ensure_one()

        # Get properties based on filters
        domain = self._get_domain()
        properties = self.env['property.property'].search(domain)

        # Prepare report data
        report_data = self._prepare_report_data(properties)

        # Open report
        return {
            'type': 'ir.actions.act_window',
            'name': _('Portfolio Analytics'),
            'res_model': 'property.portfolio.report.result',
            'view_mode': 'tree,form,pivot,graph',
            'context': {
                'default_name': f"Portfolio Report {fields.Date.today()}",
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
                'default_property_ids': [(6, 0, properties.ids)],
                'default_total_properties': len(properties),
                'default_total_value': report_data['total_value'],
                'default_total_rent': report_data['total_rent'],
                'default_occupancy_rate': report_data['occupancy_rate'],
            },
        }

    def _get_domain(self):
        """Build domain for report"""
        domain = []

        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        if self.property_type != 'all':
            domain.append(('type', '=', self.property_type))

        if self.status != 'all':
            domain.append(('status', '=', self.status))

        # Date range
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))

        return domain

    def _prepare_report_data(self, properties):
        """Prepare report data"""
        total_properties = len(properties)
        total_value = sum(p.base_price for p in properties)
        total_rent = sum(p.rental_price for p in properties)
        total_area = sum(p.area_total for p in properties)
        occupied = len(properties.filtered(lambda p: p.occupancy_rate > 0))

        # Property type breakdown
        type_breakdown = {}
        for prop in properties:
            type_breakdown[prop.type] = type_breakdown.get(prop.type, 0) + 1

        # Status breakdown
        status_breakdown = {}
        for prop in properties:
            status_breakdown[prop.status] = status_breakdown.get(prop.status, 0) + 1

        return {
            'total_properties': total_properties,
            'total_value': total_value,
            'total_rent': total_rent,
            'total_area': total_area,
            'occupied_count': occupied,
            'vacant_count': total_properties - occupied,
            'occupancy_rate': (occupied / total_properties * 100) if total_properties > 0 else 0,
            'type_breakdown': type_breakdown,
            'status_breakdown': status_breakdown,
            'avg_price': total_value / total_properties if total_properties > 0 else 0,
            'avg_area': total_area / total_properties if total_properties > 0 else 0,
        }


class PropertyPortfolioReportResult(models.TransientModel):
    """
    Portfolio Report Results - Display report data
    """
    _name = 'property.portfolio.report.result'
    _description = 'Portfolio Report Result'
    _rec_name = 'name'

    name = fields.Char(
        string='Report Name',
        required=True,
        default=lambda self: f"Portfolio Report {fields.Date.today()}"
    )

    date_from = fields.Date(
        string='Date From'
    )

    date_to = fields.Date(
        string='Date To'
    )

    property_ids = fields.Many2many(
        'property.property',
        string='Properties'
    )

    total_properties = fields.Integer(
        string='Total Properties'
    )

    total_value = fields.Monetary(
        string='Total Value',
        currency_field='currency_id'
    )

    total_rent = fields.Monetary(
        string='Total Monthly Rent',
        currency_field='currency_id'
    )

    occupancy_rate = fields.Float(
        string='Occupancy Rate (%)'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    report_data = fields.Json(
        string='Report Data'
    )

    def action_view_properties(self):
        """View properties in report"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Portfolio Properties'),
            'res_model': 'property.property',
            'view_mode': 'tree,kanban,form',
            'domain': [('id', 'in', self.property_ids.ids)],
        }

    def _get_domain(self):
        domain = []
        if self.property_type != 'all':
            domain.append(('type', '=', self.property_type))
        if self.status != 'all':
            domain.append(('status', '=', self.status))
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        return domain
    