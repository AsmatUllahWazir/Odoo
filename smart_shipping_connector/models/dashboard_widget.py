from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class ShippingDashboardWidget(models.Model):
    """Dashboard Custom Widget Configuration"""
    _name = 'shipping.dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'dashboard_id, sequence'
    _rec_name = 'name'

    dashboard_id = fields.Many2one(
        'shipping.dashboard',
        string='Dashboard',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Widget Name', required=True, translate=True)

    widget_type = fields.Selection([
        ('kpi', 'KPI Card'),
        ('chart_bar', 'Bar Chart'),
        ('chart_line', 'Line Chart'),
        ('chart_pie', 'Pie Chart'),
        ('chart_donut', 'Donut Chart'),
        ('table', 'Data Table'),
        ('map', 'Map'),
        ('timeline', 'Timeline'),
        ('gauge', 'Gauge'),
        ('metric', 'Metric'),
        ('custom', 'Custom'),
    ], string='Widget Type', required=True)

    # Configuration
    config = fields.Text(string='Configuration (JSON)')

    # Display
    width = fields.Integer(string='Width', default=6, help='Column width (1-12)')
    height = fields.Integer(string='Height', default=4, help='Height in rows')

    # Data Source
    data_source = fields.Selection([
        ('shipment', 'Shipments'),
        ('return', 'Returns'),
        ('carrier', 'Carrier Performance'),
        ('financial', 'Financial'),
        ('custom', 'Custom Query'),
    ], string='Data Source', default='shipment')

    custom_query = fields.Text(string='Custom Query')

    # Filters
    filter_domain = fields.Text(string='Domain Filter (JSON)')
    filter_date_range = fields.Boolean(string='Enable Date Range', default=True)
    date_field = fields.Char(string='Date Field', default='create_date')

    # Color Scheme
    color_scheme = fields.Selection([
        ('primary', 'Primary'),
        ('success', 'Success'),
        ('danger', 'Danger'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('dark', 'Dark'),
        ('custom', 'Custom'),
    ], string='Color Scheme', default='primary')

    custom_colors = fields.Text(string='Custom Colors (JSON)')

    # Visibility
    active = fields.Boolean(string='Active', default=True)
    group_ids = fields.Many2many(
        'res.groups',
        string='Visible Groups',
        help='Groups that can see this widget'
    )

    # Refresh
    auto_refresh = fields.Boolean(string='Auto Refresh', default=False)
    refresh_interval = fields.Integer(string='Refresh Interval (Seconds)', default=60)

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.constrains('config')
    def _check_config(self):
        for widget in self:
            if widget.config:
                try:
                    json.loads(widget.config)
                except json.JSONDecodeError:
                    raise ValidationError(_('Configuration must be valid JSON format.'))

    @api.constrains('custom_colors')
    def _check_custom_colors(self):
        for widget in self:
            if widget.custom_colors:
                try:
                    colors = json.loads(widget.custom_colors)
                    if not isinstance(colors, list):
                        raise ValidationError(_('Custom colors must be a JSON array.'))
                except json.JSONDecodeError:
                    raise ValidationError(_('Custom colors must be valid JSON format.'))

    def _get_config_data(self):
        """Parse widget configuration"""
        self.ensure_one()
        try:
            return json.loads(self.config) if self.config else {}
        except:
            return {}

    def _get_filter_domain(self, date_start=None, date_end=None):
        """Get filter domain"""
        self.ensure_one()
        domain = []

        if self.filter_domain:
            try:
                domain = json.loads(self.filter_domain)
            except:
                pass

        if date_start and date_end and self.date_field:
            domain.append((self.date_field, '>=', date_start))
            domain.append((self.date_field, '<=', date_end))

        return domain

    def get_widget_data(self, date_start=None, date_end=None):
        """Get data for the widget"""
        self.ensure_one()

        if self.data_source == 'shipment':
            return self._get_shipment_data(date_start, date_end)
        elif self.data_source == 'return':
            return self._get_return_data(date_start, date_end)
        elif self.data_source == 'carrier':
            return self._get_carrier_data(date_start, date_end)
        elif self.data_source == 'financial':
            return self._get_financial_data(date_start, date_end)
        elif self.data_source == 'custom':
            return self._get_custom_data(date_start, date_end)

        return {}

    def _get_shipment_data(self, date_start=None, date_end=None):
        """Get shipment data for widget"""
        self.ensure_one()

        Shipment = self.env['shipping.shipment']
        domain = self._get_filter_domain(date_start, date_end)

        if self.widget_type in ['kpi', 'metric']:
            # KPI Widget
            total = Shipment.search_count(domain)
            delivered = Shipment.search_count(domain + [('state', '=', 'delivered')])
            in_transit = Shipment.search_count(domain + [('state', 'in', ['shipped', 'in_transit'])])
            exceptions = Shipment.search_count(domain + [('state', '=', 'exception')])

            return {
                'total': total,
                'delivered': delivered,
                'in_transit': in_transit,
                'exceptions': exceptions,
                'delivery_rate': (delivered / total * 100) if total > 0 else 0,
            }

        elif self.widget_type in ['chart_bar', 'chart_line']:
            # Chart Widget
            data = []
            shipments = Shipment.search(domain)

            # Group by carrier
            carriers = shipments.mapped('carrier_provider_id')
            for carrier in carriers:
                count = len(shipments.filtered(lambda s: s.carrier_provider_id.id == carrier.id))
                data.append({
                    'label': carrier.name,
                    'value': count,
                })

            return {'data': data}

        return {}

    def _get_return_data(self, date_start=None, date_end=None):
        """Get return data for widget"""
        self.ensure_one()

        Return = self.env['shipping.return']
        domain = self._get_filter_domain(date_start, date_end)

        if self.widget_type in ['kpi', 'metric']:
            total = Return.search_count(domain)
            pending = Return.search_count(domain + [('state', 'in', ['draft', 'requested'])])
            completed = Return.search_count(domain + [('state', '=', 'completed')])
            rejected = Return.search_count(domain + [('state', '=', 'rejected')])

            return {
                'total': total,
                'pending': pending,
                'completed': completed,
                'rejected': rejected,
                'completion_rate': (completed / total * 100) if total > 0 else 0,
            }

        return {}

    def _get_carrier_data(self, date_start=None, date_end=None):
        """Get carrier performance data"""
        self.ensure_one()

        Shipment = self.env['shipping.shipment']
        domain = self._get_filter_domain(date_start, date_end)

        data = []
        carriers = self.env['shipping.carrier.provider'].search([('active', '=', True)])

        for carrier in carriers:
            carrier_domain = domain + [('carrier_provider_id', '=', carrier.id)]
            shipments = Shipment.search(carrier_domain)
            delivered = shipments.filtered(lambda s: s.state == 'delivered')
            on_time = delivered.filtered(lambda s: not s.delivered_late)

            data.append({
                'carrier_id': carrier.id,
                'carrier_name': carrier.name,
                'total': len(shipments),
                'delivered': len(delivered),
                'on_time': len(on_time),
                'on_time_rate': (len(on_time) / len(delivered) * 100) if delivered else 0,
                'average_cost': sum(shipments.mapped('shipping_cost')) / len(shipments) if shipments else 0,
            })

        return {'data': data}

    def _get_financial_data(self, date_start=None, date_end=None):
        """Get financial data for widget"""
        self.ensure_one()

        Shipment = self.env['shipping.shipment']
        domain = self._get_filter_domain(date_start, date_end)
        shipments = Shipment.search(domain)

        total_cost = sum(shipments.mapped('shipping_cost'))
        total_insurance = sum(shipments.mapped('insurance_cost'))
        total_cod = sum(shipments.mapped('cod_amount'))

        return {
            'total_cost': total_cost,
            'total_insurance': total_insurance,
            'total_cod': total_cod,
            'average_cost': total_cost / len(shipments) if shipments else 0,
            'total_shipments': len(shipments),
        }

    def _get_custom_data(self, date_start=None, date_end=None):
        """Get custom query data"""
        self.ensure_one()

        if not self.custom_query:
            return {}

        try:
            # Execute custom query
            self.env.cr.execute(self.custom_query, {
                'date_start': date_start or fields.Date.today() - timedelta(days=30),
                'date_end': date_end or fields.Date.today(),
            })
            result = self.env.cr.dictfetchall()
            return {'data': result}
        except Exception as e:
            _logger.error(f"Error executing custom query: {e}")
            return {'error': str(e)}
        