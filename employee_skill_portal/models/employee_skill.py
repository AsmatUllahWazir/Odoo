from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmployeeSkill(models.Model):
    _name = 'employee.skill'
    _description = 'Employee Skill'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(string='Skill Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id',
                                    store=True)
    company_id = fields.Many2one('res.company', string='Company', related='employee_id.company_id', store=True)

    # Skill Classification
    skill_type = fields.Selection([
        ('technical', 'Technical'),
        ('soft', 'Soft Skill'),
        ('language', 'Language'),
        ('certification', 'Certification'),
        ('tool', 'Tool/Software'),
        ('domain', 'Domain Knowledge'),
        ('methodology', 'Methodology'),
        ('framework', 'Framework'),
    ], string='Skill Type', default='technical', tracking=True)

    skill_category_id = fields.Many2one('skill.category', string='Skill Category')
    skill_tags = fields.Many2many('skill.tag', string='Tags')

    # Proficiency
    level = fields.Selection([
        ('novice', 'Novice (0-1 years)'),
        ('beginner', 'Beginner (1-2 years)'),
        ('intermediate', 'Intermediate (3-5 years)'),
        ('advanced', 'Advanced (5-8 years)'),
        ('expert', 'Expert (8+ years)')
    ], string='Proficiency Level', tracking=True)

    years_experience = fields.Float(string='Years of Experience', tracking=True)
    last_used = fields.Date(string='Last Used')
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('rarely', 'Rarely')
    ], string='Usage Frequency')

    # Certification Details
    certification_date = fields.Date(string='Certification Date')
    certification_expiry = fields.Date(string='Certification Expiry')
    certification_org = fields.Char(string='Certifying Organization')
    certificate_id = fields.Char(string='Certificate ID')
    certificate_url = fields.Char(string='Certificate URL')

    # Detailed Information
    description = fields.Html(string='Description')
    projects_used = fields.Text(string='Projects/Usage')
    achievements = fields.Text(string='Key Achievements')
    training_completed = fields.Text(string='Training Completed')

    # Verification & Approval
    is_verified = fields.Boolean(string='Verified by HR', default=False, tracking=True)
    verification_date = fields.Date(string='Verification Date')
    verified_by = fields.Many2one('res.users', string='Verified By')
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval State', default='draft', tracking=True)

    # Rating & Assessment
    self_rating = fields.Selection([
        ('1', '1 - Basic Awareness'),
        ('2', '2 - Novice'),
        ('3', '3 - Intermediate'),
        ('4', '4 - Advanced'),
        ('5', '5 - Expert')
    ], string='Self Rating', default='3')

    manager_rating = fields.Selection([
        ('1', '1 - Basic Awareness'),
        ('2', '2 - Novice'),
        ('3', '3 - Intermediate'),
        ('4', '4 - Advanced'),
        ('5', '5 - Expert')
    ], string='Manager Rating')

    overall_rating = fields.Float(string='Overall Rating', compute='_compute_overall_rating', store=True, digits=(3, 2))

    # Endorsements
    endorsement_ids = fields.One2many('skill.endorsement', 'skill_id', string='Endorsements')
    endorsement_count = fields.Integer(string='Endorsements', compute='_compute_endorsement_count', store=True)

    # Visual & Organization
    color = fields.Char(string='Color', default='#4CAF50')
    icon = fields.Char(string='Icon', help='Font Awesome icon class')
    sequence = fields.Integer(string='Sequence', default=10)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Priority', default='medium')

    # System Fields
    active = fields.Boolean(string='Active', default=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)

    # Computed Fields
    skill_score = fields.Float(string='Skill Score', compute='_compute_skill_score', store=True)
    days_since_last_used = fields.Integer(string='Days Since Last Used', compute='_compute_days_since_last_used')
    is_expired = fields.Boolean(string='Certificate Expired', compute='_compute_is_expired')

    # Constraints
    _sql_constraints = [
        ('unique_certificate', 'unique(certificate_id, certification_org)',
         'Certificate ID must be unique per organization!'),
    ]

    @api.depends('self_rating', 'manager_rating', 'endorsement_count', 'years_experience')
    def _compute_skill_score(self):
        for skill in self:
            score = 0
            # Base on self rating (40%)
            if skill.self_rating:
                score += int(skill.self_rating) * 8  # 1-5 becomes 8-40

            # Add manager rating (30%)
            if skill.manager_rating:
                score += int(skill.manager_rating) * 6  # 1-5 becomes 6-30

            # Add endorsements (20%)
            score += min(skill.endorsement_count * 2, 20)

            # Add experience (10%)
            score += min(skill.years_experience, 10)

            skill.skill_score = min(score, 100)

    @api.depends('last_used')
    def _compute_days_since_last_used(self):
        for skill in self:
            if skill.last_used:
                delta = fields.Date.today() - skill.last_used
                skill.days_since_last_used = delta.days
            else:
                skill.days_since_last_used = 0

    @api.depends('certification_expiry')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for skill in self:
            skill.is_expired = skill.certification_expiry and skill.certification_expiry < today

    @api.depends('self_rating', 'manager_rating')
    def _compute_overall_rating(self):
        for skill in self:
            ratings = []
            if skill.self_rating:
                ratings.append(int(skill.self_rating))
            if skill.manager_rating:
                ratings.append(int(skill.manager_rating))

            if ratings:
                skill.overall_rating = sum(ratings) / len(ratings)
            else:
                skill.overall_rating = 0

    @api.depends('endorsement_ids', 'endorsement_ids.state')
    def _compute_endorsement_count(self):
        for skill in self:
            skill.endorsement_count = len(skill.endorsement_ids.filtered(lambda e: e.state == 'approved'))

    # Action Methods
    def action_submit(self):
        """Submit skill for approval"""
        self.write({'approval_state': 'submitted'})
        return True

    def action_approve(self):
        """Approve the skill"""
        self.write({
            'approval_state': 'approved',
            'is_verified': True,
            'verification_date': fields.Date.today(),
            'verified_by': self.env.user.id
        })
        return True

    def action_reject(self):
        """Reject the skill"""
        self.write({'approval_state': 'rejected'})
        return True

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'approval_state': 'draft'})
        return True

    def action_verify(self):
        """Verify the skill"""
        for skill in self:
            skill.write({
                'is_verified': True,
                'verification_date': fields.Date.today(),
                'verified_by': self.env.user.id
            })
        return True

    def toggle_active(self):
        """Archive/Unarchive the skill"""
        self.active = not self.active
        return True

    def action_view_endorsements(self):
        """Open endorsements for this skill"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Endorsements for {self.name}',
            'res_model': 'skill.endorsement',
            'view_mode': 'list,form',
            'domain': [('skill_id', '=', self.id)],
            'context': {
                'default_skill_id': self.id,
                'search_default_skill_id': self.id,
            }
        }

    # Validation
    @api.constrains('years_experience')
    def _check_years_experience(self):
        for skill in self:
            if skill.years_experience < 0:
                raise ValidationError('Years of experience cannot be negative!')

    @api.constrains('certification_expiry')
    def _check_certification_expiry(self):
        for skill in self:
            if skill.certification_expiry and skill.certification_date:
                if skill.certification_expiry < skill.certification_date:
                    raise ValidationError('Certification expiry date cannot be before certification date!')


class SkillCategory(models.Model):
    _name = 'skill.category'
    _description = 'Skill Category'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('skill.category', string='Parent Category')
    child_ids = fields.One2many('skill.category', 'parent_id', string='Sub Categories')
    skill_type = fields.Selection([
        ('technical', 'Technical'),
        ('soft', 'Soft Skill'),
        ('language', 'Language'),
        ('certification', 'Certification'),
        ('tool', 'Tool/Software'),
        ('domain', 'Domain Knowledge'),
        ('methodology', 'Methodology'),
        ('framework', 'Framework'),
    ], string='Skill Type')
    color = fields.Char(string='Color', default='#4CAF50')
    icon = fields.Char(string='Icon')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    skill_count = fields.Integer(string='Skills Count', compute='_compute_skill_count')

    @api.depends('child_ids')
    def _compute_skill_count(self):
        for category in self:
            skills = self.env['employee.skill'].search_count([('skill_category_id', '=', category.id)])
            category.skill_count = skills


class SkillTag(models.Model):
    _name = 'skill.tag'
    _description = 'Skill Tag'

    name = fields.Char(string='Name', required=True)
    color = fields.Char(string='Color', default='#4CAF50')
    active = fields.Boolean(string='Active', default=True)


class SkillEndorsement(models.Model):
    _name = 'skill.endorsement'
    _description = 'Skill Endorsement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    skill_id = fields.Many2one('employee.skill', string='Skill', required=True, ondelete='cascade')
    endorser_id = fields.Many2one('res.partner', string='Endorser', required=True)
    endorser_email = fields.Char(string='Endorser Email', related='endorser_id.email')
    endorser_position = fields.Char(string='Endorser Position')
    endorsement_date = fields.Datetime(string='Date', default=fields.Datetime.now)
    comment = fields.Text(string='Comment')
    relationship = fields.Selection([
        ('manager', 'Manager'),
        ('colleague', 'Colleague'),
        ('client', 'Client'),
        ('vendor', 'Vendor'),
        ('mentor', 'Mentor'),
        ('other', 'Other')
    ], string='Relationship')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending', tracking=True)

    rating = fields.Selection([
        ('1', '1 - Basic Awareness'),
        ('2', '2 - Novice'),
        ('3', '3 - Intermediate'),
        ('4', '4 - Advanced'),
        ('5', '5 - Expert')
    ], string='Endorser Rating')

    is_anonymous = fields.Boolean(string='Anonymous Endorsement')
    visibility = fields.Selection([
        ('public', 'Public'),
        ('internal', 'Internal Only'),
        ('private', 'Private')
    ], string='Visibility', default='internal')

    def action_approve(self):
        """Approve the endorsement"""
        self.write({'state': 'approved'})
        return True

    def action_reject(self):
        """Reject the endorsement"""
        self.write({'state': 'rejected'})
        return True

    def action_request_endorsement(self):
        """Send endorsement request to someone"""
        return True


class EmployeeSkillAssessment(models.Model):
    _name = 'employee.skill.assessment'
    _description = 'Employee Skill Assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Assessment Name', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    assessment_date = fields.Date(string='Assessment Date', default=fields.Date.today)
    assessor_id = fields.Many2one('hr.employee', string='Assessor')
    assessment_type = fields.Selection([
        ('self', 'Self Assessment'),
        ('manager', 'Manager Assessment'),
        ('peer', 'Peer Assessment'),
        ('external', 'External Assessment')
    ], string='Assessment Type', default='self')

    skill_ids = fields.One2many('assessment.skill.line', 'assessment_id', string='Skills')
    overall_score = fields.Float(string='Overall Score', compute='_compute_overall_score', store=True)
    comments = fields.Text(string='Comments')
    recommendations = fields.Text(string='Recommendations')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('reviewed', 'Reviewed')
    ], string='State', default='draft', tracking=True)

    @api.depends('skill_ids.score')
    def _compute_overall_score(self):
        for assessment in self:
            if assessment.skill_ids:
                total = sum(skill.score for skill in assessment.skill_ids)
                assessment.overall_score = total / len(assessment.skill_ids)
            else:
                assessment.overall_score = 0

    def action_start_assessment(self):
        self.state = 'in_progress'
        return True

    def action_complete_assessment(self):
        self.state = 'completed'
        return True

    def action_review_assessment(self):
        self.state = 'reviewed'
        return True


class AssessmentSkillLine(models.Model):
    _name = 'assessment.skill.line'
    _description = 'Assessment Skill Line'

    assessment_id = fields.Many2one('employee.skill.assessment', string='Assessment')
    skill_id = fields.Many2one('employee.skill', string='Skill', required=True)
    required_level = fields.Selection([
        ('1', '1 - Basic Awareness'),
        ('2', '2 - Novice'),
        ('3', '3 - Intermediate'),
        ('4', '4 - Advanced'),
        ('5', '5 - Expert')
    ], string='Required Level')
    current_level = fields.Selection([
        ('1', '1 - Basic Awareness'),
        ('2', '2 - Novice'),
        ('3', '3 - Intermediate'),
        ('4', '4 - Advanced'),
        ('5', '5 - Expert')
    ], string='Current Level')
    score = fields.Float(string='Score')
    gap = fields.Float(string='Gap', compute='_compute_gap')
    comments = fields.Text(string='Comments')

    @api.depends('required_level', 'current_level')
    def _compute_gap(self):
        for line in self:
            required = int(line.required_level) if line.required_level else 0
            current = int(line.current_level) if line.current_level else 0
            line.gap = required - current


class SkillTraining(models.Model):
    _name = 'skill.training'
    _description = 'Skill Training'

    name = fields.Char(string='Training Name', required=True)
    skill_ids = fields.Many2many('employee.skill', string='Related Skills')
    training_type = fields.Selection([
        ('online', 'Online Course'),
        ('classroom', 'Classroom Training'),
        ('workshop', 'Workshop'),
        ('certification', 'Certification Program'),
        ('on_the_job', 'On-the-Job Training')
    ], string='Training Type')
    provider = fields.Char(string='Provider')
    duration = fields.Float(string='Duration (hours)')
    cost = fields.Float(string='Cost')
    url = fields.Char(string='Course URL')
    description = fields.Html(string='Description')
    active = fields.Boolean(string='Active', default=True)
