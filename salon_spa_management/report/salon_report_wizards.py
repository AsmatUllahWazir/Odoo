# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime

class SalonRevenueReportWizard(models.TransientModel):
    _name = 'salon.revenue.report.wizard'
    _description = 'Revenue Report Wizard'

    date_from = fields.Date(string='Date From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.today)

    def action_print_report(self):
        data = {
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
        }
        return self.env.ref('salon_spa_management.action_report_salon_revenue').report_action(self, data=data)


class SalonMembershipReportWizard(models.TransientModel):
    _name = 'salon.membership.report.wizard'
    _description = 'Membership Report Wizard'

    def action_print_report(self):
        return self.env.ref('salon_spa_management.action_report_salon_membership').report_action(self)


class SalonDailyReportWizard(models.TransientModel):
    _name = 'salon.daily.report.wizard'
    _description = 'Daily Report Wizard'

    report_date = fields.Date(string='Report Date', required=True, default=fields.Date.today)

    def action_print_report(self):
        data = {
            'report_date': self.report_date.strftime('%Y-%m-%d'),
        }
        return self.env.ref('salon_spa_management.action_report_salon_daily').report_action(self, data=data)
    