from odoo import api, fields, models

class SaudiComplianceDashboard(models.Model):
    _name = 'saudi.compliance.dashboard'
    _description = 'Saudi Compliance Dashboard'
    _auto = False
    company_id = fields.Many2one('res.company')
    employee_count = fields.Integer()
    compliant_count = fields.Integer()
    attention_count = fields.Integer()
    critical_count = fields.Integer()
    expired_document_count = fields.Integer()
    expiring_document_count = fields.Integer()
    open_case_count = fields.Integer()
    pending_transaction_count = fields.Integer()
    pending_eos_count = fields.Integer()
    pending_wps_count = fields.Integer()
    compliance_rate = fields.Float()

    def init(self):
        self.env.cr.execute('DROP VIEW IF EXISTS saudi_compliance_dashboard')
        self.env.cr.execute("\n            CREATE VIEW saudi_compliance_dashboard AS (\n                SELECT\n                    c.id AS id,\n                    c.id AS company_id,\n                    COALESCE((SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active), 0) AS employee_count,\n                    COALESCE((SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active AND e.compliance_status = 'compliant'), 0) AS compliant_count,\n                    COALESCE((SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active AND e.compliance_status = 'attention'), 0) AS attention_count,\n                    COALESCE((SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active AND e.compliance_status = 'critical'), 0) AS critical_count,\n                    COALESCE((SELECT count(*) FROM saudi_compliance_document d WHERE d.company_id = c.id AND d.state = 'expired'), 0) AS expired_document_count,\n                    COALESCE((SELECT count(*) FROM saudi_compliance_document d WHERE d.company_id = c.id AND d.state = 'expiring'), 0) AS expiring_document_count,\n                    COALESCE((SELECT count(*) FROM saudi_compliance_case x WHERE x.company_id = c.id AND x.state NOT IN ('closed','cancelled')), 0) AS open_case_count,\n                    COALESCE((SELECT count(*) FROM saudi_government_transaction t WHERE t.company_id = c.id AND t.state IN ('submitted','processing')), 0) AS pending_transaction_count,\n                    COALESCE((SELECT count(*) FROM saudi_eos_request r WHERE r.company_id = c.id AND r.state IN ('submitted','hr_approved','finance_approved')), 0) AS pending_eos_count,\n                    COALESCE((SELECT count(*) FROM saudi_wps_batch w WHERE w.company_id = c.id AND w.state NOT IN ('accepted','rejected')), 0) AS pending_wps_count,\n                    CASE WHEN COALESCE((SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active), 0) = 0 THEN 0\n                         ELSE round(100.0 * COALESCE((SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active AND e.compliance_status = 'compliant'), 0) /\n                         (SELECT count(*) FROM hr_employee e WHERE e.company_id = c.id AND e.active), 2) END AS compliance_rate\n                FROM res_company c\n            )\n        ")
