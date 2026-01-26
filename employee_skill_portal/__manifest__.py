{
    'name': 'Employee Skill Portfolio',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Portal',
    'summary': 'Showcase employee skills and certifications with beautiful portfolio design',
    'description': """
    Professional skill showcase portal for employees with modern design.
    Features:
    • Beautiful portfolio-style skill display
    • Certification gallery
    • Achievement timeline
    • Skill endorsements
    • Rating system
    • Responsive design with CSS animations
    """,
    'author': 'Your Company',
    'website': 'https://yourwebsite.com',
    'depends': ['base', 'portal', 'hr', 'website'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/data.xml',
        'views/employee_skill.xml',
        # 'views/templates.xml',
        'views/employee_skill_portal.xml',
    ],

    # 'assets': {
    #     'web.assets_frontend': [
    #         'employee_skill_portal/static/src/portal_skills.css',
    #     ],
    # },

    # 'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
    'price': 199.00,
    'currency': 'EUR',
}