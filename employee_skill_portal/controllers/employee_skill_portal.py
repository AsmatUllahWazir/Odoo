from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import datetime


class SkillPortal(CustomerPortal):

    @http.route(['/skills', '/skills/page/<int:page>'],
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
        })

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

        # Get all employees for the back button
        all_employees = request.env['hr.employee'].search([
            ('active', '=', True)
        ])

        values = self._prepare_skill_values(all_employees, skills, 1)
        values.update({
            'selected_employee': employee,
            'page': 'employee_detail',
        })

        return request.render("employee_skill_portal.portal_skill_layout", values)

    def _prepare_skill_values(self, employees, skills, page=1):
        """Prepare common values for templates"""
        # Pre-calculate skill counts for each employee
        employee_skill_counts = {}
        for emp in employees:
            emp_skills = skills.filtered(lambda s: s.employee_id == emp)
            employee_skill_counts[emp.id] = {
                'skill_count': len(emp_skills),
                'certification_count': len(emp_skills.filtered(lambda s: s.skill_type == 'certification')),
                'endorsement_count': sum(emp_skills.mapped('endorsement_count')),
            }

        # Group employees by department WITH counts
        employees_by_department = {}
        for emp in employees:
            dept_name = emp.department_id.name if emp.department_id else 'No Department'
            if dept_name not in employees_by_department:
                employees_by_department[dept_name] = []

            # Add employee with their skill counts
            employees_by_department[dept_name].append({
                'id': emp.id,
                'name': emp.name,
                'job_title': emp.job_title or 'Employee',
                'image_1920': emp.image_1920,
                'department_id': emp.department_id,
                'skill_count': employee_skill_counts.get(emp.id, {}).get('skill_count', 0),
                'certification_count': employee_skill_counts.get(emp.id, {}).get('certification_count', 0),
                'endorsement_count': employee_skill_counts.get(emp.id, {}).get('endorsement_count', 0),
                'record': emp,  # Keep the actual record for any other needs
            })

        # Group skills by category for the selected employee
        employee_skills_by_category = {}
        # This will be populated in the employee detail view
        if hasattr(self, 'selected_employee') and self.selected_employee:
            for skill in skills:
                if skill.employee_id == self.selected_employee:
                    category_name = skill.skill_category_id.name if skill.skill_category_id else 'Uncategorized'
                    if category_name not in employee_skills_by_category:
                        employee_skills_by_category[category_name] = []
                    employee_skills_by_category[category_name].append(skill)

        # Calculate overall statistics
        total_skills = len(skills)
        total_certifications = len(skills.filtered(lambda s: s.skill_type == 'certification'))
        total_endorsements = sum(skills.mapped('endorsement_count'))

        # Get top skills by endorsement
        top_skills = skills.sorted(key=lambda s: s.endorsement_count, reverse=True)[:10]

        # Get recent certifications
        recent_certs = skills.filtered(
            lambda s: s.skill_type == 'certification' and s.certification_date
        ).sorted('certification_date', reverse=True)[:5]

        # Prepare skill categories for filtering - ensure it's always a list
        skill_categories = request.env['skill.category'].search([('active', '=', True)])
        skill_tags = request.env['skill.tag'].search([('active', '=', True)])

        # Convert categories to a list format for easy template iteration
        skill_categories_list = []
        for category in skill_categories:
            category_skills = skills.filtered(lambda s: s.skill_category_id == category)
            skill_categories_list.append({
                'id': category.id,
                'name': category.name,
                'description': category.description or '',
                'skill_count': len(category_skills)
            })

        return {
            'employees': employees,
            'employees_by_department': employees_by_department,
            'employee_skill_counts': employee_skill_counts,
            'all_skills': skills,
            'employee_skills_by_category': employee_skills_by_category,
            'total_skills': total_skills,
            'total_certifications': total_certifications,
            'total_endorsements': total_endorsements,
            'total_employees': len(employees),
            'top_skills': top_skills,
            'recent_certifications': recent_certs,
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

    @http.route(['/skills/search'], type='http', auth="public", website=True)
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

    @http.route(['/skills/request-endorsement/<int:skill_id>'],
                type='http', auth="user", website=True, csrf=False)
    def portal_request_endorsement(self, skill_id, **kwargs):
        """Request endorsement for a skill"""
        skill = request.env['employee.skill'].browse(skill_id)
        if not skill.exists():
            return request.redirect('/skills')

        values = {
            'skill': skill,
            'page': 'request_endorsement',
        }

        return request.render("employee_skill_portal.endorsement_request_form", values)
