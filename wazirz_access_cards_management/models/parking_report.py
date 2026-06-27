from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime


class ParkingReport(models.AbstractModel):
    _name = 'report.wazirz_parking_management.report_parking_template'
    _description = 'Parking Request Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['car.parking'].browse(docids)
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return {
            'doc_ids': docids,
            'doc_model': 'car.parking',
            'docs': docs,
            'data': data,
            'current_datetime': current_datetime,
            'get_status_badge': self._get_status_badge,
            'get_parking_type_badge': self._get_parking_type_badge,
            'calculate_occupancy': self._calculate_occupancy,
        }

    def _get_status_badge(self, state):
        """Return appropriate badge class for status"""
        status_map = {
            'draft': 'badge-secondary',
            'submitted': 'badge-info',
            'management_approval': 'badge-primary',
            'tech_active': 'badge-warning',
            'active': 'badge-success',
            'edit': 'badge-light',
            'canceled': 'badge-danger',
            'disable': 'badge-warning',
            'archive': 'badge-secondary',
            'rejected': 'badge-danger',
            'blocked': 'badge-dark',
        }
        return status_map.get(state, 'badge-secondary')

    def _get_parking_type_badge(self, parking_type):
        """Return appropriate badge class for parking type"""
        type_map = {
            'normal': 'badge-info',
            'valet': 'badge-success',
            'valet_pl': 'badge-warning',
        }
        return type_map.get(parking_type, 'badge-secondary')

    def _calculate_occupancy(self, floor_id):
        """Calculate occupancy percentage for a floor"""
        if not floor_id:
            return 0
        floor = self.env['building.floor'].browse(floor_id)
        if floor and floor.parking_spaces > 0:
            return round((floor.used_parking_spaces / floor.parking_spaces) * 100, 1)
        return 0
    