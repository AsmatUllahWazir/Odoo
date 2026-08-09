# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SmartPrinterResolver(models.Model):
    """
    Printer Resolver Model

    Central method for printer resolution.
    Evaluates rules in a predictable priority order.
    """
    _name = 'smart.printer.resolver'
    _description = 'Smart Printer Resolver'
    _auto = False

    @api.model
    def get_printer_for_document(self, model=None, record=None, report=None,
                                 user=None, company=None, carrier=None,
                                 workstation=None, doc_type=None, **kwargs):
        """
        Central method for printer resolution.

        Evaluates printer selection rules in priority order:
        1. Explicit printer (if provided)
        2. Exact user + report rule
        3. Workstation + report rule
        4. User + model rule
        5. User default printer
        6. Company default printer
        7. Global/default printer

        Args:
            model (str): Model name
            record (Model): Record instance
            report (ir.actions.report): Report being printed
            user (res.users): User requesting the print
            company (res.company): Company context
            carrier (delivery.carrier): Carrier (if applicable)
            workstation (str): Workstation name
            doc_type (str): Document type
            **kwargs: Additional context

        Returns:
            smart.printer: The selected printer or None
        """
        # Get current context
        user = user or self.env.user
        company = company or user.company_id
        workstation = workstation or user.workstation_name

        # 1. Check explicit printer
        if kwargs.get('explicit_printer'):
            printer = kwargs['explicit_printer']
            if isinstance(printer, models.Model) and printer._name == 'smart.printer':
                if printer.active:
                    _logger.info(f"Using explicit printer: {printer.name}")
                    return printer
            elif isinstance(printer, int):
                printer_obj = self.env['smart.printer'].browse(printer)
                if printer_obj.exists() and printer_obj.active:
                    _logger.info(f"Using explicit printer: {printer_obj.name}")
                    return printer_obj

        # 2. Evaluate rules in priority order
        rules = self.env['smart.print.rule'].search([
            ('active', '=', True),
            '|',
            ('company_id', '=', company.id),
            ('company_id', '=', False)
        ], order='priority desc, apply_order')

        document_info = {
            'user': user,
            'company': company,
            'workstation': workstation,
            'report': report,
            'model': model,
            'carrier': carrier,
            'doc_type': doc_type,
            'record': record,
        }

        for rule in rules:
            if rule.evaluate_rule(document_info):
                if rule.printer_id and rule.printer_id.active:
                    _logger.info(f"Rule '{rule.name}' matched, using printer: {rule.printer_id.name}")
                    return rule.printer_id

        # 3. Check user default printer
        if user.default_printer_id and user.default_printer_id.active:
            _logger.info(f"Using user default printer: {user.default_printer_id.name}")
            return user.default_printer_id

        # 4. Check report configuration
        if report:
            report_config = self.env['smart.print.report'].get_report_config(report.id)
            if report_config and report_config.default_printer_id:
                if report_config.default_printer_id.active:
                    _logger.info(f"Using report default printer: {report_config.default_printer_id.name}")
                    return report_config.default_printer_id

        # 5. Check company default printer
        company_printer = self.env['smart.printer'].search([
            ('company_id', '=', company.id),
            ('active', '=', True)
        ], limit=1)
        if company_printer:
            _logger.info(f"Using company default printer: {company_printer.name}")
            return company_printer

        # 6. Global default (first active printer)
        global_printer = self.env['smart.printer'].search([
            ('active', '=', True)
        ], limit=1)
        if global_printer:
            _logger.info(f"Using global default printer: {global_printer.name}")
            return global_printer

        _logger.warning(
            f"No printer found for document - model: {model}, "
            f"user: {user.name}, company: {company.name}"
        )
        return None

    @api.model
    def resolve_printers_batch(self, documents, **kwargs):
        """
        Resolve printers for multiple documents efficiently.

        Args:
            documents (list): List of document info dicts
            **kwargs: Additional context

        Returns:
            dict: Mapping of document index to printer
        """
        result = {}

        for idx, doc in enumerate(documents):
            printer = self.get_printer_for_document(
                model=doc.get('model'),
                record=doc.get('record'),
                report=doc.get('report'),
                user=doc.get('user'),
                company=doc.get('company'),
                carrier=doc.get('carrier'),
                workstation=doc.get('workstation'),
                doc_type=doc.get('doc_type'),
                **kwargs
            )
            result[idx] = printer

        return result

    @api.model
    def validate_printer_compatibility(self, printer, document_format):
        """
        Validate that a printer is compatible with a document format.

        Args:
            printer (smart.printer): Printer to check
            document_format (str): Document format

        Returns:
            tuple: (bool, str) - (compatible, error_message)
        """
        if not printer:
            return False, _('No printer selected')

        if not printer.active:
            return False, _('Printer is not active')

        if not printer.can_print_format(document_format):
            return False, _(
                'Printer %(printer)s does not support format %(format)s'
            ) % {
                              'printer': printer.name,
                              'format': document_format.upper()
                          }

        if printer.server_id and printer.server_id.state != 'online':
            return False, _(
                'Print server %(server)s is not online'
            ) % {'server': printer.server_id.name}

        return True, ''
