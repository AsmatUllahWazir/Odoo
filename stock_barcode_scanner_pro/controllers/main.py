from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError


class StockBarcodeScannerController(http.Controller):

    @http.route('/stock_barcode_scanner_pro/picking/<int:picking_id>/state',
                type='json', auth='user', methods=['POST'])
    def get_picking_state(self, picking_id, **kwargs):
        picking = request.env['stock.picking'].browse(picking_id).exists()
        if not picking:
            raise UserError(_("Picking not found."))

        lines = []
        for move in picking.move_ids:
            lines.append({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'barcode': move.product_id.barcode or '',
                'demand': move.product_uom_qty,
                'quantity': move.quantity,
                'uom': move.product_uom.name,
                'state': move.state,
                'move_lines': [{
                    'move_line_id': ml.id,
                    'quantity': ml.quantity,
                    'lot_name': ml.lot_name or (ml.lot_id.name if ml.lot_id else ''),
                    'location_name': ml.location_id.display_name,
                    'dest_location_name': ml.location_dest_id.display_name,
                } for ml in move.move_line_ids],
            })

        return {
            'picking_id': picking.id,
            'picking_name': picking.name,
            'state': picking.state,
            'partner': picking.partner_id.display_name if picking.partner_id else '',
            'origin': picking.origin or '',
            'lines': lines,
            'is_done': picking.state == 'done',
            'is_cancelled': picking.state == 'cancel',
        }

    @http.route('/stock_barcode_scanner_pro/scan',
                type='json', auth='user', methods=['POST'])
    def scan_barcode(self, picking_id, barcode, increment=1.0, **kwargs):
        picking = request.env['stock.picking'].browse(picking_id).exists()
        if not picking:
            raise UserError(_("Picking not found."))
        if picking.state in ('done', 'cancel'):
            raise UserError(_("This picking is already %s.") % picking.state)

        result = picking._scanner_find_move_by_barcode(barcode)
        if not result:
            return {
                'success': False,
                'reason': 'unknown_barcode',
                'message': _("No product in this picking matches barcode: %s") % barcode,
            }

        increment = float(increment or 1.0)

        if result.get('move_line_id'):
            ml = request.env['stock.move.line'].browse(result['move_line_id'])
            ml.quantity = ml.quantity + increment
            return {
                'success': True,
                'type': 'move_line_updated',
                'move_line_id': ml.id,
                'product_name': ml.product_id.display_name,
                'new_quantity': ml.quantity,
                'uom': ml.product_uom.name,
            }

        move = request.env['stock.move'].browse(result['move_id'])
        if move.product_id.tracking != 'none' and not result.get('lot_name'):
            return {
                'success': False,
                'reason': 'lot_required',
                'message': _("Product %s is tracked. Please provide a lot/serial number.") % move.product_id.display_name,
                'move_id': move.id,
                'product_name': move.product_id.display_name,
            }

        vals = {
            'move_id': move.id,
            'picking_id': picking.id,
            'product_id': move.product_id.id,
            'product_uom': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'quantity': increment,
        }
        if result.get('lot_name'):
            vals['lot_name'] = result['lot_name']
        ml = request.env['stock.move.line'].create(vals)
        return {
            'success': True,
            'type': 'move_line_created',
            'move_line_id': ml.id,
            'product_name': ml.product_id.display_name,
            'new_quantity': ml.quantity,
            'uom': ml.product_uom.name,
        }

    @http.route('/stock_barcode_scanner_pro/validate',
                type='json', auth='user', methods=['POST'])
    def validate_picking(self, picking_id, **kwargs):
        picking = request.env['stock.picking'].browse(picking_id).exists()
        if not picking:
            raise UserError(_("Picking not found."))
        if picking.state in ('done', 'cancel'):
            return {'success': False, 'message': _("Picking is already %s.") % picking.state}
        try:
            res = picking.with_context(skip_backorder=True).button_validate()
        except UserError as e:
            return {'success': False, 'message': str(e)}

        if isinstance(res, dict) and res.get('res_model'):
            handled = self._auto_handle_wizard(res, picking)
            if not handled:
                return {
                    'success': False,
                    'reason': 'wizard_required',
                    'message': _("Validation requires a wizard (%s). Please complete it in the backend.") % res.get('res_model'),
                }
            return {'success': True, 'message': _("Picking validated.")}

        return {'success': True, 'message': _("Picking validated.")}

    def _auto_handle_wizard(self, action, picking):
        """Auto-confirm known wizards that block picking validation."""
        res_model = action.get('res_model')
        context = action.get('context', {}) or {}

        if res_model == 'confirm.stock.sms':
            wizard = request.env[res_model].with_context(context).create({})
            if hasattr(wizard, 'action_skip'):
                wizard.action_skip()
            elif hasattr(wizard, 'action_send_sms'):
                wizard.action_send_sms()
            if picking.state not in ('done', 'cancel'):
                try:
                    picking.with_context(skip_backorder=True).button_validate()
                except UserError:
                    pass
            return True

        if res_model == 'stock.backorder.confirmation':
            wizard = request.env[res_model].with_context(context).create({
                'pick_ids': [(6, 0, picking.ids)],
            })
            if hasattr(wizard, 'process'):
                wizard.with_context(skip_backorder=True).process()
            elif hasattr(wizard, 'process_cancel_backorder'):
                wizard.with_context(skip_backorder=True).process_cancel_backorder()
            return True

        return False
