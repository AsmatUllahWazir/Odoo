from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_barcode_scanner(self):
        """Open the browser-based barcode scanner for this picking."""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_("You cannot scan a picking that is already done or cancelled."))
        return {
            'type': 'ir.actions.client',
            'tag': 'stock_barcode_scanner_pro',
            'name': _('Barcode Scanner'),
            'params': {
                'picking_id': self.id,
            },
        }

    def _scanner_find_move_by_barcode(self, barcode):
        """Find a move line in this picking matching a scanned barcode."""
        self.ensure_one()
        if not barcode:
            return None
        move_lines = self.move_line_ids.filtered(
            lambda ml: ml.product_id.barcode == barcode
            or (ml.lot_id and ml.lot_id.name == barcode)
            or (ml.lot_name and ml.lot_name == barcode)
        )
        if move_lines:
            ml = move_lines[0]
            return {
                'move_line_id': ml.id,
                'product_id': ml.product_id.id,
                'product_name': ml.product_id.display_name,
                'quantity': ml.quantity,
                'uom': ml.product_uom.name,
                'tracking': ml.product_id.tracking,
                'lot_name': ml.lot_name or (ml.lot_id.name if ml.lot_id else ''),
            }
        moves = self.move_ids.filtered(
            lambda m: m.product_id.barcode == barcode
        )
        if moves:
            m = moves[0]
            return {
                'move_id': m.id,
                'product_id': m.product_id.id,
                'product_name': m.product_id.display_name,
                'quantity': m.quantity,
                'uom': m.product_uom.name,
                'tracking': m.product_id.tracking,
                'needs_move_line': True,
            }
        return None
