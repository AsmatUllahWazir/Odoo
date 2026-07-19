# -*- coding: utf-8 -*-
"""
Models module initialization
"""

from . import property_property
from . import property_unit
from . import property_lease
from . import property_viewing
from . import property_maintenance
from . import property_tenant_screening
from . import property_hoa
from . import property_dynamic_pricing
from . import property_portfolio
from . import property_res_partner
from . import property_iot_device
from . import property_account_move

try:
    from odoo.addons.account.models.account_move import AccountMove
    from . import property_account_move
except ImportError:
    pass
