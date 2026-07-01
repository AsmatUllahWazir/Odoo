# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class DispatchKPI(models.Model):
    _name = 'dispatch.kpi'
    _description = 'Dispatch KPI Metrics'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    # Volume Metrics
    total_bills = fields.Integer(string='Total Bills', readonly=True)
    auto_routed_bills = fields.Integer(string='Auto-Routed Bills', readonly=True)
    manual_routed_bills = fields.Integer(string='Manually Routed', readonly=True)
    rejected_bills = fields.Integer(string='Rejected Bills', readonly=True)

    # Percentage Metrics
    auto_routed_percentage = fields.Float(string='Auto-Routed %', readonly=True)
    rejection_rate = fields.Float(string='Rejection Rate %', readonly=True)

    # OCR Metrics
    ocr_processed = fields.Integer(string='OCR Processed', readonly=True)
    ocr_errors = fields.Integer(string='OCR Errors', readonly=True)
    avg_ocr_confidence = fields.Float(string='Avg OCR Confidence', readonly=True)

    # Processing Time Metrics
    avg_processing_time = fields.Float(string='Avg Processing Time (hours)', readonly=True)
    avg_business_approval_time = fields.Float(string='Avg Business Approval Time (hours)', readonly=True)
    avg_finance_approval_time = fields.Float(string='Avg Finance Approval Time (hours)', readonly=True)

    # Finance Approval
    finance_approvals_required = fields.Integer(string='Finance Approvals Required', readonly=True)
    finance_approved = fields.Integer(string='Finance Approved', readonly=True)

    def init(self):
        """Create SQL view for KPI metrics"""
        self._cr.execute("""
            CREATE OR REPLACE VIEW dispatch_kpi AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY DATE(am.create_date), am.company_id) as id,
                    DATE(am.create_date) as date,
                    am.company_id,

                    COUNT(*) as total_bills,
                    COUNT(*) FILTER (WHERE am.dispatch_method = 'automatic') as auto_routed_bills,
                    COUNT(*) FILTER (WHERE am.dispatch_method = 'manual') as manual_routed_bills,
                    COUNT(*) FILTER (WHERE am.dispatch_state = 'rejected') as rejected_bills,

                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            (COUNT(*) FILTER (WHERE am.dispatch_method = 'automatic')::float / COUNT(*)::float * 100)
                        ELSE 0 
                    END as auto_routed_percentage,

                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            (COUNT(*) FILTER (WHERE am.dispatch_state = 'rejected')::float / COUNT(*)::float * 100)
                        ELSE 0 
                    END as rejection_rate,

                    COUNT(*) FILTER (WHERE am.ocr_status = 'done') as ocr_processed,
                    COUNT(*) FILTER (WHERE am.ocr_status = 'error') as ocr_errors,
                    AVG(am.ocr_confidence) FILTER (WHERE am.ocr_confidence > 0) as avg_ocr_confidence,

                    AVG(
                        EXTRACT(EPOCH FROM (am.write_date - am.create_date)) / 3600
                    ) FILTER (WHERE am.state = 'posted') as avg_processing_time,

                    AVG(
                        EXTRACT(EPOCH FROM (am.business_approved_date - am.dispatch_date)) / 3600
                    ) FILTER (WHERE am.business_approved_date IS NOT NULL) as avg_business_approval_time,

                    AVG(
                        EXTRACT(EPOCH FROM (am.finance_approved_date - am.business_approved_date)) / 3600
                    ) FILTER (WHERE am.finance_approved_date IS NOT NULL) as avg_finance_approval_time,

                    COUNT(*) FILTER (WHERE am.requires_finance_approval = true) as finance_approvals_required,
                    COUNT(*) FILTER (WHERE am.dispatch_state = 'finance_approved') as finance_approved

                FROM account_move am
                WHERE am.move_type = 'in_invoice'
                    AND am.dispatch_state IS NOT NULL
                GROUP BY DATE(am.create_date), am.company_id
            )
        """)