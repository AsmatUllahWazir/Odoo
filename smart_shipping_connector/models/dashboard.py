from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import json

_logger = logging.getLogger(__name__)


class ShippingDashboard(models.Model):
    """Shipping Dashboard - Complete Analytics"""
    _name = 'shipping.dashboard'
    _description = 'Shipping Dashboard'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', default='Shipping Dashboard')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # ==================== KPI CARDS ====================
    # Shipment Statistics
    total_shipments = fields.Integer(
        string='Total Shipments',
        compute='_compute_statistics',
        help='Total number of shipments'
    )
    pending_shipments = fields.Integer(
        string='Pending Shipments',
        compute='_compute_statistics',
        help='Shipments in draft or confirmed state'
    )
    processing_shipments = fields.Integer(
        string='Processing Shipments',
        compute='_compute_statistics',
        help='Shipments being processed'
    )
    in_transit_shipments = fields.Integer(
        string='In Transit',
        compute='_compute_statistics',
        help='Shipments in transit'
    )
    out_for_delivery_shipments = fields.Integer(
        string='Out for Delivery',
        compute='_compute_statistics',
        help='Shipments out for delivery'
    )
    delivered_shipments = fields.Integer(
        string='Delivered',
        compute='_compute_statistics',
        help='Delivered shipments'
    )
    exception_shipments = fields.Integer(
        string='Exceptions',
        compute='_compute_statistics',
        help='Shipments with exceptions'
    )
    cancelled_shipments = fields.Integer(
        string='Cancelled',
        compute='_compute_statistics',
        help='Cancelled shipments'
    )

    # Return Statistics
    total_returns = fields.Integer(
        string='Total Returns',
        compute='_compute_statistics',
    )
    pending_returns = fields.Integer(
        string='Pending Returns',
        compute='_compute_statistics',
    )
    approved_returns = fields.Integer(
        string='Approved Returns',
        compute='_compute_statistics',
    )
    completed_returns = fields.Integer(
        string='Completed Returns',
        compute='_compute_statistics',
    )
    rejected_returns = fields.Integer(
        string='Rejected Returns',
        compute='_compute_statistics',
    )

    # Financial Statistics
    total_shipping_cost = fields.Monetary(
        string='Total Shipping Cost',
        currency_field='currency_id',
        compute='_compute_statistics',
    )
    average_shipping_cost = fields.Monetary(
        string='Average Shipping Cost',
        currency_field='currency_id',
        compute='_compute_statistics',
    )
    total_insurance_cost = fields.Monetary(
        string='Total Insurance Cost',
        currency_field='currency_id',
        compute='_compute_statistics',
    )
    total_return_cost = fields.Monetary(
        string='Total Return Cost',
        currency_field='currency_id',
        compute='_compute_statistics',
    )

    # Performance Metrics
    average_delivery_days = fields.Float(
        string='Avg Delivery Days',
        compute='_compute_statistics',
        digits=(10, 1),
    )
    on_time_delivery_rate = fields.Float(
        string='On-Time Delivery Rate (%)',
        compute='_compute_statistics',
        digits=(10, 1),
    )
    exception_rate = fields.Float(
        string='Exception Rate (%)',
        compute='_compute_statistics',
        digits=(10, 1),
    )
    return_rate = fields.Float(
        string='Return Rate (%)',
        compute='_compute_statistics',
        digits=(10, 1),
    )

    # Carrier Statistics
    carrier_statistics = fields.Text(
        string='Carrier Statistics',
        compute='_compute_carrier_stats',
        help='JSON data for carrier performance'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ==================== COMPUTATION METHODS ====================

    @api.depends()
    def _compute_statistics(self):
        """Compute all dashboard statistics"""
        for dashboard in self:
            Shipment = self.env['shipping.shipment']
            Return = self.env['shipping.return']

            # Shipment stats
            all_shipments = Shipment.search([('company_id', '=', dashboard.company_id.id)])
            dashboard.total_shipments = len(all_shipments)
            dashboard.pending_shipments = len(all_shipments.filtered(
                lambda s: s.state in ['draft', 'confirmed']
            ))
            dashboard.processing_shipments = len(all_shipments.filtered(
                lambda s: s.state in ['processing', 'label_generated']
            ))
            dashboard.in_transit_shipments = len(all_shipments.filtered(
                lambda s: s.state == 'in_transit'
            ))
            dashboard.out_for_delivery_shipments = len(all_shipments.filtered(
                lambda s: s.state == 'out_for_delivery'
            ))
            dashboard.delivered_shipments = len(all_shipments.filtered(
                lambda s: s.state == 'delivered'
            ))
            dashboard.exception_shipments = len(all_shipments.filtered(
                lambda s: s.state == 'exception'
            ))
            dashboard.cancelled_shipments = len(all_shipments.filtered(
                lambda s: s.state == 'cancelled'
            ))

            # Return stats
            all_returns = Return.search([('company_id', '=', dashboard.company_id.id)])
            dashboard.total_returns = len(all_returns)
            dashboard.pending_returns = len(all_returns.filtered(
                lambda r: r.state in ['draft', 'requested']
            ))
            dashboard.approved_returns = len(all_returns.filtered(
                lambda r: r.state == 'approved'
            ))
            dashboard.completed_returns = len(all_returns.filtered(
                lambda r: r.state == 'completed'
            ))
            dashboard.rejected_returns = len(all_returns.filtered(
                lambda r: r.state == 'rejected'
            ))

            # Financial stats
            delivered = all_shipments.filtered(lambda s: s.state == 'delivered')
            dashboard.total_shipping_cost = sum(all_shipments.mapped('shipping_cost'))
            dashboard.average_shipping_cost = (
                dashboard.total_shipping_cost / len(all_shipments) if all_shipments else 0
            )
            dashboard.total_insurance_cost = sum(all_shipments.mapped('insurance_cost'))
            dashboard.total_return_cost = sum(all_returns.mapped('return_cost'))

            # Performance metrics
            # Average delivery days
            shipped = all_shipments.filtered(
                lambda s: s.shipped_date and s.delivered_date
            )
            if shipped:
                total_days = sum((s.delivered_date - s.shipped_date).days for s in shipped)
                dashboard.average_delivery_days = total_days / len(shipped)
            else:
                dashboard.average_delivery_days = 0.0

            # On-time delivery rate
            on_time = shipped.filtered(
                lambda s: not s.delivered_late
            )
            dashboard.on_time_delivery_rate = (
                (len(on_time) / len(shipped) * 100) if shipped else 0.0
            )

            # Exception rate
            dashboard.exception_rate = (
                (dashboard.exception_shipments / dashboard.total_shipments * 100)
                if dashboard.total_shipments > 0 else 0.0
            )

            # Return rate
            dashboard.return_rate = (
                (dashboard.total_returns / dashboard.total_shipments * 100)
                if dashboard.total_shipments > 0 else 0.0
            )

    @api.depends()
    def _compute_carrier_stats(self):
        """Compute carrier performance statistics"""
        for dashboard in self:
            carrier_stats = {}
            carriers = self.env['shipping.carrier.provider'].search([
                ('active', '=', True),
                ('company_id', '=', dashboard.company_id.id)
            ])

            for carrier in carriers:
                shipments = self.env['shipping.shipment'].search([
                    ('carrier_provider_id', '=', carrier.id),
                    ('company_id', '=', dashboard.company_id.id)
                ])
                delivered = shipments.filtered(lambda s: s.state == 'delivered')
                on_time = delivered.filtered(lambda s: not s.delivered_late)

                carrier_stats[carrier.id] = {
                    'name': carrier.name,
                    'code': carrier.code,
                    'total_shipments': len(shipments),
                    'delivered': len(delivered),
                    'on_time': len(on_time),
                    'on_time_rate': (len(on_time) / len(delivered) * 100) if delivered else 0,
                    'average_cost': sum(shipments.mapped('shipping_cost')) / len(shipments) if shipments else 0,
                    'total_cost': sum(shipments.mapped('shipping_cost')),
                }

            dashboard.carrier_statistics = json.dumps(carrier_stats)

    # ==================== ACTION METHODS ====================

    def action_refresh(self):
        """Refresh dashboard data"""
        self.ensure_one()
        self._compute_statistics()
        self._compute_carrier_stats()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dashboard Refreshed'),
                'message': _('Dashboard statistics have been updated.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_shipments(self):
        """View all shipments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('All Shipments'),
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.company_id.id)],
        }

    def action_view_pending_shipments(self):
        """View pending shipments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pending Shipments'),
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['draft', 'confirmed'])
            ],
        }

    def action_view_in_transit(self):
        """View in-transit shipments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('In Transit Shipments'),
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['shipped', 'in_transit', 'out_for_delivery'])
            ],
        }

    def action_view_exceptions(self):
        """View exception shipments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Exception Shipments'),
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'exception')
            ],
        }

    def action_view_returns(self):
        """View all returns"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('All Returns'),
            'res_model': 'shipping.return',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.company_id.id)],
        }

    def action_export_report(self):
        """Export dashboard report"""
        self.ensure_one()
        # TODO: Implement report export
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Report Export'),
                'message': _('Dashboard report will be generated.'),
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def action_update_statistics(self):
        """Cron job to update dashboard statistics"""
        dashboards = self.search([])
        for dashboard in dashboards:
            dashboard.action_refresh()
        _logger.info(f"Updated {len(dashboards)} dashboards")
        return True


class ShippingDashboardWidget(models.Model):
    """Dashboard Custom Widget Configuration"""
    _name = 'shipping.dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'dashboard_id, sequence'

    dashboard_id = fields.Many2one(
        'shipping.dashboard',
        string='Dashboard',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Widget Name', required=True)

    widget_type = fields.Selection([
        ('kpi', 'KPI Card'),
        ('chart', 'Chart'),
        ('table', 'Data Table'),
        ('map', 'Map'),
        ('timeline', 'Timeline'),
        ('custom', 'Custom'),
    ], string='Widget Type', required=True)

    # Configuration
    config = fields.Text(string='Configuration (JSON)')
    width = fields.Integer(string='Width', default=6)
    height = fields.Integer(string='Height', default=4)

    # Visibility
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups',
        string='Visible Groups',
        help='Groups that can see this widget'
    )

    def _get_config_data(self):
        """Parse widget configuration"""
        self.ensure_one()
        try:
            return json.loads(self.config) if self.config else {}
        except:
            return {}
