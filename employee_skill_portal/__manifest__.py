{
    'name': 'Employee Skill Portfolio',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Portal',
    'summary': 'Showcase employee skills and certifications with beautiful portfolio design',

    'description': """
    Professional skill showcase portal for employees with modern design.
    
    Features:
    • Beautiful portfolio-style skill display with glassmorphism design
    • Certification gallery with expiry tracking
    • Achievement timeline and skill progression
    • Skill endorsements with request system
    • Advanced rating system with weighted scoring
    • Responsive design with CSS animations
    • AI-powered skill recommendations
    • Skill matrix and heatmap visualization
    • Department-wise skill analytics
    • Skill gap analysis for succession planning
    • REST API for external integrations
    • Automated email notifications
    • Skill comparison tool
    • Excel/PDF export capabilities
    • Change history tracking
    """,
    'author': 'Wazirz',
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

    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
    'price': 29.00,
    'currency': 'USD',
}
