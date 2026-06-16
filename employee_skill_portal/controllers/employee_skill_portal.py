# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import datetime
import json


class SkillPortal(CustomerPortal):

    @http.route(['/skills', '/skills/page/<int:page>', '/my/skills'],
                type='http', auth="public", website=True)
    def portal_all_skills(self, page=1, **kwargs):
        """Display all employees' skills in portal"""
        # Get all active employees with skills
        employees = request.env['hr.employee'].search([
            ('active', '=', True)
        ])

        # Get all skills
        skills = request.env['employee.skill'].search([
            ('active', '=', True),
            ('approval_state', '=', 'approved')
        ])

        # Calculate statistics
        values = self._prepare_skill_values(employees, skills, page)
        values.update({
            'selected_employee': None,
            'page': 'all_employees',
            'search_term': kwargs.get('search', ''),
        })

        # Handle search if present
        if kwargs.get('search'):
            search_term = kwargs.get('search', '').strip()
            if search_term:
                search_results = request.env['employee.skill'].search([
                    ('active', '=', True),
                    ('approval_state', '=', 'approved'),
                    '|', '|', '|',
                    ('name', 'ilike', search_term),
                    ('description', 'ilike', search_term),
                    ('skill_category_id.name', 'ilike', search_term),
                    ('skill_tags.name', 'ilike', search_term)
                ])
                values['search_results'] = search_results
                values['search_term'] = search_term

        # Handle category filter
        if kwargs.get('category'):
            category_id = int(kwargs.get('category'))
            category = request.env['skill.category'].browse(category_id)
            if category.exists():
                filtered_skills = skills.filtered(lambda s: s.skill_category_id.id == category_id)
                # Re-prepare values with filtered skills
                values = self._prepare_skill_values(employees, filtered_skills, page)
                values['selected_category'] = category
                values['page'] = 'category'

        return request.render("employee_skill_portal.portal_skill_layout", values)

    @http.route(['/skills/employee/<int:employee_id>'],
                type='http', auth="public", website=True)
    def portal_employee_skills(self, employee_id, **kwargs):
        """Display specific employee's skills"""
        employee = request.env['hr.employee'].browse(employee_id)
        if not employee.exists() or not employee.active:
            return request.redirect('/skills')

        # Get employee's skills
        skills = request.env['employee.skill'].search([
            ('employee_id', '=', employee.id),
            ('active', '=', True),
            ('approval_state', '=', 'approved')
        ])

        # Get skill recommendations (only for logged in users viewing their own profile)
        recommendations = []
        skill_gaps = []
        if request.env.user.employee_id.id == employee_id or request.env.user.has_group('base.group_user'):
            engine = request.env['skill.recommendation.engine']
            try:
                recommendations = engine.generate_recommendations_for_employee(employee_id, limit=5)
                skill_gaps = engine.get_role_based_skill_gaps(employee_id)
            except Exception:
                pass

        # Get all employees for context
        all_employees = request.env['hr.employee'].search([('active', '=', True)])

        # Group skills by category
        employee_skills_by_category = {}
        for skill in skills:
            category_name = skill.skill_category_id.name if skill.skill_category_id else 'Uncategorized'
            if category_name not in employee_skills_by_category:
                employee_skills_by_category[category_name] = []
            employee_skills_by_category[category_name].append(skill)

        # Prepare values
        values = self._prepare_skill_values(all_employees, skills, 1)
        values.update({
            'selected_employee': employee,
            'page': 'employee_detail',
            'employee_skills_by_category': employee_skills_by_category,
            'skill_recommendations': recommendations,
            'skill_gaps': skill_gaps[:5] if skill_gaps else [],
        })

        return request.render("employee_skill_portal.portal_skill_layout", values)

    @http.route('/skills/search', type='http', auth="public", website=True)
    def portal_search_skills(self, **kwargs):
        """Search skills by keyword"""
        search_term = kwargs.get('search', '').strip()

        if not search_term:
            return request.redirect('/skills')

        # Search in skills
        skills = request.env['employee.skill'].search([
            ('active', '=', True),
            ('approval_state', '=', 'approved'),
            '|', '|', '|',
            ('name', 'ilike', search_term),
            ('description', 'ilike', search_term),
            ('skill_category_id.name', 'ilike', search_term),
            ('skill_tags.name', 'ilike', search_term)
        ])

        # Get unique employees from search results
        employee_ids = skills.mapped('employee_id.id')
        employees = request.env['hr.employee'].browse(employee_ids)

        values = self._prepare_skill_values(employees, skills, 1)
        values.update({
            'search_term': search_term,
            'search_results': skills,
            'page': 'search',
        })

        return request.render("employee_skill_portal.portal_skill_layout", values)

    @http.route(['/skills/category/<int:category_id>'], type='http', auth="public", website=True)
    def portal_category_skills(self, category_id, **kwargs):
        """Filter skills by category"""
        category = request.env['skill.category'].browse(category_id)
        if not category.exists():
            return request.redirect('/skills')

        # Get skills in this category
        skills = request.env['employee.skill'].search([
            ('active', '=', True),
            ('approval_state', '=', 'approved'),
            ('skill_category_id', '=', category.id)
        ])

        # Get unique employees
        employee_ids = skills.mapped('employee_id.id')
        employees = request.env['hr.employee'].browse(employee_ids)

        values = self._prepare_skill_values(employees, skills, 1)
        values.update({
            'selected_category': category,
            'page': 'category',
        })

        return request.render("employee_skill_portal.portal_skill_layout", values)

    @http.route('/skills/compare', type='http', auth="public", website=True)
    def portal_compare_employees(self, **kwargs):
        """Compare skills between employees"""
        employee_ids = kwargs.get('employee_ids', [])
        if isinstance(employee_ids, str):
            employee_ids = [int(x.strip()) for x in employee_ids.split(',') if x.strip()]

        if not employee_ids or len(employee_ids) < 2:
            # Show employee selection for comparison
            employees = request.env['hr.employee'].search([('active', '=', True)])
            return request.render("employee_skill_portal.portal_skill_comparison_select", {
                'employees': employees,
                'page': 'compare_select',
            })

        employees = request.env['hr.employee'].browse(employee_ids)

        if len(employees) < 2:
            return request.redirect('/skills')

        comparison_data = []
        all_skills = set()

        for employee in employees:
            skills = employee.skill_ids.filtered(lambda s: s.active and s.approval_state == 'approved')
            skill_map = {}
            for skill in skills:
                skill_map[skill.name] = {
                    'level': skill.level,
                    'level_numeric': skill.level_numeric,
                    'score': skill.skill_score,
                    'verified': skill.is_verified
                }
                all_skills.add(skill.name)
            comparison_data.append({
                'employee': employee,
                'skills': skill_map
            })

        # Build comparison table
        comparison_table = []
        for skill_name in sorted(all_skills):
            row = {'skill': skill_name}
            for i, data in enumerate(comparison_data):
                skill_data = data['skills'].get(skill_name)
                if skill_data:
                    row[f'employee_{i}'] = {
                        'level': skill_data['level'],
                        'score': skill_data['score'],
                        'verified': skill_data['verified']
                    }
                else:
                    row[f'employee_{i}'] = None
            comparison_table.append(row)

        return request.render("employee_skill_portal.portal_skill_comparison", {
            'employees': employees,
            'comparison_table': comparison_table,
            'page': 'comparison',
        })

    def _prepare_skill_values(self, employees, skills, page=1):
        """Prepare common values for templates"""
        # Pre-calculate skill counts for each employee
        employee_skill_counts = {}
        for emp in employees:
            emp_skills = skills.filtered(lambda s: s.employee_id.id == emp.id)
            employee_skill_counts[emp.id] = {
                'skill_count': len(emp_skills),
                'certification_count': len(emp_skills.filtered(lambda s: s.skill_type == 'certification')),
                'endorsement_count': sum(emp_skills.mapped('endorsement_count')),
                'avg_skill_score': sum(emp_skills.mapped('skill_score')) / len(emp_skills) if emp_skills else 0,
                'has_critical_skills': bool(emp_skills.filtered(lambda s: s.priority == 'critical')),
            }

        # Group employees by department
        employees_by_department = {}
        for emp in employees:
            dept_name = emp.department_id.name if emp.department_id else 'No Department'
            if dept_name not in employees_by_department:
                employees_by_department[dept_name] = []

            employees_by_department[dept_name].append({
                'id': emp.id,
                'name': emp.name,
                'job_title': emp.job_title or 'Employee',
                'image_1920': emp.image_1920,
                'department_id': emp.department_id,
                'skill_count': employee_skill_counts.get(emp.id, {}).get('skill_count', 0),
                'certification_count': employee_skill_counts.get(emp.id, {}).get('certification_count', 0),
                'endorsement_count': employee_skill_counts.get(emp.id, {}).get('endorsement_count', 0),
                'avg_skill_score': employee_skill_counts.get(emp.id, {}).get('avg_skill_score', 0),
            })

        # Calculate overall statistics
        total_skills = len(skills)
        total_certifications = len(skills.filtered(lambda s: s.skill_type == 'certification'))
        total_endorsements = sum(skills.mapped('endorsement_count'))
        total_verified = len(skills.filtered(lambda s: s.is_verified))

        # Get top skills by endorsement
        top_skills = skills.sorted(key=lambda s: s.endorsement_count, reverse=True)[:10]

        # Get recent certifications
        recent_certs = skills.filtered(
            lambda s: s.skill_type == 'certification' and s.certification_date
        ).sorted('certification_date', reverse=True)[:5]

        # Skills about to expire
        expiring_soon = skills.filtered(
            lambda s: s.skill_type == 'certification' and s.expiry_status == 'expiring_soon'
        )

        # Prepare skill categories for filtering
        skill_categories = request.env['skill.category'].search([('active', '=', True)])
        skill_categories_list = []
        for category in skill_categories:
            category_skills = skills.filtered(lambda s: s.skill_category_id.id == category.id)
            skill_categories_list.append({
                'id': category.id,
                'name': category.name,
                'description': category.description or '',
                'skill_count': len(category_skills),
                'avg_score': sum(category_skills.mapped('skill_score')) / len(
                    category_skills) if category_skills else 0,
                'icon': category.icon or 'fa-folder',
                'color': category.color or '#667eea',
            })

        # Skill tags
        skill_tags = request.env['skill.tag'].search([('active', '=', True)])

        return {
            'employees': employees,
            'employees_by_department': employees_by_department,
            'employee_skill_counts': employee_skill_counts,
            'all_skills': skills,
            'total_skills': total_skills,
            'total_certifications': total_certifications,
            'total_endorsements': total_endorsements,
            'total_employees': len(employees),
            'total_verified': total_verified,
            'verification_rate': (total_verified / total_skills * 100) if total_skills else 0,
            'top_skills': top_skills,
            'recent_certifications': recent_certs,
            'expiring_soon': expiring_soon,
            'skill_categories': skill_categories,
            'skill_categories_list': skill_categories_list,
            'skill_tags': skill_tags,
            'page': page,
            'skill_type_mapping': {
                'technical': 'Technical Skills',
                'soft': 'Soft Skills',
                'language': 'Languages',
                'certification': 'Certifications',
                'tool': 'Tools & Software',
                'domain': 'Domain Knowledge',
                'methodology': 'Methodologies',
                'framework': 'Frameworks',
            },
            'current_date': datetime.datetime.now().strftime("%Y-%m-%d"),
        }
