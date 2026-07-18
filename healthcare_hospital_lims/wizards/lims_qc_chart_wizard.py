# -*- coding: utf-8 -*-
"""
QC Chart Wizard
Generates quality control charts for analysis
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class LimsQCChartWizard(models.TransientModel):
    """
    Wizard for generating QC charts
    """
    _name = 'lims.qc.chart.wizard'
    _description = 'QC Chart Wizard'

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type',
        required=True
    )

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )

    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today()
    )

    chart_type = fields.Selection([
        ('levey_jennings', 'Levey-Jennings Chart'),
        ('westgard', 'Westgard Multi-Rule'),
        ('control_chart', 'Control Chart'),
        ('histogram', 'Histogram'),
        ('trend', 'Trend Analysis')
    ], string='Chart Type', required=True, default='levey_jennings')

    include_sd_lines = fields.Boolean(
        string='Show Standard Deviation Lines',
        default=True,
        help='Display 1σ, 2σ, and 3σ lines'
    )

    include_mean_line = fields.Boolean(
        string='Show Mean Line',
        default=True
    )

    chart_image = fields.Binary(
        string='Chart Image',
        compute='_compute_chart_image'
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate date range"""
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_('Start date must be before end date!'))
            if (record.end_date - record.start_date).days > 365:
                raise ValidationError(_('Date range cannot exceed 365 days!'))

    @api.depends('test_type_id', 'start_date', 'end_date', 'chart_type')
    def _compute_chart_image(self):
        """Generate chart image"""
        for record in self:
            try:
                record.chart_image = self._generate_chart(record)
            except Exception as e:
                _logger.error(f"Error generating chart: {str(e)}")
                record.chart_image = False

    def _generate_chart(self, record):
        """Generate the actual chart image"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            # Get QC data
            qcs = self.env['lims.quality_control'].search([
                ('test_type_id', '=', record.test_type_id.id),
                ('date', '>=', record.start_date),
                ('date', '<=', record.end_date),
                ('state', '=', 'approved')
            ], order='date asc')

            if not qcs:
                return False

            values = qcs.mapped('result_value')
            dates = qcs.mapped('date')

            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))

            if record.chart_type == 'levey_jennings':
                self._create_levey_jennings(ax, qcs, dates, values, record)
            elif record.chart_type == 'westgard':
                self._create_westgard(ax, qcs, dates, values, record)
            elif record.chart_type == 'control_chart':
                self._create_control_chart(ax, qcs, dates, values, record)
            elif record.chart_type == 'histogram':
                self._create_histogram(ax, values, record)
            elif record.chart_type == 'trend':
                self._create_trend(ax, qcs, dates, values, record)

            # Save to buffer
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()

            return base64.b64encode(buffer.getvalue())
        except ImportError:
            _logger.warning("Matplotlib not installed. Cannot generate chart.")
            return False
        except Exception as e:
            _logger.error(f"Error generating chart: {str(e)}")
            return False

    def _create_levey_jennings(self, ax, qcs, dates, values, record):
        """Create Levey-Jennings chart"""
        import numpy as np

        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values)

        # Plot values
        ax.plot(dates, values, 'o-', color='blue', markersize=6, label='QC Results')

        # Add mean line
        if record.include_mean_line:
            ax.axhline(y=mean, color='green', linestyle='--', linewidth=2, label=f'Mean: {mean:.2f}')

        # Add SD lines
        if record.include_sd_lines:
            colors = ['#ff6b6b', '#ffd93d', '#6bcb77']
            for i, (color, label) in enumerate([(1, '1σ'), (2, '2σ'), (3, '3σ')]):
                ax.axhline(y=mean + i * std, color=colors[i - 1], linestyle=':', linewidth=1, label=f'+{label}')
                ax.axhline(y=mean - i * std, color=colors[i - 1], linestyle=':', linewidth=1, label=f'-{label}')

        # Formatting
        ax.set_xlabel('Date')
        ax.set_ylabel('QC Value')
        ax.set_title(f'Levey-Jennings Chart - {record.test_type_id.name}')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _create_westgard(self, ax, qcs, dates, values, record):
        """Create Westgard multi-rule chart"""
        import numpy as np

        mean = np.mean(values)
        std = np.std(values)

        # Plot points
        ax.plot(dates, values, 'o', color='blue', markersize=6)

        # Apply Westgard rules
        for i, val in enumerate(values):
            z_score = (val - mean) / std if std > 0 else 0

            # Check rules
            if abs(z_score) > 3:
                color = 'red'
                label = 'R1: 1₃S'
            elif abs(z_score) > 2:
                color = 'orange'
                label = 'R2: 1₂S'
            else:
                color = 'green'
                label = 'OK'

            ax.plot(dates[i], val, 'o', color=color, markersize=8, label=label if i == 0 else '')

        # Add lines
        ax.axhline(y=mean, color='green', linestyle='--', linewidth=1)
        ax.axhline(y=mean + 2 * std, color='orange', linestyle=':', linewidth=1)
        ax.axhline(y=mean - 2 * std, color='orange', linestyle=':', linewidth=1)
        ax.axhline(y=mean + 3 * std, color='red', linestyle=':', linewidth=1)
        ax.axhline(y=mean - 3 * std, color='red', linestyle=':', linewidth=1)

        ax.set_xlabel('Date')
        ax.set_ylabel('QC Value')
        ax.set_title(f'Westgard Multi-Rule Chart - {record.test_type_id.name}')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _create_control_chart(self, ax, qcs, dates, values, record):
        """Create control chart with upper and lower limits"""
        import numpy as np

        mean = np.mean(values)
        std = np.std(values)

        # Define limits
        upper_limit = mean + 3 * std
        lower_limit = mean - 3 * std

        # Plot
        ax.plot(dates, values, 'o-', color='blue', markersize=5, linewidth=1)
        ax.axhline(y=upper_limit, color='red', linestyle='--', linewidth=2, label=f'UCL: {upper_limit:.2f}')
        ax.axhline(y=mean, color='green', linestyle='-', linewidth=2, label=f'Mean: {mean:.2f}')
        ax.axhline(y=lower_limit, color='red', linestyle='--', linewidth=2, label=f'LCL: {lower_limit:.2f}')

        # Fill between limits
        ax.fill_between(dates, lower_limit, upper_limit, color='green', alpha=0.1)

        ax.set_xlabel('Date')
        ax.set_ylabel('QC Value')
        ax.set_title(f'Control Chart - {record.test_type_id.name}')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _create_histogram(self, ax, values, record):
        """Create histogram of QC values"""
        import numpy as np

        n, bins, patches = ax.hist(values, bins='auto', color='blue', alpha=0.7, edgecolor='black')

        # Add mean and SD lines
        mean = np.mean(values)
        std = np.std(values)
        ax.axvline(x=mean, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean:.2f}')
        ax.axvline(x=mean - std, color='orange', linestyle=':', linewidth=1, label='-1σ')
        ax.axvline(x=mean + std, color='orange', linestyle=':', linewidth=1, label='+1σ')

        ax.set_xlabel('QC Value')
        ax.set_ylabel('Frequency')
        ax.set_title(f'Histogram - {record.test_type_id.name}')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

    def _create_trend(self, ax, qcs, dates, values, record):
        """Create trend analysis chart"""
        import numpy as np
        from scipy import stats

        # Linear regression
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        trend_line = slope * x + intercept

        # Plot
        ax.plot(dates, values, 'o-', color='blue', markersize=5, label='Actual')
        ax.plot(dates, trend_line, 'r-', linewidth=2, label=f'Trend (slope: {slope:.3f})')

        # Add moving average (3-point)
        if len(values) >= 3:
            ma = np.convolve(values, np.ones(3) / 3, mode='valid')
            ma_dates = dates[1:-1] if len(dates) > 2 else dates
            ax.plot(ma_dates, ma, 'g--', linewidth=2, label='3-point Moving Average')

        ax.set_xlabel('Date')
        ax.set_ylabel('QC Value')
        ax.set_title(f'Trend Analysis - {record.test_type_id.name}')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        # Add stats annotation
        stats_text = f'R²: {r_value ** 2:.3f}\np-value: {p_value:.4f}\nn: {len(values)}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    def action_generate_chart(self):
        """Generate and display the chart"""
        self.ensure_one()

        if not self.chart_image:
            raise ValidationError(_('Could not generate chart. Please check if there is enough QC data.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('QC Chart - %s') % self.test_type_id.name,
            'res_model': 'lims.qc.chart.result',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_chart_image': self.chart_image,
                'default_test_type_id': self.test_type_id.id,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
                'default_chart_type': self.chart_type,
            },
        }


class LimsQCChartResult(models.TransientModel):
    """
    Temporary model to display QC chart results
    """
    _name = 'lims.qc.chart.result'
    _description = 'QC Chart Result'

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type'
    )

    chart_image = fields.Binary(
        string='Chart',
        required=True
    )

    chart_type = fields.Char(
        string='Chart Type'
    )

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    stats_summary = fields.Text(
        string='Statistics Summary',
        compute='_compute_stats_summary'
    )

    @api.depends('test_type_id', 'start_date', 'end_date')
    def _compute_stats_summary(self):
        """Compute statistics summary"""
        for record in self:
            if record.test_type_id:
                qcs = self.env['lims.quality_control'].search([
                    ('test_type_id', '=', record.test_type_id.id),
                    ('date', '>=', record.start_date),
                    ('date', '<=', record.end_date),
                    ('state', '=', 'approved')
                ])

                if qcs:
                    import numpy as np
                    values = qcs.mapped('result_value')
                    if values:
                        record.stats_summary = f"""
                        Sample Size: {len(values)}
                        Mean: {np.mean(values):.2f}
                        Standard Deviation: {np.std(values):.2f}
                        Minimum: {min(values):.2f}
                        Maximum: {max(values):.2f}
                        Range: {max(values) - min(values):.2f}
                        CV: {(np.std(values) / np.mean(values) * 100):.2f}%
                        """
                    else:
                        record.stats_summary = "No valid values found"
                else:
                    record.stats_summary = "No QC data found for this period"
            else:
                record.stats_summary = "No test type selected"
