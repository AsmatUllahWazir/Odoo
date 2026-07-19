# -*- coding: utf-8 -*-
"""
Account Move Extension - Add lease relationship
"""

from odoo import api, fields, models, _


class AccountMove(models.Model):
    """
    Extend account.move with lease relationship
    """
    _inherit = 'account.move'

    lease_id = fields.Many2one(
        'property.lease',
        string='Lease',
        help='Related lease agreement',
        ondelete='set null',
        index=True
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        related='lease_id.property_id',
        store=True,
        help='Related property'
    )

    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        related='lease_id.tenant_id',
        store=True,
        help='Related tenant'
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        related='lease_id.unit_id',
        store=True,
        help='Related unit'
    )

    is_lease_invoice = fields.Boolean(
        string='Is Lease Invoice',
        default=False,
        help='Whether this invoice is generated from a lease'
    )
