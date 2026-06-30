# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class SalonPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if request.env.user.partner_id:
            partner = request.env.user.partner_id
            appointments = request.env['salon.appointment'].search([
                ('customer_id', '=', partner.id),
                ('state', 'not in', ['cancelled', 'no_show', 'completed'])
            ])
            values['upcoming_appointments'] = len(appointments)
            values['total_appointments'] = len(partner.appointment_ids)
            values['membership_active'] = partner.is_member
        return values

    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'],
                type='http', auth='user', website=True)
    def my_appointments(self, page=1, **kwargs):
        """My Appointments page"""
        partner = request.env.user.partner_id

        appointments = request.env['salon.appointment'].search([
            ('customer_id', '=', partner.id)
        ], order='appointment_date desc')

        # Pagination - Fixed
        step = 10
        pager = request.website.pager(
            url='/my/appointments',
            total=len(appointments),
            page=page,
            step=step,
            url_args=kwargs
        )

        # Get the slice of appointments for this page
        offset = pager['offset']
        limit = step  # Use the step value as limit
        appointments = appointments[offset:offset + limit]

        return request.render('salon_spa_management.portal_my_appointments', {
            'appointments': appointments,
            'pager': pager,
        })

    @http.route('/my/appointment/<int:appointment_id>', type='http', auth='user', website=True)
    def appointment_detail(self, appointment_id, **kwargs):
        """View single appointment detail"""
        appointment = request.env['salon.appointment'].browse(appointment_id)

        if not appointment.exists():
            return request.redirect('/my/appointments')

        if appointment.customer_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/appointments')

        return request.render('salon_spa_management.portal_appointment_detail', {
            'appointment': appointment,
        })

    @http.route('/my/appointment/<int:appointment_id>/cancel',
                type='http', auth='user', website=True, methods=['POST'])
    def cancel_my_appointment(self, appointment_id, **kwargs):
        """Cancel appointment from portal"""
        appointment = request.env['salon.appointment'].browse(appointment_id)

        if appointment.exists() and appointment.customer_id.id == request.env.user.partner_id.id:
            reason = kwargs.get('reason', 'Cancelled by customer via portal')
            if kwargs.get('reason_text'):
                reason = kwargs.get('reason_text')
            appointment.action_cancel()
            appointment.cancellation_reason = reason

        return request.redirect('/my/appointments')

    @http.route('/my/membership', type='http', auth='user', website=True)
    def my_membership(self, **kwargs):
        """My Membership page"""
        partner = request.env.user.partner_id

        return request.render('salon_spa_management.portal_my_membership', {
            'partner': partner,
            'membership_card': partner.membership_card_id,
            'membership_plans': request.env['salon.membership'].search([('is_active', '=', True)]),
        })

    @http.route('/my/membership/upgrade', type='http', auth='user', website=True, methods=['POST'])
    def upgrade_membership(self, **kwargs):
        """Upgrade membership plan"""
        partner = request.env.user.partner_id
        plan_id = kwargs.get('plan_id')

        if plan_id:
            plan = request.env['salon.membership'].browse(int(plan_id))
            if plan.exists():
                partner.membership_id = plan.id
                partner.is_member = True

                # Update or create membership card
                if not partner.membership_card_id:
                    card = request.env['salon.membership.card'].create({
                        'partner_id': partner.id,
                        'membership_id': plan.id,
                        'start_date': fields.Date.today(),
                    })
                    partner.membership_card_id = card.id

        return request.redirect('/my/membership')

    @http.route('/salon/booking', type='http', auth='public', website=True)
    def booking_page(self):
        """Online booking page"""
        services = request.env['salon.service'].search([
            ('active', '=', True)
        ])

        staff = request.env['hr.employee'].search([
            ('salon_skill_level', '!=', False)
        ])

        # Import datetime for the template
        from datetime import datetime
        import datetime as dt

        return request.render('salon_spa_management.salon_booking_portal', {
            'services': services,
            'staff': staff,
            'datetime': dt,  # Pass datetime module to template
        })
